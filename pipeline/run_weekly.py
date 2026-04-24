"""Weekly run: scrape all sources, classify+embed *new or changed* docs, upsert into Supabase.

Content-hash dedup: unchanged docs are skipped (no Gemini calls, no DB writes).
Changed docs are re-classified, re-embedded, and have last_changed_at bumped.
"""
from __future__ import annotations
import hashlib
import json
import sys
import traceback

from db.connection import connect
from scrapers import ALL_SCRAPERS
from .classify import classify_doc
from .embed import embed_text


UPSERT_SQL = """
insert into documents (source, source_id, url, title, raw_text, summary, why_care,
                      category, region, published_at, embedding, metadata,
                      content_hash, last_changed_at)
values (%(source)s, %(source_id)s, %(url)s, %(title)s, %(raw_text)s, %(summary)s, %(why_care)s,
        %(category)s, %(region)s, %(published_at)s, %(embedding)s, %(metadata)s,
        %(content_hash)s, now())
on conflict (source, source_id) do update set
    url = excluded.url,
    title = excluded.title,
    raw_text = excluded.raw_text,
    summary = excluded.summary,
    why_care = excluded.why_care,
    category = excluded.category,
    region = excluded.region,
    published_at = coalesce(excluded.published_at, documents.published_at),
    embedding = excluded.embedding,
    metadata = excluded.metadata,
    content_hash = excluded.content_hash,
    last_changed_at = now()
returning (xmax = 0) as inserted;
"""

EXISTING_HASHES_SQL = "select source_id, content_hash from documents where source = %s"


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def main() -> int:
    inserted = 0
    updated = 0
    unchanged = 0
    errors = 0
    conn = connect()
    try:
        for scraper in ALL_SCRAPERS:
            print(f"\n=== {scraper.source} ({scraper.region}) ===")
            with conn.cursor() as cur:
                cur.execute(EXISTING_HASHES_SQL, (scraper.source,))
                existing_hashes = {row[0]: row[1] for row in cur.fetchall()}

            try:
                docs = scraper.fetch()
            except Exception:
                traceback.print_exc()
                errors += 1
                continue

            print(f"  fetched {len(docs)} docs")
            src_inserted = src_updated = src_unchanged = 0
            for doc in docs:
                content_for_hash = (doc.raw_text or doc.title or "").strip()
                new_hash = _hash(content_for_hash)
                old_hash = existing_hashes.get(doc.source_id)

                # Skip: doc already exists and content hasn't changed
                if old_hash == new_hash:
                    src_unchanged += 1
                    unchanged += 1
                    continue

                # Skip: linked-only doc (no raw_text) that already exists
                if doc.source_id in existing_hashes and not doc.raw_text:
                    src_unchanged += 1
                    unchanged += 1
                    continue

                try:
                    text_for_llm = doc.raw_text or doc.title
                    enriched = classify_doc(doc.title, doc.url, doc.source, text_for_llm)
                    region = enriched.get("region_confirm") or doc.region
                    embedding = embed_text(f"{doc.title}\n\n{text_for_llm}")
                    with conn.cursor() as cur:
                        cur.execute(UPSERT_SQL, {
                            "source": doc.source,
                            "source_id": doc.source_id,
                            "url": doc.url,
                            "title": doc.title,
                            "raw_text": doc.raw_text,
                            "summary": enriched["summary"],
                            "why_care": enriched["why_care"],
                            "category": enriched["category"],
                            "region": region,
                            "published_at": doc.published_at,
                            "embedding": embedding,
                            "metadata": json.dumps(doc.metadata),
                            "content_hash": new_hash,
                        })
                        was_inserted = cur.fetchone()[0]
                    conn.commit()
                    if was_inserted:
                        inserted += 1
                        src_inserted += 1
                        print(f"  + NEW: {doc.title[:80]}")
                    else:
                        updated += 1
                        src_updated += 1
                        print(f"  ~ CHANGED: {doc.title[:80]}")
                except Exception:
                    conn.rollback()
                    traceback.print_exc()
                    errors += 1
            print(f"  → new={src_inserted} changed={src_updated} unchanged={src_unchanged}")
    finally:
        conn.close()

    print(f"\nDone. new={inserted} changed={updated} unchanged={unchanged} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""Weekly run: scrape all sources, classify+embed new docs, upsert into Supabase."""
from __future__ import annotations
import json
import sys
import traceback

from db.connection import connect
from scrapers import ALL_SCRAPERS
from .classify import classify_doc
from .embed import embed_text


UPSERT_SQL = """
insert into documents (source, source_id, url, title, raw_text, summary, why_care,
                      category, region, published_at, embedding, metadata)
values (%(source)s, %(source_id)s, %(url)s, %(title)s, %(raw_text)s, %(summary)s, %(why_care)s,
        %(category)s, %(region)s, %(published_at)s, %(embedding)s, %(metadata)s)
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
    metadata = excluded.metadata
returning (xmax = 0) as inserted;
"""

EXISTING_IDS_SQL = "select source_id from documents where source = %s"


def main() -> int:
    inserted = 0
    updated = 0
    errors = 0
    conn = connect()
    try:
        for scraper in ALL_SCRAPERS:
            print(f"\n=== {scraper.source} ({scraper.region}) ===")
            with conn.cursor() as cur:
                cur.execute(EXISTING_IDS_SQL, (scraper.source,))
                existing = {row[0] for row in cur.fetchall()}

            try:
                docs = scraper.fetch()
            except Exception:
                traceback.print_exc()
                errors += 1
                continue

            print(f"  fetched {len(docs)} docs")
            for doc in docs:
                if doc.source_id in existing and not doc.raw_text:
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
                        })
                        was_inserted = cur.fetchone()[0]
                    conn.commit()
                    if was_inserted:
                        inserted += 1
                        print(f"  + {doc.title[:80]}")
                    else:
                        updated += 1
                except Exception:
                    conn.rollback()
                    traceback.print_exc()
                    errors += 1
    finally:
        conn.close()

    print(f"\nDone. inserted={inserted} updated={updated} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

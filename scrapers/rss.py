"""Generic RSS scraper. Handles journal feeds (NEJM, JAMA, Lancet, npj DM, Health Affairs)."""
from __future__ import annotations
import hashlib
import html
import re
from datetime import datetime, timezone
from time import mktime

import feedparser

from .base import BaseScraper, ScrapedDoc

UA = "Mozilla/5.0 (clinical-ai-regwatch)"

# Loose AI / clinical-AI keyword set used to filter journal feeds (which publish lots of non-AI content)
AI_KEYWORDS = [
    "artificial intelligence", " ai ", " ai)", "(ai", "ai-", "-ai",
    "machine learning", " ml ", "deep learning", "neural network", "neural net",
    "large language model", " llm ", " llms ", "gpt", "transformer",
    "predictive model", "clinical decision support", "decision support",
    "algorithm", "algorithmic",
    "digital health", "digital medicine", "digital therapeutic",
    "samd", "software as a medical device",
    "model drift", "post-market surveillance",
]


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _is_ai_relevant(title: str, summary: str) -> bool:
    haystack = f"{title} {summary}".lower()
    return any(k in haystack for k in AI_KEYWORDS)


class RSSScraper(BaseScraper):
    def __init__(
        self,
        source: str,
        region: str,
        feed_url: str,
        keyword_filter: bool = True,
        max_items: int = 100,
    ) -> None:
        self.source = source
        self.region = region
        self.feed_url = feed_url
        self.keyword_filter = keyword_filter
        self.max_items = max_items

    def fetch(self) -> list[ScrapedDoc]:
        try:
            feed = feedparser.parse(self.feed_url, agent=UA)
        except Exception as e:
            print(f"[{self.source}] feed parse failed: {e}")
            return []
        if feed.bozo and not feed.entries:
            print(f"[{self.source}] feed has no entries (bozo={feed.bozo_exception})")
            return []

        docs: list[ScrapedDoc] = []
        for entry in feed.entries[: self.max_items]:
            title = _strip_html(entry.get("title", ""))
            summary = _strip_html(entry.get("summary", "") or entry.get("description", ""))
            link = entry.get("link", "")

            if self.keyword_filter and not _is_ai_relevant(title, summary):
                continue
            if not title or not link:
                continue

            published_at = None
            if getattr(entry, "published_parsed", None):
                published_at = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
            elif getattr(entry, "updated_parsed", None):
                published_at = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)

            sid = _hash(entry.get("id", "") or link)
            text_for_classifier = f"{title}\n\n{summary}" if summary else title

            docs.append(ScrapedDoc(
                source=self.source,
                source_id=sid,
                url=link,
                title=title,
                raw_text=text_for_classifier,
                region=self.region,
                published_at=published_at,
                metadata={"kind": "rss_item", "feed": self.feed_url},
            ))
        return docs

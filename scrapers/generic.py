"""Generic list-page scraper: fetches seed URLs, extracts relevant article links."""
from __future__ import annotations
import hashlib
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapedDoc

UA = "Mozilla/5.0 (clinical-ai-regwatch)"


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def _extract_main_text(soup: BeautifulSoup) -> str:
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return ""
    for tag in main.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = main.get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


class GenericListScraper(BaseScraper):
    """Fetches each seed URL, extracts main text, then walks in-domain links and keeps the relevant ones."""

    def __init__(
        self,
        source: str,
        region: str,
        seed_urls: list[str],
        base_domain: str,
        keywords: list[str] | None = None,
        max_links_per_seed: int = 40,
    ) -> None:
        self.source = source
        self.region = region
        self.seed_urls = seed_urls
        self.base_domain = base_domain
        self.keywords = [k.lower() for k in keywords] if keywords else None
        self.max_links_per_seed = max_links_per_seed

    def fetch(self) -> list[ScrapedDoc]:
        docs: list[ScrapedDoc] = []
        seen: set[str] = set()
        session = requests.Session()
        session.headers.update({
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

        for seed in self.seed_urls:
            try:
                resp = session.get(seed, timeout=30, allow_redirects=True)
                resp.raise_for_status()
            except Exception as e:
                print(f"[{self.source}] failed to fetch {seed}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            page_text = _extract_main_text(soup)
            page_title_tag = soup.find("h1") or soup.find("title")
            page_title = page_title_tag.get_text(strip=True) if page_title_tag else seed
            sid = _hash(resp.url)
            if sid not in seen and page_text:
                seen.add(sid)
                docs.append(ScrapedDoc(
                    source=self.source,
                    source_id=sid,
                    url=resp.url,
                    title=page_title,
                    raw_text=page_text,
                    region=self.region,
                    metadata={"kind": "seed_page"},
                ))

            kept = 0
            for a in soup.find_all("a", href=True):
                if kept >= self.max_links_per_seed:
                    break
                href = urljoin(resp.url, a["href"])
                netloc = urlparse(href).netloc.lower()
                if self.base_domain not in netloc:
                    continue
                text = a.get_text(strip=True)
                if not text or len(text) < 10:
                    continue
                if self.keywords and not self._is_relevant(text, href):
                    continue
                sid = _hash(href)
                if sid in seen:
                    continue
                seen.add(sid)
                kept += 1
                docs.append(ScrapedDoc(
                    source=self.source,
                    source_id=sid,
                    url=href,
                    title=text,
                    raw_text="",  # title-only; classifier uses title
                    region=self.region,
                    metadata={"kind": "linked_page", "discovered_on": resp.url},
                ))

        return docs

    def _is_relevant(self, text: str, href: str) -> bool:
        haystack = f"{text} {href}".lower()
        return any(k in haystack for k in self.keywords or [])

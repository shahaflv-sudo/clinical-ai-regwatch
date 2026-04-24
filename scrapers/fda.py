"""FDA scraper — pulls AI/ML SaMD guidance and the AI-enabled device list."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapedDoc

UA = "Mozilla/5.0 (clinical-ai-regwatch; +https://github.com/shahaflv-sudo/clinical-ai-regwatch)"

SEED_PAGES = [
    "https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-aiml-enabled-medical-devices",
    "https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-software-medical-device",
    "https://www.fda.gov/medical-devices/digital-health-center-excellence/digital-health-policy-navigator",
]


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


class FDAScraper(BaseScraper):
    source = "fda"
    region = "US"

    def fetch(self) -> list[ScrapedDoc]:
        docs: list[ScrapedDoc] = []
        seen: set[str] = set()
        session = requests.Session()
        session.headers.update({"User-Agent": UA})

        for seed in SEED_PAGES:
            try:
                resp = session.get(seed, timeout=30)
                resp.raise_for_status()
            except Exception as e:
                print(f"[fda] failed to fetch {seed}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            page_text = _extract_main_text(soup)
            page_title = (soup.find("h1") or soup.find("title"))
            page_title = page_title.get_text(strip=True) if page_title else seed
            sid = _hash(seed)
            if sid not in seen and page_text:
                seen.add(sid)
                docs.append(ScrapedDoc(
                    source=self.source,
                    source_id=sid,
                    url=seed,
                    title=page_title,
                    raw_text=page_text,
                    region=self.region,
                    published_at=None,
                    metadata={"kind": "guidance_page"},
                ))

            # Also follow links to FDA pages with relevant keywords
            for a in soup.find_all("a", href=True):
                href = urljoin(seed, a["href"])
                if not href.startswith("https://www.fda.gov/"):
                    continue
                text = a.get_text(strip=True)
                if not text or len(text) < 8:
                    continue
                if not _looks_relevant(text):
                    continue
                sid = _hash(href)
                if sid in seen:
                    continue
                seen.add(sid)
                docs.append(ScrapedDoc(
                    source=self.source,
                    source_id=sid,
                    url=href,
                    title=text,
                    raw_text="",  # to be lazily fetched in pipeline if needed
                    region=self.region,
                    published_at=None,
                    metadata={"kind": "linked_page", "discovered_on": seed},
                ))

        return docs


def _extract_main_text(soup: BeautifulSoup) -> str:
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return ""
    for tag in main.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = main.get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def _looks_relevant(text: str) -> bool:
    text = text.lower()
    keywords = [
        "artificial intelligence", "machine learning", "ai/ml", "ai-enabled",
        "software as a medical device", "samd", "digital health",
        "predetermined change control", "good machine learning practice",
    ]
    return any(k in text for k in keywords)

"""Israel Ministry of Health scraper — חוזרי מנכ"ל and digital health policies."""
from __future__ import annotations
import hashlib
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapedDoc

UA = "Mozilla/5.0 (clinical-ai-regwatch)"

# gov.il publishes circulars via a dynamic collector API
COLLECTOR_API = "https://www.gov.il/he/api/DynamicCollectorResultsApi"
CIRCULAR_COLLECTOR = "moh-circulars"

AI_KEYWORDS_HE = [
    "בינה מלאכותית", "AI", "ML", "למידת מכונה", "אלגוריתם",
    "תומך החלטה", "דיגיטלי", "טלרפואה", "סייבר",
]


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def _looks_relevant_he(text: str) -> bool:
    return any(k in text for k in AI_KEYWORDS_HE)


class MOHIsraelScraper(BaseScraper):
    source = "moh_il"
    region = "IL"

    def fetch(self) -> list[ScrapedDoc]:
        session = requests.Session()
        session.headers.update({"User-Agent": UA, "Accept": "application/json"})

        params = {
            "queryType": 4,
            "CollectorType": CIRCULAR_COLLECTOR,
            "skip": 0,
            "limit": 200,
        }
        try:
            resp = session.get(COLLECTOR_API, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"[moh_il] collector API failed: {e}")
            return []

        results = payload.get("Results") or payload.get("results") or []
        docs: list[ScrapedDoc] = []
        for item in results:
            data = item.get("Data", item)
            title = data.get("Title") or data.get("title") or ""
            description = data.get("Description") or data.get("description") or ""
            combined = f"{title}\n{description}"
            if not _looks_relevant_he(combined):
                continue

            url_path = data.get("DocumentUrl") or data.get("url") or item.get("Url") or ""
            url = urljoin("https://www.gov.il", url_path) if url_path else ""
            pub = data.get("PublishedDate") or data.get("publishedDate")
            published_at = _parse_date(pub)
            sid = _hash(url or title)

            docs.append(ScrapedDoc(
                source=self.source,
                source_id=sid,
                url=url,
                title=title,
                raw_text=description,
                region=self.region,
                published_at=published_at,
                metadata={"kind": "moh_circular", "raw": data},
            ))
        return docs


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

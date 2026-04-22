import logging
import time
import random
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, retry

logger = logging.getLogger(__name__)

PW_BASE = "https://pw.live"

TARGETS = [
    f"{PW_BASE}/study-material",
    f"{PW_BASE}/courses",
    f"{PW_BASE}/videos",
]

PCB_KEYWORDS = [
    "neet", "pcb", "physics", "chemistry", "biology",
    "class 12", "class12", "12th", "medical", "alakh",
    "dpp", "lecture", "yakeen", "batch",
]


class PWWebsiteCollector(BaseCollector):
    source_type = "website"

    def collect(self) -> list[dict]:
        all_items = []
        for url in TARGETS:
            try:
                items = self._scrape_page(url)
                all_items.extend(items)
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                logger.error(f"Failed scraping {url}: {e}")
        return all_items

    @retry(max_attempts=3, base_delay=5)
    def _scrape_page(self, url: str) -> list[dict]:
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = []

        # Generic card/article scraper — PW uses React so we parse what's rendered
        for card in soup.select("div[class*='card'], article, div[class*='course'], li[class*='item']"):
            title_el = card.select_one("h1, h2, h3, h4, a[class*='title'], span[class*='title']")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not self._is_pcb_relevant(title):
                continue

            link_el = card.select_one("a[href]")
            href = link_el["href"] if link_el else ""
            full_url = urljoin(PW_BASE, href) if href and not href.startswith("http") else href

            desc_el = card.select_one("p, span[class*='desc'], div[class*='desc']")
            body = desc_el.get_text(strip=True) if desc_el else ""

            img_el = card.select_one("img[src]")
            media_url = img_el.get("src", "") if img_el else ""

            external_id = full_url or title

            items.append(self.normalize({
                "title": title,
                "body": body,
                "url": full_url,
                "media_url": media_url,
                "external_id": external_id,
                "published_at": None,
            }))

        return items

    def normalize(self, raw: dict) -> dict:
        title = raw.get("title", "")
        body = raw.get("body", "")
        return {
            "external_id": raw.get("external_id") or raw.get("url") or title,
            "title": title,
            "body": body,
            "url": raw.get("url", ""),
            "media_url": raw.get("media_url", ""),
            "published_at": raw.get("published_at"),
            "content_type": self.classify_content_type(title, body),
            "category": self.classify_category(title, body),
        }

    def _is_pcb_relevant(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in PCB_KEYWORDS)

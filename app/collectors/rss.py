import html
import logging
import re
from datetime import datetime, timezone

from app.collectors.base import BaseCollector, retry

logger = logging.getLogger(__name__)

# For general news sites, only keep articles mentioning these
NEWS_FILTER_KEYWORDS = [
    "neet", "physics wallah", "physicswallah", "alakh pandey", "pw", "pcb",
    "class 12", "class12", "12th", "ncert", "biology", "chemistry", "physics",
    "medical entrance", "yakeen", "dpp", "syllabus", "nta",
]

# Sources that are already targeted (YouTube, Google News searches) — no filter needed
SKIP_FILTER_DOMAINS = [
    "youtube.com", "news.google.com",
]


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


class RSSCollector(BaseCollector):
    source_type = "rss"

    def collect(self) -> list[dict]:
        try:
            import feedparser
        except ImportError:
            logger.error("feedparser not installed")
            return []
        return self._fetch_feed()

    @retry(max_attempts=3, base_delay=5)
    def _fetch_feed(self) -> list[dict]:
        import feedparser
        feed_url = self.source.identifier
        since = self.source.last_checked_at
        if since and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        # Determine if this is a targeted feed (no keyword filtering needed)
        is_targeted = any(d in feed_url for d in SKIP_FILTER_DOMAINS)

        feed = feedparser.parse(feed_url)
        if feed.bozo and not feed.entries:
            logger.warning(f"RSS feed error for {feed_url}: {feed.bozo_exception}")
            return []

        results = []
        for entry in feed.entries[:50]:
            pub = self._parse_date(entry)
            if since and pub and pub < since:
                continue

            title = _strip_html(entry.get("title", ""))
            body = _strip_html(
                entry.get("summary", "") or entry.get("description", "") or entry.get("content", [{}])[0].get("value", "")
            )

            if not title:
                continue

            # For general news sites, require at least one relevant keyword
            if not is_targeted:
                text_lower = (title + " " + body).lower()
                if not any(kw in text_lower for kw in NEWS_FILTER_KEYWORDS):
                    continue

            results.append(self.normalize({
                "external_id": entry.get("id") or entry.get("link", ""),
                "title": title,
                "body": body,
                "url": entry.get("link", ""),
                "media_url": self._extract_thumbnail(entry),
                "published_at": pub,
            }))

        logger.info(f"RSS {self.source.name}: fetched {len(results)} items")
        return results

    def normalize(self, raw: dict) -> dict:
        title = raw.get("title", "")
        body = raw.get("body", "")
        return {
            "external_id": raw.get("external_id"),
            "title": title[:500],
            "body": body[:3000],
            "url": raw.get("url", ""),
            "media_url": raw.get("media_url", ""),
            "published_at": raw.get("published_at"),
            "content_type": self.classify_content_type(title, body),
            "category": self.classify_category(title, body),
        }

    @staticmethod
    def _parse_date(entry) -> datetime | None:
        for field in ("published", "updated", "created"):
            val = entry.get(f"{field}_parsed")
            if val:
                try:
                    import time as _time
                    ts = _time.mktime(val)
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    pass
        return None

    @staticmethod
    def _extract_thumbnail(entry) -> str:
        media = entry.get("media_thumbnail") or entry.get("media_content")
        if media and isinstance(media, list) and media[0]:
            return media[0].get("url", "")
        for link in entry.get("links", []):
            if link.get("type", "").startswith("image/"):
                return link.get("href", "")
        # Try enclosure
        for enc in entry.get("enclosures", []):
            if "image" in enc.get("type", ""):
                return enc.get("href", "") or enc.get("url", "")
        return ""

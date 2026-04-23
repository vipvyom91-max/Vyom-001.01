import html
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app.collectors.base import BaseCollector, retry

logger = logging.getLogger(__name__)


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

        feed = feedparser.parse(feed_url)
        if feed.bozo:
            logger.warning(f"RSS feed parse warning for {feed_url}: {feed.bozo_exception}")

        results = []
        for entry in feed.entries[:25]:
            pub = self._parse_date(entry)
            if since and pub and pub < since:
                continue
            results.append(self.normalize({
                "external_id": entry.get("id") or entry.get("link", ""),
                "title": entry.get("title", ""),
                "body": entry.get("summary", "") or entry.get("description", ""),
                "url": entry.get("link", ""),
                "media_url": self._extract_thumbnail(entry),
                "published_at": pub,
            }))
        return results

    def normalize(self, raw: dict) -> dict:
        title = html.unescape(raw.get("title", ""))
        body = html.unescape(raw.get("body", ""))
        return {
            "external_id": raw.get("external_id"),
            "title": title[:500],
            "body": body[:2000],
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
        if media and isinstance(media, list):
            return media[0].get("url", "")
        links = entry.get("links", [])
        for link in links:
            if link.get("type", "").startswith("image/"):
                return link.get("href", "")
        return ""

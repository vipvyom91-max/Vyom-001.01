import html
import logging
from datetime import datetime, timezone

from app.collectors.base import BaseCollector, retry

logger = logging.getLogger(__name__)


class YouTubeCollector(BaseCollector):
    source_type = "youtube"

    def collect(self) -> list[dict]:
        if not self.config.YOUTUBE_API_KEY:
            logger.warning("YouTube API key not configured — skipping")
            return []
        try:
            from googleapiclient.discovery import build
        except ImportError:
            logger.error("google-api-python-client not installed")
            return []

        youtube = build("youtube", "v3", developerKey=self.config.YOUTUBE_API_KEY)
        return self._fetch_channel_videos(youtube)

    @retry(max_attempts=3, base_delay=5)
    def _fetch_channel_videos(self, youtube) -> list[dict]:
        published_after = self.source.last_checked_at
        if published_after and published_after.tzinfo is None:
            published_after = published_after.replace(tzinfo=timezone.utc)

        kwargs = {
            "part": "snippet",
            "channelId": self.source.identifier,
            "order": "date",
            "maxResults": 15,
            "type": "video",
        }
        if published_after:
            kwargs["publishedAfter"] = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")

        response = youtube.search().list(**kwargs).execute()
        items = response.get("items", [])
        return [self.normalize(item) for item in items if item.get("id", {}).get("videoId")]

    def normalize(self, raw: dict) -> dict:
        snippet = raw.get("snippet", {})
        video_id = raw.get("id", {}).get("videoId", "")
        title = html.unescape(snippet.get("title", ""))
        description = html.unescape(snippet.get("description", ""))
        published_str = snippet.get("publishedAt", "")

        published_at = None
        if published_str:
            try:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except Exception:
                pass

        thumbnails = snippet.get("thumbnails", {})
        thumb = (
            thumbnails.get("maxres", {}).get("url")
            or thumbnails.get("high", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )

        return {
            "external_id": video_id,
            "title": title,
            "body": description[:1000],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "media_url": thumb,
            "published_at": published_at,
            "content_type": self.classify_content_type(title, description),
            "category": self.classify_category(title, description),
        }

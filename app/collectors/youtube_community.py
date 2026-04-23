"""
Scrapes YouTube Community tab posts (teacher announcements, schedule posts,
text updates from channels) without requiring any API key.
"""
import html
import json
import logging
import re
from datetime import datetime, timezone

from app.collectors.base import BaseCollector, retry

logger = logging.getLogger(__name__)

PCB_KEYWORDS = [
    "neet", "pcb", "physics", "chemistry", "biology", "class 12", "class12",
    "12th", "medical", "alakh", "dpp", "lecture", "yakeen", "schedule",
    "chapter", "batch", "today", "tomorrow", "test", "syllabus", "ncert",
    "live class", "free class", "result", "important",
]


def _extract_yt_initial_data(html_text: str) -> dict | None:
    """Parse ytInitialData JSON from YouTube HTML source."""
    marker = "var ytInitialData = "
    idx = html_text.find(marker)
    if idx == -1:
        return None
    start = idx + len(marker)
    depth = 0
    in_string = False
    escape_next = False
    chunk = html_text[start:start + 3_000_000]  # limit scan to 3MB
    for i, ch in enumerate(chunk):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(chunk[: i + 1])
                except json.JSONDecodeError:
                    return None
    return None


class YouTubeCommunityCollector(BaseCollector):
    source_type = "youtube_community"

    def collect(self) -> list[dict]:
        try:
            return self._fetch_posts()
        except Exception as e:
            logger.error(f"YouTube community failed for {self.source.identifier}: {e}")
            return []

    @retry(max_attempts=2, base_delay=5)
    def _fetch_posts(self) -> list[dict]:
        channel_id = self.source.identifier
        url = f"https://www.youtube.com/channel/{channel_id}/community"
        self.session.headers.update({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        })
        resp = self.session.get(url, timeout=20)
        if resp.status_code != 200:
            logger.warning(f"Community page {channel_id} returned {resp.status_code}")
            return []

        data = _extract_yt_initial_data(resp.text)
        if not data:
            logger.warning(f"No ytInitialData found for {channel_id}")
            return []

        posts = self._walk_community_posts(data)
        since = self.source.last_checked_at
        if since and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        results = []
        for post in posts:
            text = post.get("body", "")
            if not text or len(text) < 15:
                continue
            text_lower = text.lower()
            if not any(kw in text_lower for kw in PCB_KEYWORDS):
                continue
            results.append(self.normalize(post))

        logger.info(f"YT Community {channel_id}: collected {len(results)} posts")
        return results

    def _walk_community_posts(self, data: dict) -> list[dict]:
        """Walk the nested YouTube JSON to find community post objects."""
        posts = []
        try:
            tabs = (
                data.get("contents", {})
                .get("twoColumnBrowseResultsRenderer", {})
                .get("tabs", [])
            )
            for tab in tabs:
                renderer = tab.get("tabRenderer", {})
                content = renderer.get("content", {})
                sections = content.get("sectionListRenderer", {}).get("contents", [])
                for section in sections:
                    items = section.get("itemSectionRenderer", {}).get("contents", [])
                    for item in items:
                        # Two possible keys for community post wrapper
                        post_data = (
                            item.get("backstagePostThreadRenderer", {}).get("post", {})
                            or item.get("backstagePostRenderer", {})
                        )
                        if post_data:
                            parsed = self._parse_post(post_data)
                            if parsed:
                                posts.append(parsed)
        except Exception as e:
            logger.debug(f"Walk error: {e}")
        return posts

    def _parse_post(self, post_data: dict) -> dict | None:
        try:
            runs = post_data.get("contentText", {}).get("runs", [])
            text = "".join(run.get("text", "") for run in runs).strip()
            if not text:
                return None

            post_id = post_data.get("postId", "")

            # Try to get image
            media_url = ""
            attach = post_data.get("backstageAttachment", {})
            img_renderer = attach.get("backstageImageRenderer", {})
            if img_renderer:
                thumbs = img_renderer.get("image", {}).get("thumbnails", [])
                if thumbs:
                    media_url = thumbs[-1].get("url", "")

            channel_id = self.source.identifier
            url = (
                f"https://www.youtube.com/post/{post_id}"
                if post_id
                else f"https://www.youtube.com/channel/{channel_id}/community"
            )
            clean = html.unescape(text)
            return {
                "external_id": post_id or str(abs(hash(clean))),
                "title": clean[:150],
                "body": clean,
                "url": url,
                "media_url": media_url,
                "published_at": None,
            }
        except Exception:
            return None

    def normalize(self, raw: dict) -> dict:
        title = raw.get("title", "")
        body = raw.get("body", "")
        return {
            "external_id": str(raw.get("external_id", "")),
            "title": title[:500],
            "body": body,
            "url": raw.get("url", ""),
            "media_url": raw.get("media_url", ""),
            "published_at": raw.get("published_at"),
            "content_type": self.classify_content_type(title, body),
            "category": self.classify_category(title, body),
        }

import asyncio
import html
import logging
from datetime import datetime, timezone

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

PCB_KEYWORDS = [
    "neet", "pcb", "physics", "chemistry", "biology", "class 12", "class12",
    "12th", "medical", "alakh", "dpp", "lecture", "yakeen", "revision",
    "botany", "zoology", "organic", "inorganic", "mechanics", "electrostatics",
    "schedule", "test series", "syllabus", "chapter", "free class", "live class",
    "notes", "formula", "numericals", "mcq", "question bank",
]

# Skip messages that are just promotional spam
SPAM_PATTERNS = [
    "free course alert", "join now", "enroll now", "limited seats",
    "offer expires", "discount", "coupon", "hurry", "registration open",
    "pay now", "buy now", "purchase", "₹", "rs.", "price", "fee",
    "admission open", "new batch starting", "batch starting",
]


class TelegramCollector(BaseCollector):
    source_type = "telegram"

    def collect(self) -> list[dict]:
        if not self.config.TELEGRAM_API_ID or not self.config.TELEGRAM_API_HASH:
            logger.warning("Telegram API credentials not configured — skipping")
            return []
        try:
            return asyncio.run(self._async_collect())
        except Exception as e:
            logger.error(f"Telegram collection failed for {self.source.identifier}: {e}")
            return []

    async def _async_collect(self) -> list[dict]:
        try:
            from telethon import TelegramClient
            from telethon.tl.types import MessageMediaPhoto
        except ImportError:
            logger.error("telethon not installed")
            return []

        results = []
        session_name = self.config.TELEGRAM_SESSION or "pw_monitor"

        async with TelegramClient(
            session_name,
            int(self.config.TELEGRAM_API_ID),
            self.config.TELEGRAM_API_HASH,
        ) as client:
            channel = self.source.identifier
            since = self.source.last_checked_at
            if since and since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)

            try:
                async for message in client.iter_messages(channel, limit=50):
                    if since and message.date and message.date < since:
                        break
                    text = message.text or ""
                    if not text or len(text) < 20:
                        continue
                    text_lower = text.lower()
                    # Skip promotional spam
                    if any(sp in text_lower for sp in SPAM_PATTERNS):
                        continue
                    # Only keep PCB/NEET relevant messages
                    if not any(kw in text_lower for kw in PCB_KEYWORDS):
                        continue
                    media_url = ""
                    if message.media and isinstance(message.media, MessageMediaPhoto):
                        media_url = "[photo attached]"
                    clean_text = html.unescape(text)
                    results.append(self.normalize({
                        "external_id": str(message.id),
                        "title": clean_text[:120],
                        "body": clean_text,
                        "url": f"https://t.me/{channel.lstrip('@')}/{message.id}",
                        "media_url": media_url,
                        "published_at": message.date,
                    }))
            except Exception as e:
                logger.error(f"Error reading {channel}: {e}")

        return results

    def normalize(self, raw: dict) -> dict:
        title = raw.get("title", "")
        body = raw.get("body", "")
        return {
            "external_id": raw.get("external_id"),
            "title": title[:500],
            "body": body,
            "url": raw.get("url", ""),
            "media_url": raw.get("media_url", ""),
            "published_at": raw.get("published_at"),
            "content_type": self.classify_content_type(title, body),
            "category": self.classify_category(title, body),
        }

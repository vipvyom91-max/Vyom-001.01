import asyncio
import html
import logging
from datetime import datetime, timezone

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# These channels are 100% PCB/NEET-focused — collect everything except paid promos
DEDICATED_PCB_CHANNELS = {
    "pw_neet_pcb", "biologywallah", "pwchemistry", "pwphysics",
    "ncertwallah", "yakeenbatch", "pwyakeen", "pw_biology",
    "pwbiologyneet", "pwneetbiology",
}

# PCB keyword filter for general channels
PCB_KEYWORDS = [
    "neet", "pcb", "physics", "chemistry", "biology", "class 12", "class12",
    "12th", "medical", "alakh", "dpp", "lecture", "yakeen", "revision",
    "botany", "zoology", "organic", "inorganic", "mechanics", "electrostatics",
    "schedule", "test series", "syllabus", "chapter", "free class", "live class",
    "notes", "formula", "numericals", "mcq", "question bank", "ncert",
    "class tomorrow", "class today", "today class", "tomorrow class",
    "new video", "new lecture", "uploaded", "available now",
]

# Skip messages that are pure paid-course marketing (apply to ALL channels)
MARKETING_SKIP = [
    "₹", "rs.", "price drop", "buy now", "pay now", "purchase now",
    "limited time offer", "offer ends", "flat off", "% off",
]

# Skip for general channels only (dedicated channels ignore these)
GENERAL_SPAM = [
    "free course alert", "enroll now", "register now", "admission open",
    "join our", "registration open", "seats are filling", "hurry",
    "discount", "coupon code", "use code", "new batch starting",
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
            from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
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
            channel_key = channel.lstrip("@").lower()
            is_dedicated = channel_key in DEDICATED_PCB_CHANNELS

            since = self.source.last_checked_at
            if since and since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)

            try:
                async for message in client.iter_messages(channel, limit=100):
                    if since and message.date and message.date < since:
                        break

                    text = message.text or ""
                    if not text or len(text) < 15:
                        continue

                    text_lower = text.lower()

                    # Always skip paid marketing (applies to every channel)
                    if any(sp in text_lower for sp in MARKETING_SKIP):
                        continue

                    if is_dedicated:
                        # Dedicated PCB channel — skip only general spam/promos
                        if any(sp in text_lower for sp in GENERAL_SPAM):
                            continue
                        # Everything else from a dedicated channel is kept
                    else:
                        # General channel — require PCB keyword
                        if any(sp in text_lower for sp in GENERAL_SPAM):
                            continue
                        if not any(kw in text_lower for kw in PCB_KEYWORDS):
                            continue

                    media_url = ""
                    if message.media and isinstance(message.media, MessageMediaPhoto):
                        media_url = "[photo attached]"
                    elif message.media and isinstance(message.media, MessageMediaDocument):
                        media_url = "[document attached]"

                    clean_text = html.unescape(text)
                    results.append(self.normalize({
                        "external_id": str(message.id),
                        "title": clean_text[:150],
                        "body": clean_text,
                        "url": f"https://t.me/{channel.lstrip('@')}/{message.id}",
                        "media_url": media_url,
                        "published_at": message.date,
                    }))
            except Exception as e:
                logger.error(f"Error reading {channel}: {e}")

        logger.info(f"Telegram {channel}: collected {len(results)} messages")
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
            "content_type": self._classify_telegram(title, body),
            "category": self.classify_category(title, body),
        }

    def _classify_telegram(self, title: str, body: str) -> str:
        text = (title + " " + body).lower()
        if any(k in text for k in ["dpp", "daily practice", "practice problem", "question bank"]):
            return "dpp"
        if any(k in text for k in ["schedule", "timetable", "time table", "today class", "tomorrow class",
                                     "class at", "pm class", "am class", "class time"]):
            return "schedule"
        if any(k in text for k in ["test series", "mock test", "test on", "exam on", "result"]):
            return "announcement"
        if any(k in text for k in ["lecture", "class", "session", "chapter", "video", "uploaded", "live"]):
            return "lecture"
        if any(k in text for k in ["tip", "trick", "shortcut", "revision", "formula", "notes"]):
            return "tip"
        if any(k in text for k in ["important", "update", "notice", "announce", "new"]):
            return "announcement"
        return "general"

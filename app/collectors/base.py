import hashlib
import logging
import time
from datetime import datetime
from functools import wraps

import requests

logger = logging.getLogger(__name__)


def retry(max_attempts=3, base_delay=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait = base_delay * (attempt + 1)
                    logger.warning(f"Attempt {attempt+1} failed: {e}. Retrying in {wait}s…")
                    time.sleep(wait)
        return wrapper
    return decorator


class BaseCollector:
    source_type: str = ""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0 Safari/537.36",
    ]

    def __init__(self, source, config):
        self.source = source
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = self.USER_AGENTS[0]
        self.session.headers["Accept-Language"] = "en-IN,en;q=0.9,hi;q=0.8"

    # ── override in subclass ──────────────────────────────────────────────
    def collect(self) -> list[dict]:
        raise NotImplementedError

    def normalize(self, raw: dict) -> dict:
        raise NotImplementedError

    # ── shared helpers ────────────────────────────────────────────────────
    @staticmethod
    def make_hash(title: str, body: str) -> str:
        return hashlib.sha256(f"{title}{body}".encode()).hexdigest()

    def is_duplicate(self, session, external_id: str, content_hash: str) -> bool:
        from app.models import Update
        if external_id:
            exists = session.query(Update).filter_by(
                source_id=self.source.id,
                external_id=external_id
            ).first()
            if exists:
                return True
        if content_hash:
            exists = session.query(Update).filter_by(
                content_hash=content_hash
            ).first()
            if exists:
                return True
        return False

    def save_updates(self, db_session, updates: list[dict]) -> int:
        from app.models import Update, CollectionLog
        saved = 0
        for item in updates:
            try:
                h = self.make_hash(item.get("title", ""), item.get("body", ""))
                if self.is_duplicate(db_session, item.get("external_id"), h):
                    continue
                update = Update(
                    source_id=self.source.id,
                    external_id=item.get("external_id"),
                    content_hash=h,
                    title=item.get("title", "")[:500],
                    body=item.get("body", ""),
                    url=item.get("url", ""),
                    media_url=item.get("media_url", ""),
                    published_at=item.get("published_at"),
                    content_type=item.get("content_type", "general"),
                    category=item.get("category"),
                )
                db_session.add(update)
                saved += 1
            except Exception as e:
                logger.error(f"Failed to save update: {e}")
                db_session.rollback()

        try:
            db_session.commit()
            log = CollectionLog(
                source_id=self.source.id,
                source_name=self.source.name,
                status="success",
                items_collected=saved,
            )
            db_session.add(log)
            db_session.commit()
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            db_session.rollback()

        return saved

    def classify_content_type(self, title: str, body: str = "") -> str:
        text = (title + " " + body).lower()
        if any(k in text for k in ["dpp", "daily practice", "practice problem"]):
            return "dpp"
        if any(k in text for k in ["schedule", "timetable", "time table", "routine"]):
            return "schedule"
        if any(k in text for k in ["lecture", "class", "session", "chapter"]):
            return "lecture"
        if any(k in text for k in ["tip", "trick", "strategy", "shortcut", "revision"]):
            return "tip"
        if any(k in text for k in ["announce", "notification", "alert", "important"]):
            return "announcement"
        return "general"

    def classify_category(self, title: str, body: str = "") -> str:
        text = (title + " " + body).lower()
        if any(k in text for k in ["physics", "mechanic", "electro", "optic", "thermodynamic", "wave"]):
            return "Physics"
        if any(k in text for k in ["chemistry", "organic", "inorganic", "reaction", "mole", "equilibrium"]):
            return "Chemistry"
        if any(k in text for k in ["biology", "botany", "zoology", "cell", "genetics", "ecology", "anatomy"]):
            return "Biology"
        return "General"

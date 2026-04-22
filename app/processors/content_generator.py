import logging
from datetime import datetime

from app.processors.caption_ai import CaptionAI
from app.processors.image_creator import ImageCreator, CONTENT_TYPE_TEMPLATE_MAP

logger = logging.getLogger(__name__)

RELEVANCE_KEYWORDS = [
    "neet", "pcb", "class 12", "class12", "12th", "dpp", "lecture",
    "biology", "chemistry", "physics", "schedule", "batch", "alakh",
    "yakeen", "pw", "physicsWallah", "medical", "revision",
]
BONUS_KEYWORDS = ["important", "live", "free", "new", "today", "just", "launch"]


class ContentGenerator:
    def __init__(self, config):
        self.config = config
        self.caption_ai = CaptionAI(config)
        self.image_creator = ImageCreator(config)

    def process_update(self, update) -> "Post | None":
        from app.models import Post
        from app import db

        score = self._score_relevance(update)
        update.relevance_score = score
        update.is_processed = True

        if score < 0.35:
            logger.debug(f"Update {update.id} scored {score:.2f} — skipping auto-post")
            return None

        # Generate caption via Claude (or fallback)
        ai_result = self.caption_ai.generate_caption(update, "feed")

        # Override category from AI if it looks valid
        if ai_result.get("category") and ai_result["category"] in ("Physics", "Chemistry", "Biology", "General"):
            update.category = ai_result["category"]

        # Generate image
        template = CONTENT_TYPE_TEMPLATE_MAP.get(update.content_type or "general", "lecture_update")
        image_path = ""
        try:
            image_path = self.image_creator.create_post_image(update, template)
        except Exception as e:
            logger.error(f"Image creation failed: {e}")

        post = Post(
            update_id=update.id,
            caption=ai_result["caption"],
            template_name=template,
            image_path=image_path,
            post_type="feed",
            status="draft",
            ai_caption_used=True,
        )
        post.hashtags = ai_result["hashtags"]
        return post

    def _score_relevance(self, update) -> float:
        text = (
            (update.title or "") + " " + (update.body or "")
        ).lower()

        keyword_hits = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text)
        bonus_hits = sum(1 for kw in BONUS_KEYWORDS if kw in text)

        score = min(keyword_hits / 6, 0.55)
        score += min(bonus_hits / 4, 0.15)

        source_bonus = {
            "youtube": 0.20,
            "telegram": 0.15,
            "twitter": 0.10,
            "website": 0.10,
            "rss": 0.05,
        }
        if update.source:
            score += source_bonus.get(update.source.source_type, 0)

        type_bonus = {"lecture": 0.10, "dpp": 0.10, "schedule": 0.05}
        score += type_bonus.get(update.content_type or "", 0)

        return min(round(score, 3), 1.0)

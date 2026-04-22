import json
import hashlib
from datetime import datetime
from app import db


class Source(db.Model):
    __tablename__ = "sources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)   # youtube|telegram|twitter|website|rss
    identifier = db.Column(db.String(255), nullable=False)   # channel ID, URL, handle
    is_active = db.Column(db.Boolean, default=True)
    last_checked_at = db.Column(db.DateTime, default=datetime(2000, 1, 1))
    check_interval_hours = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    metadata_json = db.Column(db.Text)                       # JSON blob for source-specific config

    updates = db.relationship("Update", backref="source", lazy=True)

    def get_meta(self):
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except Exception:
            return {}

    def set_meta(self, data):
        self.metadata_json = json.dumps(data)

    def __repr__(self):
        return f"<Source {self.name} ({self.source_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type,
            "identifier": self.identifier,
            "is_active": self.is_active,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "check_interval_hours": self.check_interval_hours,
            "created_at": self.created_at.isoformat(),
        }


class Update(db.Model):
    __tablename__ = "updates"

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"), nullable=False)
    external_id = db.Column(db.String(255))                  # stable ID from the source
    content_hash = db.Column(db.String(64), index=True)      # SHA-256 for fuzzy dedup
    title = db.Column(db.String(500))
    body = db.Column(db.Text)
    url = db.Column(db.String(512))
    media_url = db.Column(db.String(512))                    # thumbnail / image URL
    published_at = db.Column(db.DateTime)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)
    content_type = db.Column(db.String(50), default="general")  # lecture|dpp|schedule|tip|announcement|general
    category = db.Column(db.String(100))                     # Physics|Chemistry|Biology|General
    relevance_score = db.Column(db.Float, default=0.0)       # 0-1
    is_processed = db.Column(db.Boolean, default=False)
    is_queued = db.Column(db.Boolean, default=False)
    is_starred = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint("source_id", "external_id", name="uq_source_external"),)

    posts = db.relationship("Post", backref="update", lazy=True)

    @staticmethod
    def make_hash(title: str, body: str) -> str:
        return hashlib.sha256(f"{title}{body}".encode()).hexdigest()

    def __repr__(self):
        return f"<Update {self.id}: {self.title[:40]}>"

    def to_dict(self):
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source.name if self.source else None,
            "source_type": self.source.source_type if self.source else None,
            "title": self.title,
            "body": self.body,
            "url": self.url,
            "media_url": self.media_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "collected_at": self.collected_at.isoformat(),
            "content_type": self.content_type,
            "category": self.category,
            "relevance_score": self.relevance_score,
            "is_processed": self.is_processed,
            "is_queued": self.is_queued,
            "is_starred": self.is_starred,
        }


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    update_id = db.Column(db.Integer, db.ForeignKey("updates.id"), nullable=True)
    caption = db.Column(db.Text)
    _hashtags = db.Column("hashtags", db.Text)
    image_path = db.Column(db.String(512))
    post_type = db.Column(db.String(50), default="feed")     # feed|story|carousel
    template_name = db.Column(db.String(100))
    status = db.Column(db.String(50), default="draft")       # draft|queued|scheduled|posted|failed
    instagram_post_id = db.Column(db.String(100))
    ai_caption_used = db.Column(db.Boolean, default=False)
    editor_notes = db.Column(db.Text)
    error_log = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scheduled_posts = db.relationship("ScheduledPost", backref="post", lazy=True)

    @property
    def hashtags(self):
        try:
            return json.loads(self._hashtags) if self._hashtags else []
        except Exception:
            return []

    @hashtags.setter
    def hashtags(self, value):
        self._hashtags = json.dumps(value if isinstance(value, list) else [])

    @property
    def full_caption(self):
        tags = " ".join(self.hashtags)
        return f"{self.caption}\n\n{tags}".strip() if self.caption else ""

    def __repr__(self):
        return f"<Post {self.id} ({self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "update_id": self.update_id,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "full_caption": self.full_caption,
            "image_path": self.image_path,
            "post_type": self.post_type,
            "template_name": self.template_name,
            "status": self.status,
            "instagram_post_id": self.instagram_post_id,
            "ai_caption_used": self.ai_caption_used,
            "editor_notes": self.editor_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScheduledPost(db.Model):
    __tablename__ = "scheduled_posts"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    posted_at = db.Column(db.DateTime)
    attempt_count = db.Column(db.Integer, default=0)
    last_error = db.Column(db.Text)
    status = db.Column(db.String(50), default="pending")     # pending|posting|done|failed

    def __repr__(self):
        return f"<ScheduledPost {self.id} at {self.scheduled_at}>"

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "scheduled_at": self.scheduled_at.isoformat(),
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "attempt_count": self.attempt_count,
            "last_error": self.last_error,
            "status": self.status,
        }


class CollectionLog(db.Model):
    __tablename__ = "collection_logs"

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"), nullable=True)
    source_name = db.Column(db.String(100))
    status = db.Column(db.String(50))                        # success|error
    items_collected = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    ran_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "source_name": self.source_name,
            "status": self.status,
            "items_collected": self.items_collected,
            "error_message": self.error_message,
            "ran_at": self.ran_at.isoformat(),
        }


class DailyStat(db.Model):
    __tablename__ = "daily_stats"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    updates_collected = db.Column(db.Integer, default=0)
    posts_created = db.Column(db.Integer, default=0)
    posts_published = db.Column(db.Integer, default=0)
    api_calls_made = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "updates_collected": self.updates_collected,
            "posts_created": self.posts_created,
            "posts_published": self.posts_published,
            "api_calls_made": self.api_calls_made,
        }

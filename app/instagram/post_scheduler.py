import logging
from datetime import datetime, timedelta, timezone

import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# Best posting hours for Indian student audience (IST)
OPTIMAL_HOURS_IST = [7, 12, 17, 20, 22]   # 7am, 12pm, 5pm, 8pm, 10pm


class PostScheduler:
    def __init__(self, config):
        self.config = config

    def suggest_next_slot(self, after: datetime = None) -> datetime:
        """Return next available optimal IST posting time as UTC datetime."""
        from app.models import ScheduledPost
        from app import db

        now_utc = after or datetime.utcnow().replace(tzinfo=timezone.utc)
        now_ist = now_utc.astimezone(IST)

        candidate = now_ist.replace(second=0, microsecond=0)

        for _ in range(14):  # scan up to 14 days ahead
            for h in OPTIMAL_HOURS_IST:
                slot_ist = candidate.replace(hour=h, minute=0)
                if slot_ist <= now_ist:
                    continue
                slot_utc = slot_ist.astimezone(timezone.utc)
                # Check no other post is within 30 minutes of this slot
                window_start = slot_utc - timedelta(minutes=30)
                window_end = slot_utc + timedelta(minutes=30)
                conflict = ScheduledPost.query.filter(
                    ScheduledPost.scheduled_at >= window_start,
                    ScheduledPost.scheduled_at <= window_end,
                    ScheduledPost.status.in_(["pending", "posting"]),
                ).first()
                if not conflict:
                    return slot_utc.replace(tzinfo=None)
            candidate = (candidate + timedelta(days=1)).replace(hour=0)

        # Last resort: 3 hours from now
        return (now_utc + timedelta(hours=3)).replace(tzinfo=None)

    def queue_post(self, post, scheduled_at: datetime = None):
        from app.models import ScheduledPost
        from app import db

        if scheduled_at is None:
            scheduled_at = self.suggest_next_slot()

        sp = ScheduledPost(
            post_id=post.id,
            scheduled_at=scheduled_at,
            status="pending",
        )
        post.status = "scheduled"
        db.session.add(sp)
        db.session.commit()
        return sp

    def run_due_posts(self, app):
        """Called every 5 min by APScheduler. Posts anything that's due."""
        from app.models import ScheduledPost, Post
        from app import db
        from app.instagram.poster import InstagramPoster

        now = datetime.utcnow()
        due = ScheduledPost.query.filter(
            ScheduledPost.scheduled_at <= now,
            ScheduledPost.status == "pending",
        ).all()

        if not due:
            return

        poster = InstagramPoster(self.config)
        for sp in due:
            sp.status = "posting"
            sp.attempt_count += 1
            db.session.commit()
            try:
                post = sp.post
                ig_id = poster.post_feed_image(post, app)
                post.status = "posted"
                post.instagram_post_id = ig_id
                sp.status = "done"
                sp.posted_at = datetime.utcnow()
                logger.info(f"Post {post.id} published → IG {ig_id}")
            except Exception as e:
                logger.error(f"Failed to post {sp.post_id}: {e}")
                sp.last_error = str(e)
                sp.status = "failed" if sp.attempt_count >= 3 else "pending"
                sp.post.status = "failed" if sp.attempt_count >= 3 else "scheduled"
                sp.scheduled_at = datetime.utcnow() + timedelta(minutes=15)
            finally:
                db.session.commit()

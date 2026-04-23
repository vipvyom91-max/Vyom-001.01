"""
APScheduler configuration.
Runs data collection every COLLECTION_INTERVAL_HOURS (default: 1 hour).
Adds small delays between sources to avoid rate limiting.
"""
import logging
import time
import random
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

# Source types that need a delay between calls to avoid rate limits
_RATE_LIMITED_TYPES = {"telegram", "youtube", "youtube_community"}


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        import pytz
        _scheduler = BackgroundScheduler(timezone=pytz.utc)
    return _scheduler


def start_scheduler(app):
    scheduler = get_scheduler()
    interval_h = app.config.get("COLLECTION_INTERVAL_HOURS", 1)

    scheduler.add_job(
        func=_run_collection,
        trigger=IntervalTrigger(hours=interval_h),
        id="data_collection",
        name="Collect PW Updates",
        replace_existing=True,
        args=[app],
    )

    if not scheduler.running:
        scheduler.start()
        logger.info(f"APScheduler started — collection every {interval_h}h")


def _run_collection(app):
    """Runs inside APScheduler thread — pushes Flask app context."""
    with app.app_context():
        from app.models import Source, Update, DailyStat
        from app.collectors import get_collector_for_source
        from app.processors.content_generator import ContentGenerator
        from app import db
        from config import Config

        sources = Source.query.filter_by(is_active=True).all()
        if not sources:
            logger.info("No active sources configured")
            return

        gen = ContentGenerator(Config)
        total_collected = 0
        total_posts = 0

        from app.models import CollectionLog

        for source in sources:
            log = CollectionLog(source_id=source.id, source_name=source.name)
            try:
                collector = get_collector_for_source(source, Config)
                raw_items = collector.collect()
                saved = collector.save_updates(db.session, raw_items)
                total_collected += saved

                new_updates = Update.query.filter_by(
                    source_id=source.id, is_processed=False
                ).all()
                posts_created = 0
                for upd in new_updates:
                    post = gen.process_update(upd)
                    if post:
                        db.session.add(post)
                        posts_created += 1
                total_posts += posts_created

                source.last_checked_at = datetime.utcnow()
                log.status = "success"
                log.items_collected = saved
                db.session.add(log)
                db.session.commit()

                if saved or posts_created:
                    logger.info(f"[{source.name}] saved={saved} posts={posts_created}")

                # Brief pause between rate-limited sources
                if source.source_type in _RATE_LIMITED_TYPES:
                    time.sleep(random.uniform(1.0, 2.5))

            except Exception as e:
                logger.error(f"Collection failed for {source.name}: {e}")
                db.session.rollback()
                log.status = "error"
                log.error_message = str(e)[:500]
                log.items_collected = 0
                try:
                    db.session.add(log)
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        logger.info(f"Collection complete — updates={total_collected} posts={total_posts}")

        # Update daily stats
        try:
            from datetime import date
            today = date.today()
            stat = DailyStat.query.filter_by(date=today).first()
            if not stat:
                stat = DailyStat(date=today)
                db.session.add(stat)
            stat.updates_collected = (stat.updates_collected or 0) + total_collected
            stat.posts_created = (stat.posts_created or 0) + total_posts
            db.session.commit()
        except Exception as e:
            logger.error(f"Stats update failed: {e}")

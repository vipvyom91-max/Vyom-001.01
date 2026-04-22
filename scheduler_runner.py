"""
APScheduler configuration.
Started inside the Flask application factory (app/__init__.py).
Two jobs:
  1. Data collection — every COLLECTION_INTERVAL_HOURS hours
  2. Scheduled post executor — every 5 minutes
"""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
    return _scheduler


def start_scheduler(app):
    scheduler = get_scheduler()

    interval_h = app.config.get("COLLECTION_INTERVAL_HOURS", 3)

    scheduler.add_job(
        func=_run_collection,
        trigger=IntervalTrigger(hours=interval_h),
        id="data_collection",
        name="Collect PW Updates",
        replace_existing=True,
        args=[app],
    )

    scheduler.add_job(
        func=_run_scheduled_posts,
        trigger=IntervalTrigger(minutes=5),
        id="post_publisher",
        name="Publish Scheduled Posts",
        replace_existing=True,
        args=[app],
    )

    if not scheduler.running:
        scheduler.start()
        logger.info(f"APScheduler started — collection every {interval_h}h, publisher every 5m")


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

        for source in sources:
            try:
                collector = get_collector_for_source(source, Config)
                raw_items = collector.collect()
                saved = collector.save_updates(db.session, raw_items)
                total_collected += saved

                # Process newly collected updates
                new_updates = Update.query.filter_by(
                    source_id=source.id, is_processed=False
                ).all()
                posts_created = 0
                for upd in new_updates:
                    post = gen.process_update(upd)
                    if post:
                        db.session.add(post)
                        posts_created += 1
                db.session.commit()

                source.last_checked_at = datetime.utcnow()
                db.session.commit()

                logger.info(
                    f"[{source.name}] collected={saved} posts_created={posts_created}"
                )
            except Exception as e:
                logger.error(f"Collection failed for {source.name}: {e}")
                db.session.rollback()

        # Update daily stats
        try:
            from datetime import date
            today = date.today()
            stat = DailyStat.query.filter_by(date=today).first()
            if not stat:
                stat = DailyStat(date=today)
                db.session.add(stat)
            stat.updates_collected += total_collected
            db.session.commit()
        except Exception as e:
            logger.error(f"Stats update failed: {e}")


def _run_scheduled_posts(app):
    """Publish any ScheduledPosts that are due."""
    with app.app_context():
        from app.instagram.post_scheduler import PostScheduler
        from config import Config
        sched = PostScheduler(Config)
        sched.run_due_posts(app)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="dashboard/templates",
        static_folder="dashboard/static",
        static_url_path="/static",
    )
    app.config.from_object(config_class)

    db.init_app(app)

    from app.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    with app.app_context():
        db.create_all()
        _seed_default_sources()
        _start_background_scheduler(app)

    return app


def _seed_default_sources():
    """Add default PW sources on first run (idempotent)."""
    from app.models import Source
    if Source.query.count() > 0:
        return
    defaults = [
        ("PW Alakh Pandey (YouTube)", "youtube",  "UCk0Kvsaln4I4v9AKBb3FXOQ"),
        ("PW Official (YouTube)",     "youtube",  "UCb1RuCdQk8i-A4RYkvBJpZA"),
        ("PW Biology (YouTube)",      "youtube",  "UCWPm8bRzqZbZYhBEGS0anEA"),
        ("PW YouTube (RSS fallback)", "rss",      "https://www.youtube.com/feeds/videos.xml?channel_id=UCk0Kvsaln4I4v9AKBb3FXOQ"),
        ("PW Official (Twitter/X)",   "twitter",  "PhysicsWallah"),
        ("Alakh Pandey (Twitter/X)",  "twitter",  "AlakhPandey01"),
        ("PW Website",                "website",  "https://pw.live"),
        ("PW Courses",                "website",  "https://pw.live/courses"),
    ]
    for name, stype, ident in defaults:
        src = Source(name=name, source_type=stype, identifier=ident)
        db.session.add(src)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _start_background_scheduler(app):
    try:
        from scheduler_runner import start_scheduler
        start_scheduler(app)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Scheduler not started: {e}")

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

ALL_DEFAULT_SOURCES = [
    # ── YouTube (needs API key) ───────────────────────────────────────────
    ("PW Alakh Pandey (YouTube)",   "youtube",  "UCiGyWN6DEbnj2alu7iapuKQ"),
    ("PW NEET (YouTube)",           "youtube",  "UCGw8iWmsw1cPlfcrww-3C0g"),
    ("NCERT Wallah (YouTube)",      "youtube",  "UC8zCnnfhz-dvIpVdZ1CheuA"),

    # ── YouTube RSS (no API key needed) ───────────────────────────────────
    ("PW Alakh Pandey (RSS)",       "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UCiGyWN6DEbnj2alu7iapuKQ"),
    ("PW NEET (RSS)",               "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UCGw8iWmsw1cPlfcrww-3C0g"),
    ("NCERT Wallah (RSS)",          "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UC8zCnnfhz-dvIpVdZ1CheuA"),

    # ── Google News RSS — news articles about PW ─────────────────────────
    ("PW News – NEET",              "rss", "https://news.google.com/rss/search?q=Physics+Wallah+NEET+2025&hl=en-IN&gl=IN&ceid=IN:en"),
    ("PW News – Class 12",          "rss", "https://news.google.com/rss/search?q=Physics+Wallah+class+12+PCB&hl=en-IN&gl=IN&ceid=IN:en"),
    ("NEET 2025 Updates",           "rss", "https://news.google.com/rss/search?q=NEET+2025+exam+syllabus+update&hl=en-IN&gl=IN&ceid=IN:en"),

    # ── Telegram channels ─────────────────────────────────────────────────
    ("PW Official Telegram",        "telegram", "physicswallah"),
    ("Alakh Pandey Telegram",       "telegram", "AlakhPandey"),
    ("PW Live Telegram",            "telegram", "pwlive"),
    ("PW NEET PCB Telegram",        "telegram", "pw_neet_pcb"),
    ("Biology Wallah Telegram",     "telegram", "BiologyWallah"),
    ("NCERT Wallah Telegram",       "telegram", "ncertwallah"),
    ("PW Chemistry Telegram",       "telegram", "PWchemistry"),
    ("PW Physics Telegram",         "telegram", "PWphysics"),
    ("Yakeen Batch Telegram",       "telegram", "yakeenbatch"),
    ("PW Yakeen Telegram",          "telegram", "pwyakeen"),
]


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
    """Add default PW sources (idempotent — skips existing by name)."""
    from app.models import Source
    existing_names = {s.name for s in Source.query.all()}
    added = 0
    for name, stype, ident in ALL_DEFAULT_SOURCES:
        if name not in existing_names:
            db.session.add(Source(name=name, source_type=stype, identifier=ident))
            added += 1
    if added:
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

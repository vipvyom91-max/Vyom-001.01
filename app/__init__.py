from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

# ── Sources that are no longer valid — disable them on startup ────────────
_DEAD_IDENTIFIERS = {
    "https://pw.live/study-material",
    "https://pw.live/videos",
    "https://pw.live",
}

ALL_DEFAULT_SOURCES = [
    # ── YouTube API (needs YOUTUBE_API_KEY) ───────────────────────────────
    ("PW Alakh Pandey (YouTube)",        "youtube",           "UCiGyWN6DEbnj2alu7iapuKQ"),
    ("PW NEET Channel (YouTube)",        "youtube",           "UCGw8iWmsw1cPlfcrww-3C0g"),
    ("NCERT Wallah (YouTube)",           "youtube",           "UC8zCnnfhz-dvIpVdZ1CheuA"),

    # ── YouTube RSS (no API key needed) ───────────────────────────────────
    ("PW Alakh Pandey (RSS)",            "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UCiGyWN6DEbnj2alu7iapuKQ"),
    ("PW NEET (RSS)",                    "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UCGw8iWmsw1cPlfcrww-3C0g"),
    ("NCERT Wallah (RSS)",               "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UC8zCnnfhz-dvIpVdZ1CheuA"),

    # ── YouTube Community Posts (teacher announcements, schedules) ────────
    ("PW Alakh Pandey (Community)",      "youtube_community", "UCiGyWN6DEbnj2alu7iapuKQ"),
    ("PW NEET (Community)",              "youtube_community", "UCGw8iWmsw1cPlfcrww-3C0g"),
    ("NCERT Wallah (Community)",         "youtube_community", "UC8zCnnfhz-dvIpVdZ1CheuA"),

    # ── Telegram — PW official channels ──────────────────────────────────
    ("PW Official Telegram",             "telegram", "physicswallah"),
    ("Alakh Pandey Telegram",            "telegram", "AlakhPandey"),
    ("PW Live Telegram",                 "telegram", "pwlive"),
    ("PW NEET PCB Telegram",             "telegram", "pw_neet_pcb"),
    ("Biology Wallah Telegram",          "telegram", "BiologyWallah"),
    ("NCERT Wallah Telegram",            "telegram", "ncertwallah"),
    ("PW Chemistry Telegram",            "telegram", "PWchemistry"),
    ("PW Physics Telegram",              "telegram", "PWphysics"),
    ("Yakeen Batch Telegram",            "telegram", "yakeenbatch"),
    ("PW Yakeen Telegram",               "telegram", "pwyakeen"),
    ("PW English Telegram",              "telegram", "pwenglish"),
    ("PW Foundation Telegram",           "telegram", "PWFoundation"),
    ("PW Arjuna Telegram",               "telegram", "PWArjuna"),
    ("PW Pariksha Telegram",             "telegram", "PW_pariksha"),
    ("PW Schedule Telegram",             "telegram", "pwschedule"),
    ("PW Updates Telegram",              "telegram", "PWupdates"),
    ("PW Maths Telegram",                "telegram", "PWmaths"),
    ("PW Biology NEET Telegram",         "telegram", "PWbiologyneet"),
    ("PW Notes Telegram",                "telegram", "pwnotes"),
    ("PW DPP Telegram",                  "telegram", "pw_dpp"),
    ("Yakeen NEET 2025 Telegram",        "telegram", "yakeenneet2025"),
    ("Yakeen NEET 2026 Telegram",        "telegram", "yakeenneet2026"),
    ("PW Lakshya Telegram",              "telegram", "PWLakshya"),
    ("PW Vidyapeeth Telegram",           "telegram", "PWVidyapeeth"),

    # ── Google News RSS — articles about PW/NEET ─────────────────────────
    ("GNews: Physics Wallah NEET",       "rss", "https://news.google.com/rss/search?q=Physics+Wallah+NEET+2025&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: PW Class 12 PCB",           "rss", "https://news.google.com/rss/search?q=Physics+Wallah+class+12+PCB&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: Alakh Pandey",              "rss", "https://news.google.com/rss/search?q=Alakh+Pandey+Physics+Wallah+new&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: NEET 2025 Exam",            "rss", "https://news.google.com/rss/search?q=NEET+UG+2025+exam+date+result+update&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: NEET Preparation",          "rss", "https://news.google.com/rss/search?q=NEET+2025+preparation+biology+chemistry+physics&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: NTA NEET",                  "rss", "https://news.google.com/rss/search?q=NTA+NEET+2025+notification+syllabus&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: PW New Batch",              "rss", "https://news.google.com/rss/search?q=Physics+Wallah+new+batch+free+class&hl=en-IN&gl=IN&ceid=IN:en"),

    # ── Education News RSS ────────────────────────────────────────────────
    ("NDTV Education",                   "rss", "https://www.ndtv.com/rss/education"),
    ("Times of India Education",         "rss", "https://timesofindia.indiatimes.com/rssfeeds/913168846.cms"),
    ("Hindustan Times Education",        "rss", "https://www.hindustantimes.com/feeds/rss/education/rssfeed.xml"),
    ("India Today Education",            "rss", "https://www.indiatoday.in/rss/1206579"),
    ("AglaSem Education",                "rss", "https://aglasem.com/feed/"),
    ("Jagranjosh NEET",                  "rss", "https://www.jagranjosh.com/articles/neet-articles.feed"),
    ("Careers360 NEET",                  "rss", "https://medicine.careers360.com/articles?format=rss"),
    ("Shiksha NEET",                     "rss", "https://www.shiksha.com/medicine-health-sciences/neet/rss"),
    ("CollegeDekho NEET",                "rss", "https://www.collegedekho.com/news/category/neet/feed/"),
    ("Embibe NEET",                      "rss", "https://www.embibe.com/exams/neet/feed/"),
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
        _cleanup_dead_sources()
        _start_background_scheduler(app)
        _auto_collect_if_empty(app)

    return app


def _seed_default_sources():
    """Add any missing default sources on every startup (idempotent by name)."""
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
            import logging
            logging.getLogger(__name__).info(f"Seeded {added} new sources")
        except Exception:
            db.session.rollback()


def _cleanup_dead_sources():
    """Disable sources pointing to known-dead URLs."""
    from app.models import Source
    changed = False
    for src in Source.query.filter_by(is_active=True).all():
        if src.identifier in _DEAD_IDENTIFIERS:
            src.is_active = False
            changed = True
    if changed:
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


def _auto_collect_if_empty(app):
    """On first ever run (0 updates in DB), kick off an RSS-only collect in background."""
    import threading, logging
    from app.models import Update
    log = logging.getLogger(__name__)
    if Update.query.count() > 0:
        return

    def _run():
        with app.app_context():
            try:
                from app.models import Source
                from app.collectors import get_collector_for_source
                from app.processors.content_generator import ContentGenerator
                from config import Config
                rss_sources = Source.query.filter_by(is_active=True, source_type="rss").all()
                gen = ContentGenerator(Config)
                total = 0
                for src in rss_sources[:15]:  # first 15 RSS sources
                    try:
                        col = get_collector_for_source(src, Config)
                        items = col.collect()
                        saved = col.save_updates(db.session, items)
                        total += saved
                        for upd in Update.query.filter_by(source_id=src.id, is_processed=False).all():
                            post = gen.process_update(upd)
                            if post:
                                db.session.add(post)
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                log.info(f"Auto first-run collect: {total} updates from RSS")
            except Exception as e:
                log.warning(f"Auto collect failed: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    import logging
    logging.getLogger(__name__).info("First run detected — auto-collecting RSS sources in background...")

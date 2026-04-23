from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

ALL_DEFAULT_SOURCES = [
    # ════════════════════════════════════════════════════════════════════════
    # YOUTUBE — needs API key, but RSS fallbacks work without any key
    # ════════════════════════════════════════════════════════════════════════
    ("PW Alakh Pandey (YouTube)",        "youtube", "UCiGyWN6DEbnj2alu7iapuKQ"),
    ("PW NEET Channel (YouTube)",        "youtube", "UCGw8iWmsw1cPlfcrww-3C0g"),
    ("NCERT Wallah (YouTube)",           "youtube", "UC8zCnnfhz-dvIpVdZ1CheuA"),

    # ════════════════════════════════════════════════════════════════════════
    # YOUTUBE RSS — works without any API key
    # ════════════════════════════════════════════════════════════════════════
    ("PW Alakh Pandey (RSS)",            "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UCiGyWN6DEbnj2alu7iapuKQ"),
    ("PW NEET (RSS)",                    "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UCGw8iWmsw1cPlfcrww-3C0g"),
    ("NCERT Wallah (RSS)",               "rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UC8zCnnfhz-dvIpVdZ1CheuA"),

    # ════════════════════════════════════════════════════════════════════════
    # TELEGRAM — PW official channels
    # ════════════════════════════════════════════════════════════════════════
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
    # More PW Telegram channels
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
    ("Physics Wallah Study Telegram",    "telegram", "physicsWallahstudy"),
    ("Yakeen NEET 2025 Telegram",        "telegram", "yakeenneet2025"),
    ("Yakeen NEET 2026 Telegram",        "telegram", "yakeenneet2026"),
    ("PW Lakshya Telegram",              "telegram", "PWLakshya"),
    ("PW Vidyapeeth Telegram",           "telegram", "PWVidyapeeth"),

    # ════════════════════════════════════════════════════════════════════════
    # GOOGLE NEWS RSS — news articles and blog posts about PW/NEET
    # ════════════════════════════════════════════════════════════════════════
    ("GNews: Physics Wallah NEET",       "rss", "https://news.google.com/rss/search?q=Physics+Wallah+NEET+2025&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: PW Class 12 PCB",           "rss", "https://news.google.com/rss/search?q=Physics+Wallah+class+12+PCB&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: Alakh Pandey",              "rss", "https://news.google.com/rss/search?q=Alakh+Pandey+Physics+Wallah+new&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: NEET 2025 Exam",            "rss", "https://news.google.com/rss/search?q=NEET+UG+2025+exam+date+result+update&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: NEET Preparation",          "rss", "https://news.google.com/rss/search?q=NEET+2025+preparation+biology+chemistry+physics&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: NTA NEET",                  "rss", "https://news.google.com/rss/search?q=NTA+NEET+2025+notification+syllabus&hl=en-IN&gl=IN&ceid=IN:en"),
    ("GNews: PW New Batch",              "rss", "https://news.google.com/rss/search?q=Physics+Wallah+new+batch+free+class&hl=en-IN&gl=IN&ceid=IN:en"),

    # ════════════════════════════════════════════════════════════════════════
    # EDUCATION NEWS RSS — major Indian news sites education sections
    # ════════════════════════════════════════════════════════════════════════
    ("NDTV Education",                   "rss", "https://www.ndtv.com/rss/education"),
    ("Times of India Education",         "rss", "https://timesofindia.indiatimes.com/rssfeeds/913168846.cms"),
    ("Hindustan Times Education",        "rss", "https://www.hindustantimes.com/feeds/rss/education/rssfeed.xml"),
    ("India Today Education",            "rss", "https://www.indiatoday.in/rss/1206579"),
    ("AglaSem Education",                "rss", "https://aglasem.com/feed/"),
    ("Jagranjosh NEET",                  "rss", "https://www.jagranjosh.com/articles/neet-articles.feed"),
    ("Careers360 NEET",                  "rss", "https://medicine.careers360.com/articles?format=rss"),
    ("Shiksha NEET",                     "rss", "https://www.shiksha.com/medicine-health-sciences/neet/rss"),
    ("CollegeDekho NEET",                "rss", "https://www.collegedekho.com/news/category/neet/feed/"),
    ("GetMyUni NEET",                    "rss", "https://www.getmyuni.com/rss/neet.xml"),
    ("Embibe NEET",                      "rss", "https://www.embibe.com/exams/neet/feed/"),
    ("Vidyarthiplus NEET",               "rss", "https://www.vidyarthiplus.com/neet/feed/"),
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

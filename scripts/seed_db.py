"""Seed the database with default PW PCB monitoring sources."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Source
from config import Config

SOURCES = [
    # YouTube channels
    ("PW — Alakh Pandey (Physics)", "youtube",  "UCk0Kvsaln4I4v9AKBb3FXOQ"),
    ("PW Official Channel",         "youtube",  "UCb1RuCdQk8i-A4RYkvBJpZA"),
    ("PW Biology Wallah",           "youtube",  "UCWPm8bRzqZbZYhBEGS0anEA"),
    ("PW Yakeen Batch NEET",        "youtube",  "UCyMDCMkGEaUwq96ROxbJLsQ"),
    ("PW English Medium",           "youtube",  "UCX4qoqREmvDrHs5EwDOxrsg"),
    # RSS feeds (YouTube fallback — no API key required)
    ("PW RSS — Alakh Pandey",       "rss",      "https://www.youtube.com/feeds/videos.xml?channel_id=UCk0Kvsaln4I4v9AKBb3FXOQ"),
    ("PW RSS — Official",           "rss",      "https://www.youtube.com/feeds/videos.xml?channel_id=UCb1RuCdQk8i-A4RYkvBJpZA"),
    # Twitter / X
    ("Physics Wallah (Twitter)",    "twitter",  "PhysicsWallah"),
    ("Alakh Pandey (Twitter)",      "twitter",  "AlakhPandey01"),
    # Website
    ("PW Website (pw.live)",        "website",  "https://pw.live"),
    ("PW Study Material",           "website",  "https://pw.live/study-material"),
]

def main():
    app = create_app(Config)
    with app.app_context():
        added = 0
        for name, stype, ident in SOURCES:
            exists = Source.query.filter_by(source_type=stype, identifier=ident).first()
            if not exists:
                db.session.add(Source(name=name, source_type=stype, identifier=ident))
                added += 1
                print(f"  ✅ Added: {name}")
            else:
                print(f"  ⏭  Exists: {name}")
        db.session.commit()
        print(f"\nDone — {added} source(s) added.")

if __name__ == "__main__":
    main()

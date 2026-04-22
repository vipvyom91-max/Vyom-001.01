import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///pw_pcb_updates.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # YouTube
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
    PW_YOUTUBE_CHANNEL_IDS = [
        "UCk0Kvsaln4I4v9AKBb3FXOQ",  # Physics Wallah – Alakh Pandey
        "UCb1RuCdQk8i-A4RYkvBJpZA",  # PW Official channel
        "UCWPm8bRzqZbZYhBEGS0anEA",  # PW Biology
    ]
    PW_YOUTUBE_PLAYLIST_IDS = [
        "PLQJDMIkEOQ7E83gPBt1AwMuUGEqX_mNIK",  # Class 12 Physics
        "PLQJDMIkEOQ7GfJaAh4ib7hDPXQKXvX7Dq",  # Class 12 Chemistry
    ]

    # Telegram
    TELEGRAM_API_ID = os.environ.get("TELEGRAM_API_ID", "")
    TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
    TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION", "pw_monitor")
    PW_TELEGRAM_CHANNELS = [
        c.strip()
        for c in os.environ.get(
            "PW_TELEGRAM_CHANNELS",
            "physicswallah,pw_neet_pcb",
        ).split(",")
        if c.strip()
    ]

    # Twitter / X
    TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")
    PW_TWITTER_ACCOUNTS = [
        a.strip()
        for a in os.environ.get(
            "PW_TWITTER_ACCOUNTS", "PhysicsWallah,AlakhPandey01"
        ).split(",")
        if a.strip()
    ]

    # Instagram
    INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME", "")
    INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD", "")

    # Anthropic / Claude
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

    # Scheduler
    COLLECTION_INTERVAL_HOURS = int(os.environ.get("COLLECTION_INTERVAL_HOURS", "3"))

    # App
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    PORT = int(os.environ.get("PORT", "5000"))

    # Hashtag bank for PCB / NEET content
    HASHTAG_BANK = {
        "general": [
            "#PhysicsWallah", "#PW", "#PWians", "#AlakhPandey",
            "#NEET2025", "#NEET2026", "#NEETPrep", "#NEETAspirants",
            "#Class12", "#PCB", "#BiologyNEET",
        ],
        "Physics": [
            "#PhysicsClass12", "#PhysicsPW", "#PhysicsNEET",
            "#Mechanics", "#Electrostatics", "#Optics", "#ModernPhysics",
        ],
        "Chemistry": [
            "#ChemistryClass12", "#ChemistryPW", "#ChemNEET",
            "#OrganicChemistry", "#Electrochemistry", "#PhysicalChem",
        ],
        "Biology": [
            "#BiologyClass12", "#BioPW", "#BioNEET",
            "#Genetics", "#Ecology", "#HumanPhysiology", "#Botany",
        ],
        "Schedule": [
            "#PWSchedule", "#LiveClass", "#PWLive", "#FreeClasses",
        ],
        "DPP": [
            "#DPP", "#PWdpp", "#PracticeProblems", "#NEETQuestions",
        ],
    }

"""
One-time Telegram authentication script.
Run this once to create the Telethon session file.
After that, the collector will use the saved session automatically.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

API_ID   = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
SESSION  = os.environ.get("TELEGRAM_SESSION", "pw_monitor")

if not API_ID or not API_HASH:
    print("❌ Set TELEGRAM_API_ID and TELEGRAM_API_HASH in your .env file first.")
    sys.exit(1)

try:
    from telethon.sync import TelegramClient
except ImportError:
    print("❌ telethon not installed. Run: pip install telethon")
    sys.exit(1)

print(f"Authenticating Telegram session '{SESSION}'…")
print("You will receive an OTP on your Telegram app.\n")

with TelegramClient(SESSION, int(API_ID), API_HASH) as client:
    me = client.get_me()
    print(f"\n✅ Authenticated as: {me.first_name} (@{me.username})")
    print(f"   Session saved to: {SESSION}.session")
    print("   You can now run the app — Telegram collection will work automatically.")

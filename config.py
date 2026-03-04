import os

from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")


# --- Bot settings ---
CHECK_INTERVAL = 60  # secondi tra un check commit e l'altro
DB_FILE = "repos.db"

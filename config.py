import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- Bot settings ---
CHECK_INTERVAL = 60   # secondi tra un check commit e l'altro
DB_FILE        = "repos.db"

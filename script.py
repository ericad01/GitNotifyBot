
import logging
import sqlite3
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_TOKEN, DB_FILE

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ================= DATABASE =================

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id         INTEGER PRIMARY KEY,
                github_token    TEXT,
                github_username TEXT
            )
        """)

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *GitHub Notify Bot*\n\n"
        "Benvenuto! Questo bot ti notifica i nuovi commit e le release delle tue repository GitHub.\n\n"
        "Comandi disponibili (in arrivo):\n"
        "`/login` — Accedi con GitHub\n"
        "`/add owner/repo [branch]` — Monitora un branch\n"
        "`/list` — Elenca repository monitorate\n"
        "`/remove owner/repo` — Rimuovi monitoraggio",
        parse_mode="Markdown",
    )

# ================= MAIN =================

def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    logging.info("Bot avviato!")
    app.run_polling()

if __name__ == "__main__":
    main()

import logging
import sqlite3
import functools
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_TOKEN, DB_FILE
from oauth_server import generate_oauth_url

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ================= DATABASE =================


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                chat_id         INTEGER PRIMARY KEY,
                github_token    TEXT,
                github_username TEXT
            )
        """
        )


def get_user_token(chat_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            "SELECT github_token FROM users WHERE chat_id=?", (chat_id,)
        ).fetchone()
    return row[0] if row else None


def get_user_info(chat_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            "SELECT github_token, github_username FROM users WHERE chat_id=?",
            (chat_id,),
        ).fetchone()
    return {"token": row[0], "username": row[1]} if row else None


def delete_user(chat_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))


# ================= AUTH DECORATOR =================


def require_auth(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not get_user_token(chat_id):
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔑 Accedi con GitHub", url=generate_oauth_url(chat_id)
                        )
                    ]
                ]
            )
            await update.message.reply_text(
                "⚠️ Devi prima autenticarti con GitHub.\nClicca il bottone qui sotto:",
                reply_markup=keyboard,
            )
            return
        return await func(update, context)

    return wrapper


# ================= COMMANDS =================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_info = get_user_info(chat_id)
    status = (
        f"✅ Connesso come *{user_info['username']}*"
        if user_info
        else "⚠️ Non autenticato — usa /login"
    )

    await update.message.reply_text(
        f"🤖 *GitHub Notify Bot*\n\n"
        f"{status}\n\n"
        f"Comandi disponibili:\n"
        f"`/login` — Accedi con GitHub\n"
        f"`/logout` — Disconnetti account\n"
        f"`/add owner/repo [branch]` — Monitora un branch\n"
        f"`/list` — Elenca repository monitorate\n"
        f"`/remove owner/repo` — Rimuovi monitoraggio",
        parse_mode="Markdown",
    )


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_info = get_user_info(chat_id)
    if user_info:
        await update.message.reply_text(
            f"✅ Sei già connesso come *{user_info['username']}*.\nUsa /logout per disconnetterti.",
            parse_mode="Markdown",
        )
        return
    oauth_url = generate_oauth_url(chat_id)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔑 Accedi con GitHub", url=oauth_url)]]
    )
    await update.message.reply_text(
        "Clicca il bottone per autenticarti con GitHub.\n\n"
        "🔒 Il bot accederà alle tue repo pubbliche *e private* in sola lettura.\n"
        "⏱️ Il link scade se non lo usi entro qualche minuto.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_info = get_user_info(chat_id)
    if not user_info:
        await update.message.reply_text("Non sei autenticato.")
        return
    delete_user(chat_id)
    await update.message.reply_text(
        f"👋 Account *{user_info['username']}* disconnesso.",
        parse_mode="Markdown",
    )


# ================= MAIN =================


def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("logout", logout))

    logging.info("Bot avviato!")
    app.run_polling()


if __name__ == "__main__":
    main()

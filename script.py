import logging
import sqlite3
import functools
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_TOKEN, DB_FILE, CHECK_INTERVAL
from oauth_server import generate_oauth_url

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

DEFAULT_HEADERS = {"User-Agent": "Telegram-GitHub-Bot"}

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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS repos (
                chat_id  INTEGER,
                repo     TEXT,
                branch   TEXT DEFAULT 'main',
                last_sha TEXT,
                PRIMARY KEY (chat_id, repo, branch)
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
        conn.execute("DELETE FROM repos WHERE chat_id=?", (chat_id,))


def add_repo_db(chat_id, repo, branch, sha):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO repos VALUES (?, ?, ?, ?)",
            (chat_id, repo, branch, sha),
        )


def remove_repo_db(chat_id, repo, branch=None):
    with sqlite3.connect(DB_FILE) as conn:
        if branch:
            conn.execute(
                "DELETE FROM repos WHERE chat_id=? AND repo=? AND branch=?",
                (chat_id, repo, branch),
            )
        else:
            conn.execute(
                "DELETE FROM repos WHERE chat_id=? AND repo=?", (chat_id, repo)
            )


def load_all_repos():
    with sqlite3.connect(DB_FILE) as conn:
        return conn.execute(
            "SELECT chat_id, repo, branch, last_sha FROM repos"
        ).fetchall()


def update_sha_db(chat_id, repo, branch, sha):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "UPDATE repos SET last_sha=? WHERE chat_id=? AND repo=? AND branch=?",
            (sha, chat_id, repo, branch),
        )


# ================= GITHUB API =================


def build_headers(chat_id: int) -> dict:
    h = dict(DEFAULT_HEADERS)
    token = get_user_token(chat_id)
    if token:
        h["Authorization"] = f"token {token}"
    return h


def get_commits_since(chat_id, repo, branch, since_sha):
    url = f"https://api.github.com/repos/{repo}/commits"
    r = requests.get(
        url,
        headers=build_headers(chat_id),
        params={"sha": branch, "per_page": 10},
        timeout=10,
    )
    if r.status_code != 200:
        return None, None
    commits = r.json()
    if not commits:
        return None, None
    latest_sha = commits[0]["sha"]
    new_commits = []
    for c in commits:
        if c["sha"] == since_sha:
            break
        new_commits.append(c)
    return latest_sha, new_commits


def format_commit_digest(repo, branch, new_commits):
    count = len(new_commits)
    authors = list({c["commit"]["author"]["name"] for c in new_commits})
    lines = [
        f"📦 *{count} nuovi commit su* `{repo}` (branch: `{branch}`)",
        f"👥 *Autori:* {', '.join(authors)}",
        "",
    ]
    for c in new_commits[:5]:
        sha_short = c["sha"][:7]
        msg_line = c["commit"]["message"].split("\n")[0]
        author = c["commit"]["author"]["name"]
        lines.append(f"• [`{sha_short}`]({c['html_url']}) {msg_line} — _{author}_")
    if count > 5:
        lines.append(f"_...e altri {count - 5} commit._")
    return "\n".join(lines)


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
        f"`/remove owner/repo [branch]` — Rimuovi monitoraggio",
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
        f"👋 Account *{user_info['username']}* disconnesso.\nTutti i tuoi monitoraggi sono stati rimossi.",
        parse_mode="Markdown",
    )


@require_auth
async def add_repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Uso: `/add owner/repo [branch]`\nEsempio: `/add mio-user/repo-privata main`",
            parse_mode="Markdown",
        )
        return
    repo = context.args[0]
    branch = context.args[1] if len(context.args) > 1 else "main"
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f"⏳ Verifico `{repo}` (branch: `{branch}`)...", parse_mode="Markdown"
    )

    latest_sha, _ = get_commits_since(chat_id, repo, branch, "")
    if not latest_sha:
        await update.message.reply_text(
            "❌ Repository o branch non trovato.\n"
            "Controlla il nome e che il tuo account abbia accesso (per le repo private serve il login).",
        )
        return

    add_repo_db(chat_id, repo, branch, latest_sha)
    await update.message.reply_text(
        f"✅ `{repo}` (branch: `{branch}`) aggiunta!\nRiceverai notifiche per ogni nuova push.",
        parse_mode="Markdown",
    )


@require_auth
async def list_repos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_repos = [(r[1], r[2]) for r in load_all_repos() if r[0] == chat_id]
    if not user_repos:
        await update.message.reply_text(
            "Nessuna repository monitorata.\nUsa `/add owner/repo` per iniziare!",
            parse_mode="Markdown",
        )
        return
    lines = ["📋 *Repository monitorate:*\n"]
    for repo, branch in user_repos:
        lines.append(f"• `{repo}` — branch: `{branch}`")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_auth
async def remove_repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Uso: `/remove owner/repo [branch]`", parse_mode="Markdown"
        )
        return
    repo = context.args[0]
    branch = context.args[1] if len(context.args) > 1 else None
    chat_id = update.effective_chat.id
    remove_repo_db(chat_id, repo, branch)
    msg = (
        f"🗑️ `{repo}` (branch: `{branch}`) rimossa."
        if branch
        else f"🗑️ `{repo}` rimossa (tutti i branch)."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ================= JOBS =================


async def check_repositories(context: ContextTypes.DEFAULT_TYPE):
    for chat_id, repo, branch, last_sha in load_all_repos():
        try:
            latest_sha, new_commits = get_commits_since(chat_id, repo, branch, last_sha)
            if latest_sha and new_commits:
                update_sha_db(chat_id, repo, branch, latest_sha)
                await context.bot.send_message(
                    chat_id,
                    format_commit_digest(repo, branch, new_commits),
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
        except Exception as e:
            logging.error(f"Errore check commit {repo}@{branch}: {e}")


# ================= MAIN =================


def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(CommandHandler("add", add_repo))
    app.add_handler(CommandHandler("list", list_repos))
    app.add_handler(CommandHandler("remove", remove_repo))

    app.job_queue.run_repeating(check_repositories, interval=CHECK_INTERVAL, first=10)

    logging.info("Bot avviato!")
    app.run_polling()


if __name__ == "__main__":
    main()

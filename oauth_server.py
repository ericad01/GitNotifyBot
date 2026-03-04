import secrets
import sqlite3

import requests
from flask import Flask, request

from config import (DB_FILE, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET,
                    OAUTH_REDIRECT_URI)

app = Flask(__name__)


# ================= DB HELPERS =================


def ensure_tables():
    """Crea le tabelle se non esistono (chiamata all'avvio)."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id         INTEGER PRIMARY KEY,
                github_token    TEXT,
                github_username TEXT
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state      TEXT PRIMARY KEY,
                chat_id    INTEGER,
                created_at DATETIME DEFAULT (datetime('now'))
            )
            """)


def save_state(state: str, chat_id: int):
    """Salva lo state nel DB (visibile a entrambi i processi)."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO oauth_states (state, chat_id) VALUES (?, ?)",
            (state, chat_id),
        )


def pop_state(state: str):
    """Legge e cancella lo state. Restituisce chat_id o None."""
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            "SELECT chat_id FROM oauth_states WHERE state=?", (state,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM oauth_states WHERE state=?", (state,))
            return row[0]
    return None


def save_github_token(chat_id: int, token: str, username: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (chat_id, github_token, github_username) VALUES (?, ?, ?)",
            (chat_id, token, username),
        )


def get_github_username(token: str):
    r = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"token {token}",
            "User-Agent": "Telegram-GitHub-Bot",
        },
        timeout=10,
    )
    if r.status_code == 200:
        return r.json().get("login")
    return None


# ================= URL GENERATOR (usato da script.py) =================


def generate_oauth_url(chat_id: int) -> str:
    """
    Genera un URL OAuth univoco per l'utente.
    Lo state e' salvato nel DB cosi' il server Flask puo' ritrovarlo
    anche se gira in un processo separato rispetto al bot.
    """
    ensure_tables()
    state = secrets.token_urlsafe(16)
    save_state(state, chat_id)

    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={OAUTH_REDIRECT_URI}"
        f"&scope=repo,read:user"
        f"&state={state}"
    )
    return f"https://github.com/login/oauth/authorize?{params}"


# ================= FLASK ROUTES =================


@app.route("/callback")
def github_callback():
    """GitHub reindirizza qui dopo che l'utente ha autorizzato l'app."""
    code = request.args.get("code")
    state = request.args.get("state")

    chat_id = pop_state(state) if state else None

    if not chat_id or not code:
        return (
            "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            "<h2>❌ Autenticazione fallita.</h2>"
            "<p>Link non valido o scaduto. Torna su Telegram e riprova con /login.</p>"
            "</body></html>"
        ), 400

    token_resp = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": OAUTH_REDIRECT_URI,
        },
        timeout=10,
    )

    if token_resp.status_code != 200:
        return "<h2>❌ Errore durante l'autenticazione con GitHub.</h2>", 500

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        error = token_data.get("error", "sconosciuto")
        error_desc = token_data.get("error_description", "")
        return (
            f"<h2>❌ Token non ricevuto.</h2><p>Errore: {error} — {error_desc}</p>",
            500,
        )

    username = get_github_username(access_token) or "sconosciuto"
    save_github_token(chat_id, access_token, username)

    return f"""
    <html>
    <head><title>Login completato</title></head>
    <body style="font-family:sans-serif;text-align:center;padding:60px;">
        <h1>✅ Login effettuato con successo!</h1>
        <p>Ciao <strong>{username}</strong>! Il tuo account GitHub è stato collegato.</p>
        <p>Torna su Telegram — il bot è pronto ad usare il tuo account.</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    ensure_tables()
    app.run(host="0.0.0.0", port=5001, debug=False)

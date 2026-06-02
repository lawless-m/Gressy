"""Shared helpers for the visitor-log CGI scripts (check-in / check-out / admin).

Runs under lighttpd mod_cgi as the www-data user. Python 3.13 removed the
stdlib `cgi` module, so request parsing is done manually here.
"""
import html
import os
import sqlite3
import sys
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

DB_PATH = "/var/lib/visitorlog/visitors.db"
COOKIE_NAME = "visitor_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


# --- database -------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            company     TEXT NOT NULL,
            cookie      TEXT NOT NULL,
            checkin_at  TEXT NOT NULL,
            checkout_at TEXT
        )
        """
    )
    return conn


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --- request parsing ------------------------------------------------------

def read_post():
    """Return a dict of POSTed form fields (first value of each)."""
    try:
        length = int(os.environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    body = sys.stdin.buffer.read(length).decode("utf-8", "replace") if length else ""
    return {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}


def get_cookie():
    """Return the existing visitor_id cookie value, or None."""
    raw = os.environ.get("HTTP_COOKIE", "")
    if not raw:
        return None
    jar = SimpleCookie()
    jar.load(raw)
    morsel = jar.get(COOKIE_NAME)
    return morsel.value if morsel else None


def is_https():
    return (
        os.environ.get("HTTPS") == "on"
        or os.environ.get("REQUEST_SCHEME") == "https"
        or os.environ.get("HTTP_X_FORWARDED_PROTO", "").split(",")[0].strip() == "https"
    )


def cookie_header(value):
    parts = [
        f"{COOKIE_NAME}={value}",
        "Path=/",
        f"Max-Age={COOKIE_MAX_AGE}",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if is_https():
        parts.append("Secure")
    return "Set-Cookie: " + "; ".join(parts)


# --- response -------------------------------------------------------------

def send(body, set_cookie=None, status="200 OK"):
    out = sys.stdout
    out.write(f"Status: {status}\r\n")
    out.write("Content-Type: text/html; charset=utf-8\r\n")
    if set_cookie:
        out.write(set_cookie + "\r\n")
    out.write("\r\n")
    out.write(body)


# --- HTML template (matches the homepage look & feel) ---------------------

def page(card_html, title="Ramsden International", max_width="480px"):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1a1a2e;
            background: #f8f9fa;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        header {{
            background: #1a1a2e;
            color: #fff;
            padding: 2rem 1.5rem;
            text-align: center;
        }}
        header h1 {{ font-size: 2.2rem; font-weight: 700; letter-spacing: 0.04em; }}
        main {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 3rem 1.5rem;
        }}
        .card {{
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
            padding: 2.5rem 3rem;
            max-width: {max_width};
            width: 100%;
            text-align: center;
        }}
        .card h2 {{ font-size: 1.3rem; margin-bottom: 1.5rem; color: #1a1a2e; }}
        .card h3 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: 0.06em;
                    color: #666; margin: 1.8rem 0 0.8rem; text-align: left; }}
        .field {{ margin: 1.2rem 0; text-align: left; }}
        .field label {{
            font-weight: 600;
            display: block;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #666;
            margin-bottom: 0.4rem;
        }}
        .field input {{
            width: 100%;
            padding: 0.7rem 0.9rem;
            font-size: 1rem;
            border: 1px solid #ccc;
            border-radius: 8px;
            font-family: inherit;
        }}
        .field input:focus {{ outline: none; border-color: #2a5298; }}
        button {{
            margin-top: 1rem;
            width: 100%;
            padding: 0.8rem 1rem;
            font-size: 1rem;
            font-weight: 600;
            color: #fff;
            background: #2a5298;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }}
        button:hover {{ background: #1f3f74; }}
        .msg {{ margin: 1.2rem 0; font-size: 1.05rem; line-height: 1.6; }}
        .error {{ color: #b00020; margin-bottom: 0.5rem; font-size: 0.95rem; }}
        .detail {{ color: #666; font-size: 0.95rem; line-height: 1.7; }}
        .nav {{ margin-top: 1.5rem; font-size: 0.9rem; }}
        .nav a {{ color: #2a5298; text-decoration: none; }}
        .nav a:hover {{ text-decoration: underline; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
        th, td {{ text-align: left; padding: 0.6rem 0.7rem; border-bottom: 1px solid #eee; }}
        th {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #888; }}
        td.actions {{ text-align: right; }}
        .empty {{ color: #888; font-style: italic; padding: 0.8rem 0; text-align: left; }}
        button.inline {{ width: auto; margin: 0; padding: 0.4rem 0.9rem; font-size: 0.85rem;
                         background: #b00020; }}
        button.inline:hover {{ background: #8a0019; }}
        .pill {{ display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
                 font-size: 0.78rem; font-weight: 600; }}
        .pill.in {{ background: #e6f4ea; color: #1e7e34; }}
        .pill.out {{ background: #eee; color: #777; }}
    </style>
</head>
<body>
    <header>
        <h1>Ramsden International</h1>
    </header>

    <main>
        <div class="card">
{card_html}
        </div>
    </main>

    <footer style="text-align:center;padding:1.5rem;font-size:0.85rem;background:#1a1a2e;color:#aaa;line-height:1.8;">
        &copy; 2026 Ramsden International. All rights reserved.<br>
        Ramsden International is a trading name of S D Ramsden &amp; Co Limited.<br>
        Registered in England and Wales. Company Registration No. 07902211
    </footer>
</body>
</html>"""

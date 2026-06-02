#!/usr/bin/env python3
"""Visitor check-out page.

GET  -> look up the visitor's open check-in (by cookie) and offer a button.
POST -> stamp checkout_at on the most recent open visit for this cookie.
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlog


def open_visit(conn, cookie_val):
    if not cookie_val:
        return None
    return conn.execute(
        "SELECT * FROM visits WHERE cookie = ? AND checkout_at IS NULL "
        "ORDER BY id DESC LIMIT 1",
        (cookie_val,),
    ).fetchone()


def confirm_card(visit):
    return f"""            <h2>Check Out</h2>
            <p class="msg">You are checked in as <strong>{html.escape(visit['name'])}</strong>.</p>
            <p class="detail">
                Company: {html.escape(visit['company'])}<br>
                Checked in at {html.escape(visit['checkin_at'])} UTC
            </p>
            <form method="post" action="/check-out">
                <button type="submit">Check Out</button>
            </form>"""


def done_card(visit, when):
    return f"""            <h2>Checked Out</h2>
            <p class="msg">Goodbye, <strong>{html.escape(visit['name'])}</strong>.</p>
            <p class="detail">Checked out at {html.escape(when)} UTC</p>"""


def none_card():
    return """            <h2>Check Out</h2>
            <p class="msg">No active check-in was found for this device.</p>
            <p class="nav"><a href="/check-in">Check in</a></p>"""


def main():
    method = os.environ.get("REQUEST_METHOD", "GET").upper()
    cookie_val = vlog.get_cookie()
    conn = vlog.get_db()

    visit = open_visit(conn, cookie_val)

    if method == "POST":
        if not visit:
            conn.close()
            vlog.send(vlog.page(none_card(), "Check Out"))
            return
        when = vlog.now_iso()
        with conn:
            conn.execute(
                "UPDATE visits SET checkout_at = ? WHERE id = ?",
                (when, visit["id"]),
            )
        conn.close()
        vlog.send(vlog.page(done_card(visit, when), "Checked Out"))
        return

    # GET
    conn.close()
    if not visit:
        vlog.send(vlog.page(none_card(), "Check Out"))
        return
    vlog.send(vlog.page(confirm_card(visit), "Check Out"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        sys.stderr.write(traceback.format_exc())
        vlog.send(vlog.page(
            '            <h2>Something went wrong</h2>'
            '<p class="msg">Please try again shortly.</p>', "Error"),
            status="500 Internal Server Error")

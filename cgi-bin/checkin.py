#!/usr/bin/env python3
"""Visitor check-in page.

GET  -> render the check-in form (sets a visitor_id cookie if absent).
POST -> validate Name & Company are both non-empty, then store the visit
        (name, company, cookie, timestamp) in the database.
"""
import html
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlog


def form_card(name="", company="", error=""):
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    return f"""            <h2>Visitor Check-In</h2>
            {error_html}
            <form method="post" action="/check-in">
                <div class="field">
                    <label for="name">Name</label>
                    <input type="text" id="name" name="name" value="{html.escape(name)}"
                           required autocomplete="name" autofocus>
                </div>
                <div class="field">
                    <label for="company">Company</label>
                    <input type="text" id="company" name="company" value="{html.escape(company)}"
                           required autocomplete="organization">
                </div>
                <button type="submit">Check In</button>
            </form>"""


def success_card(name, company, when):
    return f"""            <h2>Checked In</h2>
            <p class="msg">Welcome, <strong>{html.escape(name)}</strong>.</p>
            <p class="detail">
                Company: {html.escape(company)}<br>
                Checked in at {html.escape(when)} UTC
            </p>
            <p class="nav">When you leave, please <a href="/check-out">check out</a>.</p>"""


def main():
    method = os.environ.get("REQUEST_METHOD", "GET").upper()
    cookie_val = vlog.get_cookie()

    if method == "POST":
        form = vlog.read_post()
        name = (form.get("name") or "").strip()
        company = (form.get("company") or "").strip()

        if not name or not company:
            vlog.send(vlog.page(
                form_card(name, company, "Please enter both your name and company."),
                "Visitor Check-In"))
            return

        # Ensure we have a cookie to associate with this visit.
        set_cookie = None
        if not cookie_val:
            cookie_val = uuid.uuid4().hex
            set_cookie = vlog.cookie_header(cookie_val)

        when = vlog.now_iso()
        conn = vlog.get_db()
        with conn:
            conn.execute(
                "INSERT INTO visits (name, company, cookie, checkin_at) "
                "VALUES (?, ?, ?, ?)",
                (name, company, cookie_val, when),
            )
        conn.close()

        vlog.send(vlog.page(success_card(name, company, when), "Checked In"),
                  set_cookie=set_cookie)
        return

    # GET: show the form, setting a cookie if the visitor doesn't have one yet.
    set_cookie = None
    if not cookie_val:
        set_cookie = vlog.cookie_header(uuid.uuid4().hex)
    vlog.send(vlog.page(form_card(), "Visitor Check-In"), set_cookie=set_cookie)


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

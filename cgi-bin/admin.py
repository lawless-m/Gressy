#!/usr/bin/env python3
"""Visitor-log admin page (protected by HTTP Basic Auth at the lighttpd layer).

GET  -> show who is currently on-site, plus the full visit history.
POST -> action=checkout&id=N stamps checkout_at on that visit (admin override).
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlog


def fmt(ts):
    return html.escape(ts) if ts else "—"


def onsite_table(rows):
    if not rows:
        return '<p class="empty">No visitors are currently checked in.</p>'
    body = []
    for r in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(r['name'])}</td>"
            f"<td>{html.escape(r['company'])}</td>"
            f"<td>{fmt(r['checkin_at'])}</td>"
            '<td class="actions">'
            '<form method="post" action="/admin" style="display:inline">'
            f'<input type="hidden" name="action" value="checkout">'
            f'<input type="hidden" name="id" value="{r["id"]}">'
            '<button type="submit" class="inline">Check out</button>'
            "</form></td>"
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Name</th><th>Company</th><th>Checked in (UTC)</th><th></th>"
        "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"
    )


def history_table(rows):
    if not rows:
        return '<p class="empty">No visits recorded yet.</p>'
    body = []
    for r in rows:
        if r["checkout_at"]:
            status = '<span class="pill out">Out</span>'
        else:
            status = '<span class="pill in">On-site</span>'
        body.append(
            "<tr>"
            f"<td>{html.escape(r['name'])}</td>"
            f"<td>{html.escape(r['company'])}</td>"
            f"<td>{fmt(r['checkin_at'])}</td>"
            f"<td>{fmt(r['checkout_at'])}</td>"
            f"<td>{status}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Name</th><th>Company</th><th>Checked in (UTC)</th>"
        "<th>Checked out (UTC)</th><th>Status</th>"
        "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"
    )


def render(conn, notice=""):
    onsite = conn.execute(
        "SELECT * FROM visits WHERE checkout_at IS NULL ORDER BY checkin_at DESC"
    ).fetchall()
    history = conn.execute(
        "SELECT * FROM visits ORDER BY id DESC LIMIT 500"
    ).fetchall()
    user = os.environ.get("REMOTE_USER", "")
    notice_html = f'<p class="msg" style="color:#1e7e34">{html.escape(notice)}</p>' if notice else ""
    card = f"""            <h2>Visitor Log{f' &mdash; {html.escape(user)}' if user else ''}</h2>
            {notice_html}
            <h3>Currently on-site ({len(onsite)})</h3>
            {onsite_table(onsite)}
            <h3>Full history</h3>
            {history_table(history)}"""
    vlog.send(vlog.page(card, "Visitor Log Admin", max_width="900px"))


def main():
    method = os.environ.get("REQUEST_METHOD", "GET").upper()
    conn = vlog.get_db()

    if method == "POST":
        form = vlog.read_post()
        notice = ""
        if form.get("action") == "checkout":
            try:
                vid = int(form.get("id", ""))
            except (TypeError, ValueError):
                vid = None
            if vid is not None:
                row = conn.execute(
                    "SELECT name FROM visits WHERE id = ? AND checkout_at IS NULL",
                    (vid,),
                ).fetchone()
                if row:
                    with conn:
                        conn.execute(
                            "UPDATE visits SET checkout_at = ? WHERE id = ?",
                            (vlog.now_iso(), vid),
                        )
                    notice = f"Checked out {row['name']}."
        render(conn, notice)
        conn.close()
        return

    render(conn)
    conn.close()


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

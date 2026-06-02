# Gressy — Visitor Log

A lightweight visitor sign-in / sign-out system for the Ramsden International
site (`miami.ram-int.uk`), served by **lighttpd** via Python **CGI** with a
**SQLite** backing store. No application server or framework — just CGI scripts.

## Pages

| URL          | Purpose                                                                 |
|--------------|-------------------------------------------------------------------------|
| `/check-in`  | Visitor enters **Name** and **Company**. Both required. Stores the visit (name, company, cookie, UTC timestamp) and sets a `visitor_id` cookie. |
| `/check-out` | Looks up the visitor's open visit by cookie and stamps the checkout time. |
| `/admin`     | HTTP Basic Auth. Lists who is currently on-site plus full history; allows manual check-out. |

All pages reuse the homepage look and feel.

## Layout

```
cgi-bin/
  vlog.py        Shared helpers: SQLite access, request/cookie parsing, HTML template
  checkin.py     GET shows the form; POST validates + records the visit
  checkout.py    GET confirms; POST stamps checkout_at
  admin.py       Basic-Auth-protected log viewer + manual check-out
lighttpd/
  05-auth.conf       Loads mod_auth / mod_authn_file (before mod_cgi)
  50-visitorlog.conf Routes /check-in /check-out /admin to the CGI scripts; Basic Auth on /admin
print/
  check-in.svg       QR code for https://miami.ram-int.uk/check-in
  check-out.svg      QR code for https://miami.ram-int.uk/check-out
  print.html         Two A4 sheets (check-in + check-out) ready to print
deploy.sh        Installs everything onto the host and reloads lighttpd
```

## Printable QR sheets

`print/print.html` is two A4 portrait pages — a check-in sheet and a check-out
sheet — each with its QR code and the URL printed underneath. Open it in a
browser and print (Ctrl/Cmd-P, paper size **A4**, margins **None/Default**); the
`@page` rules size each sheet to A4 and force a page break between them. The QR
images are the vector `.svg` files in the same folder, so they stay crisp at any
size. Regenerate them with:

```sh
qrencode -t SVG -l M -m 0 -o print/check-in.svg  "https://miami.ram-int.uk/check-in"
qrencode -t SVG -l M -m 0 -o print/check-out.svg "https://miami.ram-int.uk/check-out"
```

## Database

SQLite at `/var/lib/visitorlog/visitors.db` (owned by `www-data`), single table:

```sql
CREATE TABLE visits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    company     TEXT NOT NULL,
    cookie      TEXT NOT NULL,   -- value of the visitor_id cookie
    checkin_at  TEXT NOT NULL,   -- ISO-8601 UTC
    checkout_at TEXT             -- ISO-8601 UTC, NULL while on-site
);
```

The table is created automatically on first request.

## Deploy

On the lighttpd host (Debian, Python 3.11+):

```sh
git clone git@github.com:lawless-m/Gressy.git
cd Gressy
sudo ./deploy.sh
```

`deploy.sh` is idempotent. On first run it creates the admin credential file at
`/etc/lighttpd/visitorlog.htpasswd` (prompting for a password for user `admin`);
on later runs it leaves an existing one untouched.

## Admin password

The real credential file is **not** in git (see `.gitignore`); only
`visitorlog.htpasswd.example` is. To set or change it:

```sh
printf 'admin:%s\n' "$(openssl passwd -6)" | sudo tee /etc/lighttpd/visitorlog.htpasswd
sudo chown root:www-data /etc/lighttpd/visitorlog.htpasswd
sudo chmod 0640 /etc/lighttpd/visitorlog.htpasswd
sudo systemctl reload lighttpd
```

## Notes

- Requires lighttpd modules `mod_cgi`, `mod_alias`, `mod_auth`, `mod_authn_file`.
- The `visitor_id` cookie is `HttpOnly; SameSite=Lax` and `Secure` over HTTPS.
- Cookie-based identity ties checkout to the same browser/device used to check in.
- User input is HTML-escaped on output and stored via parameterised SQL.

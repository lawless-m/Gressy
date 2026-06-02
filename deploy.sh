#!/usr/bin/env bash
#
# Deploy the Gressy visitor log onto a lighttpd host.
# Run from the repo root:  sudo ./deploy.sh
#
# Idempotent: safe to re-run after pulling changes. It will NOT overwrite an
# existing admin password file.
set -euo pipefail

CGI_DIR=/var/www/cgi-bin
WEB_DIR=/var/www/html
DB_DIR=/var/lib/visitorlog
CONF_AVAIL=/etc/lighttpd/conf-available
CONF_ENABLED=/etc/lighttpd/conf-enabled
HTPASSWD=/etc/lighttpd/visitorlog.htpasswd

REPO="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run with sudo: sudo ./deploy.sh" >&2
    exit 1
fi

echo "==> Installing CGI scripts to $CGI_DIR"
install -d -m 0755 "$CGI_DIR"
install -m 0644 "$REPO/cgi-bin/vlog.py"     "$CGI_DIR/vlog.py"
install -m 0755 "$REPO/cgi-bin/checkin.py"  "$CGI_DIR/checkin.py"
install -m 0755 "$REPO/cgi-bin/checkout.py" "$CGI_DIR/checkout.py"
install -m 0755 "$REPO/cgi-bin/admin.py"    "$CGI_DIR/admin.py"

echo "==> Creating database directory $DB_DIR (owned by www-data)"
install -d -o www-data -g www-data -m 0755 "$DB_DIR"

echo "==> Installing printable QR sheets to $WEB_DIR/print"
install -d -m 0755 "$WEB_DIR/print"
install -m 0644 "$REPO/print/print.html"    "$WEB_DIR/print/print.html"
install -m 0644 "$REPO/print/check-in.svg"  "$WEB_DIR/print/check-in.svg"
install -m 0644 "$REPO/print/check-out.svg" "$WEB_DIR/print/check-out.svg"

echo "==> Installing lighttpd configuration"
install -m 0644 "$REPO/lighttpd/05-auth.conf"       "$CONF_AVAIL/05-auth.conf"
install -m 0644 "$REPO/lighttpd/50-visitorlog.conf" "$CONF_AVAIL/50-visitorlog.conf"
ln -sf ../conf-available/05-auth.conf       "$CONF_ENABLED/05-auth.conf"
ln -sf ../conf-available/50-visitorlog.conf "$CONF_ENABLED/50-visitorlog.conf"
# mod_cgi is provided by Debian's stock 10-cgi.conf — enable it if present.
if [ -f "$CONF_AVAIL/10-cgi.conf" ] && [ ! -e "$CONF_ENABLED/10-cgi.conf" ]; then
    ln -sf ../conf-available/10-cgi.conf "$CONF_ENABLED/10-cgi.conf"
fi

if [ ! -f "$HTPASSWD" ]; then
    echo "==> No admin password file found — creating one for user 'admin'"
    printf 'admin:%s\n' "$(openssl passwd -6)" > "$HTPASSWD"
    chown root:www-data "$HTPASSWD"
    chmod 0640 "$HTPASSWD"
else
    echo "==> Keeping existing admin password file $HTPASSWD"
fi

echo "==> Validating lighttpd configuration"
lighttpd -tt -f /etc/lighttpd/lighttpd.conf

echo "==> Reloading lighttpd"
systemctl reload lighttpd

echo "Done. Pages: /check-in  /check-out  /admin (Basic Auth)"

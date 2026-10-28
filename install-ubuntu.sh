#!/usr/bin/env bash
# KUFGEM InfoScreen: Ubuntu Server 24.04/26.04, x86_64 or arm64, local HDMI kiosk.
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
if [[ ${EUID} -ne 0 ]]; then echo "Bitte mit sudo ausführen." >&2; exit 1; fi
. /etc/os-release
if [[ "${ID:-}" != ubuntu ]]; then echo "Nur Ubuntu Server wird unterstützt." >&2; exit 1; fi
case "$(dpkg --print-architecture)" in amd64|arm64) ;; *) echo "Nur amd64/arm64 unterstützt" >&2; exit 1;; esac
REPO="https://github.com/Fxbso/InfoScreenOS/archive/refs/heads/main.tar.gz"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "==> Ubuntu-Pakete installieren"
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl tar python3 python3-pygame python3-numpy libsdl2-2.0-0 lightdm lightdm-gtk-greeter xserver-xorg xserver-xorg-input-libinput dbus-x11 x11-xserver-utils fonts-dejavu-core
echo "==> InfoScreen herunterladen"
curl -fL --retry 3 --connect-timeout 15 "$REPO" -o "$TMP/source.tar.gz"
mkdir -p "$TMP/src"
tar -xzf "$TMP/source.tar.gz" -C "$TMP/src" --strip-components=1
for path in backend/app.py display/renderer.py dashboard/index.html packaging/kufgem-infoscreen-api.service; do
 test -s "$TMP/src/$path" || { echo "Fehlt im Download: $path" >&2; exit 1; }
done
python3 -m compileall -q "$TMP/src/backend" "$TMP/src/display"
echo "==> Anwendung und Zugriffsrechte konfigurieren"
if ! id infoscreen >/dev/null 2>&1; then
 useradd --system --user-group --home-dir /var/lib/kufgem-infoscreen --shell /usr/sbin/nologin infoscreen
fi
if ! id infoscreen-kiosk >/dev/null 2>&1; then
 useradd --create-home --user-group --shell /bin/bash infoscreen-kiosk
fi
install -d -m 0755 /opt/kufgem-infoscreen /var/lib/kufgem-infoscreen
install -d -m 0750 /etc/kufgem-infoscreen
chown infoscreen:infoscreen /var/lib/kufgem-infoscreen
for dir in backend display dashboard; do
 rm -rf "/opt/kufgem-infoscreen/$dir"
 cp -a "$TMP/src/$dir" /opt/kufgem-infoscreen/
done
chown -R root:root /opt/kufgem-infoscreen
chmod -R a+rX /opt/kufgem-infoscreen
if [[ ! -s /etc/kufgem-infoscreen/admin-token ]]; then
 umask 077
 od -An -N32 -tx1 /dev/urandom | tr -d ' \n' > /etc/kufgem-infoscreen/admin-token
fi
chown root:infoscreen /etc/kufgem-infoscreen/admin-token
chmod 0640 /etc/kufgem-infoscreen/admin-token
install -m 0644 "$TMP/src/packaging/kufgem-infoscreen-api.service" /etc/systemd/system/kufgem-infoscreen-api.service
# Ubuntu's display is an X11 kiosk, not the Pi-only KMS/DRM service.
systemctl disable --now kufgem-infoscreen-display.service 2>/dev/null || true
cat > /usr/local/bin/infoscreen-kiosk-session <<'EOF'
#!/bin/sh
export SDL_VIDEODRIVER=x11
export SDL_AUDIODRIVER=dummy
export INFOSCREEN_DATA_DIR=/var/lib/kufgem-infoscreen
xset s off -dpms s noblank 2>/dev/null || true
exec /usr/bin/python3 /opt/kufgem-infoscreen/display/renderer.py
EOF
chmod 0755 /usr/local/bin/infoscreen-kiosk-session
install -d /usr/share/xsessions /etc/lightdm/lightdm.conf.d
cat > /usr/share/xsessions/infoscreen.desktop <<'EOF'
[Desktop Entry]
Name=KUFGEM InfoScreen
Comment=Native InfoScreen Fullscreen
Exec=/usr/local/bin/infoscreen-kiosk-session
Type=Application
EOF
cat > /etc/lightdm/lightdm.conf.d/90-infoscreen.conf <<'EOF'
[Seat:*]
autologin-user=infoscreen-kiosk
autologin-user-timeout=0
user-session=infoscreen
EOF
# Ensure the display can read saved images/layout while API retains write access.
if [[ -f /var/lib/kufgem-infoscreen/layout.json ]]; then chmod 0644 /var/lib/kufgem-infoscreen/layout.json; fi
if [[ -f /var/lib/kufgem-infoscreen/background.img ]]; then chmod 0644 /var/lib/kufgem-infoscreen/background.img; fi
echo "==> Dienste starten"
systemctl daemon-reload
systemctl enable --now kufgem-infoscreen-api.service
systemctl set-default graphical.target
systemctl enable lightdm.service
systemctl restart lightdm.service
echo
echo "KUFGEM InfoScreen installiert."
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo "Admin-Token: $(cat /etc/kufgem-infoscreen/admin-token)"
echo "Token auch später abrufbar: sudo cat /etc/kufgem-infoscreen/admin-token"
echo "Bei Bedarf neu starten: sudo reboot"
echo "Info: Die Weboberfläche ist nur für vertrauenswürdige LANs gedacht (noch kein HTTPS)."

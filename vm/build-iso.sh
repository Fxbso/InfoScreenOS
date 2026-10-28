#!/usr/bin/env bash
# Build a Debian Trixie amd64 LIVE ISO for VirtualBox, no browser inside the VM.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(uname -m)" != "x86_64" ]]; then echo "Use an amd64 Debian builder" >&2; exit 1; fi
command -v lb >/dev/null || { echo "Install: sudo apt install live-build" >&2; exit 1; }
command -v dpkg-deb >/dev/null || { echo "Install: sudo apt install dpkg-dev" >&2; exit 1; }
command -v gpg >/dev/null || { echo "GnuPG missing: sudo apt install gnupg" >&2; exit 1; }
ARCH=amd64 bash "$ROOT/packaging/build-deb.sh"
OUTPUT="$ROOT/dist"
BUILD="$ROOT/.build/vm-iso"
mkdir -p "$BUILD"
cd "$BUILD"
sudo lb clean --purge 2>/dev/null || true
lb config --mode debian --distribution trixie --architectures amd64 --binary-images iso-hybrid --system live --archive-areas "main non-free-firmware" --mirror-bootstrap https://deb.debian.org/debian/ --mirror-chroot https://deb.debian.org/debian/ --mirror-binary https://deb.debian.org/debian/ --debian-installer none --apt-recommends false --security false
mkdir -p config/package-lists config/packages.chroot config/hooks/live config/includes.chroot/etc/lightdm/lightdm.conf.d config/includes.chroot/usr/share/xsessions config/includes.chroot/usr/local/bin
cat >config/package-lists/infoscreen.list.chroot <<'EOF'
live-boot
live-config
systemd-sysv
linux-image-amd64
lightdm
lightdm-gtk-greeter
dbus-x11
xserver-xorg-core
xserver-xorg-video-fbdev
xserver-xorg-input-libinput
x11-xserver-utils
python3
python3-pygame
libsdl2-2.0-0
ca-certificates
gnupg
network-manager
sudo
EOF
cp "$OUTPUT"/kufgem-infoscreen_*_amd64.deb config/packages.chroot/
cat >config/includes.chroot/etc/lightdm/lightdm.conf.d/99-infoscreen.conf <<'EOF'
[Seat:*]
autologin-user=user
user-session=infoscreen
autologin-user-timeout=0
EOF
cat >config/includes.chroot/usr/share/xsessions/infoscreen.desktop <<'EOF'
[Desktop Entry]
Name=KUFGEM InfoScreen
Comment=Native InfoScreen on VirtualBox
Exec=/usr/local/bin/infoscreen-vm-session
Type=Application
EOF
cat >config/includes.chroot/usr/local/bin/infoscreen-vm-session <<'EOF'
#!/bin/sh
export SDL_VIDEODRIVER=x11
export SDL_AUDIODRIVER=dummy
export INFOSCREEN_DATA_DIR=/var/lib/kufgem-infoscreen
exec /usr/bin/python3 /opt/kufgem-infoscreen/display/renderer.py
EOF
chmod +x config/includes.chroot/usr/local/bin/infoscreen-vm-session
cat >config/hooks/live/9990-vm-services.hook.chroot <<'EOF'
#!/bin/sh
set -e
systemctl disable kufgem-infoscreen-display.service || true
systemctl enable kufgem-infoscreen-api.service lightdm.service NetworkManager.service || true
EOF
chmod +x config/hooks/live/9990-vm-services.hook.chroot
# Ubuntu's older live-build generates the obsolete trixie/updates security suite.
# The VM-only development live ISO disables that generator; security updates
# are provided using Debian's official trixie-security suite in the live filesystem.
mkdir -p config/includes.chroot/etc/apt/sources.list.d
cat >config/includes.chroot/etc/apt/sources.list.d/infoscreen-security.list <<'EOF'
deb https://security.debian.org/debian-security trixie-security main
EOF
sudo lb build
ISO="$(find . -maxdepth 1 -name '*.iso' -print -quit)"
test -n "$ISO"
cp "$ISO" "$OUTPUT/KUFGEM-InfoScreenOS-VM-amd64.iso"
sha256sum "$OUTPUT/KUFGEM-InfoScreenOS-VM-amd64.iso" > "$OUTPUT/KUFGEM-InfoScreenOS-VM-amd64.iso.sha256"
echo "ISO: $OUTPUT/KUFGEM-InfoScreenOS-VM-amd64.iso"

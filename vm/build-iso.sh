#!/usr/bin/env bash
# Build a Debian Trixie amd64 LIVE ISO for VirtualBox, no browser inside the VM.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(uname -m)" != "x86_64" ]]; then echo "Use an amd64 Debian builder" >&2; exit 1; fi
command -v lb >/dev/null || { echo "Install: sudo apt install live-build" >&2; exit 1; }
command -v dpkg-deb >/dev/null || { echo "Install: sudo apt install dpkg-dev" >&2; exit 1; }
command -v gpg >/dev/null || { echo "GnuPG missing: sudo apt install gnupg" >&2; exit 1; }
OUTPUT="$ROOT/dist"
BUILD="$ROOT/.build/vm-iso"
mkdir -p "$BUILD" "$OUTPUT"
cd "$BUILD"
sudo lb clean --purge 2>/dev/null || true
lb config --mode debian --distribution trixie --architectures amd64 --binary-images iso-hybrid --system live --initsystem systemd --archive-areas "main non-free-firmware" --mirror-bootstrap https://deb.debian.org/debian/ --mirror-chroot https://deb.debian.org/debian/ --mirror-binary https://deb.debian.org/debian/ --debian-installer false --apt-recommends false --security false --linux-packages none
# Ship real BIOS Syslinux files, not live-build's absolute symlinks.
# The Ubuntu theme can contain dangling symlinks even with isolinux installed.
mkdir -p config/bootloaders/isolinux
cp -a /usr/share/live/build/bootloaders/isolinux/. config/bootloaders/isolinux/
ISOLINUX_BIN="$(dpkg -L isolinux | grep -E '/isolinux[.]bin$' | head -1)"
BIOS_MODULES="/usr/lib/syslinux/modules/bios"
test -n "$ISOLINUX_BIN" && test -s "$ISOLINUX_BIN" || {
  echo "FATAL: isolinux.bin missing from installed isolinux package" >&2; exit 1;
}
test -s "$BIOS_MODULES/vesamenu.c32" || {
  echo "FATAL: Syslinux BIOS modules missing" >&2; exit 1;
}
rm -f config/bootloaders/isolinux/isolinux.bin
cp -L "$ISOLINUX_BIN" config/bootloaders/isolinux/isolinux.bin
for module in "$BIOS_MODULES"/*.c32; do
  target="config/bootloaders/isolinux/$(basename "$module")"
  rm -f "$target"
  cp -L "$module" "$target"
done
test -s config/bootloaders/isolinux/isolinux.bin
test -s config/bootloaders/isolinux/vesamenu.c32
mkdir -p config/package-lists config/hooks/live config/includes.chroot/etc/lightdm/lightdm.conf.d config/includes.chroot/usr/share/xsessions config/includes.chroot/usr/local/bin config/includes.chroot/opt/kufgem-infoscreen config/includes.chroot/etc/systemd/system config/includes.chroot/var/lib/kufgem-infoscreen
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
# Avoid config/packages.chroot: older live-build versions try to GPG-sign a
# temporary local APT repository before gnupg exists in the debootstrap chroot.
# Copy architecture-independent application sources directly into the image.
cp -a "$ROOT/backend" "$ROOT/display" "$ROOT/dashboard" config/includes.chroot/opt/kufgem-infoscreen/
cp "$ROOT/packaging/kufgem-infoscreen-api.service" config/includes.chroot/etc/systemd/system/
cp "$ROOT/packaging/kufgem-infoscreen-display.service" config/includes.chroot/etc/systemd/system/
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
# VM display uses X11/LightDM. The direct KMS/DRM unit is Pi-only.
systemctl disable kufgem-infoscreen-display.service || true
id infoscreen >/dev/null 2>&1 || adduser --system --group --home /var/lib/kufgem-infoscreen --no-create-home infoscreen
install -d -m 0755 -o infoscreen -g infoscreen /var/lib/kufgem-infoscreen
install -d -m 0750 /etc/kufgem-infoscreen
if [ ! -s /etc/kufgem-infoscreen/admin-token ]; then
  head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \\n' > /etc/kufgem-infoscreen/admin-token
fi
chown root:infoscreen /etc/kufgem-infoscreen/admin-token
chmod 0640 /etc/kufgem-infoscreen/admin-token
# Live media are shared: the token is therefore only a demo secret.
# Production images must provision their own unique token on first boot.
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

#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${VERSION:-0.1.0}"
ARCH="${ARCH:-arm64}"
case "$ARCH" in arm64|amd64) ;; *) echo "Unsupported architecture: $ARCH" >&2; exit 2;; esac
OUT="${OUT:-$PWD/dist}"
mkdir -p "$OUT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/DEBIAN" "$TMP/opt/kufgem-infoscreen" "$TMP/lib/systemd/system" "$TMP/usr/share/doc/kufgem-infoscreen"
cp -r backend dashboard display "$TMP/opt/kufgem-infoscreen/"
cp packaging/*.service "$TMP/lib/systemd/system/"
cat >"$TMP/DEBIAN/control" <<EOF
Package: kufgem-infoscreen
Version: $VERSION
Section: misc
Priority: optional
Architecture: $ARCH
Depends: python3, python3-pygame, libsdl2-2.0-0
Maintainer: KUFGEM InfoScreen Team
Description: Native InfoScreen display and dashboard for Raspberry Pi
EOF
cp packaging/postinst "$TMP/DEBIAN/postinst"
cp packaging/postrm "$TMP/DEBIAN/postrm"
chmod 0755 "$TMP/DEBIAN/"*
dpkg-deb --root-owner-group --build "$TMP" "$OUT/kufgem-infoscreen_${VERSION}_${ARCH}.deb"
echo "Built $OUT/kufgem-infoscreen_${VERSION}_arm64.deb"

#!/usr/bin/env bash
# Build on a supported Debian/Raspberry Pi OS ARM64 host with enough RAM/disk.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEY="${SSH_PUBLIC_KEY:-$HOME/.ssh/id_ed25519.pub}"
if [[ ! -f "$KEY" ]]; then
 echo "An SSH public key is required: SSH_PUBLIC_KEY=/path/to/key.pub" >&2; exit 1
fi
if [[ "$(uname -m)" != "aarch64" ]]; then
 echo "Warning: cross-building on $(uname -m) is not officially supported by rpi-image-gen." >&2
fi
bash "$ROOT/packaging/build-deb.sh"
DEB="$(ls -1 "$ROOT"/dist/kufgem-infoscreen_*_arm64.deb | tail -1)"
BUILDER="${RPI_IMAGE_GEN_DIR:-$ROOT/.build/rpi-image-gen}"
if [[ ! -x "$BUILDER/rpi-image-gen" ]]; then
 echo "Clone official builder into $BUILDER"
 mkdir -p "$(dirname "$BUILDER")"
 git clone --depth 1 https://github.com/raspberrypi/rpi-image-gen.git "$BUILDER"
 echo "Install builder dependencies as documented upstream: sudo $BUILDER/install_deps.sh"
fi
CFG="$ROOT/.build/infoscreen-rpi4.yaml"
mkdir -p "$(dirname "$CFG")"
PUBKEY="$(cat "$KEY")"
cat > "$CFG" <<EOF
device:
  layer: rpi4
  hostname: kufgem-infoscreen
  user1: infoscreenadmin
image:
  layer: image-rpios
  boot_part_size: 256M
  root_part_size: 3072M
ssh:
  pubkey_user1: "$PUBKEY"
  pubkey_only: y
packages:
  - "$DEB"
EOF
echo "Building image using $CFG"
cd "$BUILDER"
./rpi-image-gen build -S "$ROOT" -c "$CFG"
echo "Check $BUILDER/work/ for built .img files. Validate on actual Pi 4B before release."

# KUFGEM InfoScreen OS

Own native InfoScreen software for Raspberry Pi **4 Model B**, without Chromium or a desktop session. Includes a web management dashboard, a native fullscreen SDL2-based display, Debian packaging and an experimental custom image build recipe.

**Status: 0.1.0-alpha source implementation; not yet field tested on hardware. No downloadable OS image or APT feed is published yet.**

## Included
- Native Python/Pygame display using SDL2, designed for KMS/DRM.
- Responsive browser dashboard used on a separate PC: drag widgets, edit colors, messages and positions.
- Lightweight Python standard-library API; no database or Chromium required.
- Local JSON layout, periodically reread by display.
- Clock/date and text display. Weather, rail and traffic are placeholders for future API connectors.
- Per-device administrator token protecting config changes (trusted LAN only until TLS is implemented).
- systemd services to start display and API at boot, with crash restart.
- ARM64 Debian package script, GitHub Actions package CI.
- Initial image-build script based on official Raspberry Pi rpi-image-gen.

## Quick start for developers
```bash
python3 -m unittest discover -s tests
INFOSCREEN_DATA_DIR=/tmp/infoscreen-dev INFOSCREEN_TOKEN_FILE=/tmp/infoscreen-token python3 backend/app.py
```
For development, create `/tmp/infoscreen-token` containing a random token and restrict permissions before running the server. Visit `http://127.0.0.1:8080` on the same machine.

## VirtualBox VM ISO (experimental)

A separate Debian Live ISO build for VirtualBox is now included. It uses the same InfoScreen app but an X11 SDL2 video backend inside the VM (no browser). See [vm/README.md](vm/README.md). The GitHub Actions workflow **Build VirtualBox Live ISO** can build and upload the ISO as a workflow artifact when manually triggered. The workflow has not yet been verified to complete successfully.

## Build / install
See [docs/INSTALL.md](docs/INSTALL.md). On a suitable ARM64 builder:
```bash
bash packaging/build-deb.sh
```
For an experimental image build:
```bash
SSH_PUBLIC_KEY="$HOME/.ssh/id_ed25519.pub" bash image/build-image.sh
```

## Target deployment
Flash a **tested** InfoScreen OS image to SD, power on, HDMI display launches automatically, configure the layout from a PC. A future signed APT repository will be embedded for normal `apt upgrade` updates.

## Security and data
No personal user data, no backup subsystem. The Pi stores only local layout settings and its administration token. The dashboard must remain on a trusted internal network until HTTPS/reverse proxy support is in place.

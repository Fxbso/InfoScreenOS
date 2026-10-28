# Raspberry Pi 4B – build and deployment

This project currently provides source files and an **unvalidated image-build recipe**, not a tested OS image.

## Target
Raspberry Pi 4 Model B, Raspberry Pi OS Lite ARM64 base, native HDMI via SDL2 KMS/DRM. No Chromium or desktop session.

## Debian package
Build on a Linux host with dpkg-deb:

```bash
bash packaging/build-deb.sh
```

Output: `dist/kufgem-infoscreen_0.1.0_arm64.deb`. To smoke-test on an existing Raspberry Pi OS Lite ARM64 installation:

```bash
sudo apt install ./dist/kufgem-infoscreen_0.1.0_arm64.deb
sudo systemctl status kufgem-infoscreen-api kufgem-infoscreen-display
```

Display requires a real HDMI connector, working DRM/KMS kernel stack and SDL2 KMSDRM support. Verify with `journalctl -u kufgem-infoscreen-display -b`.

## OS image
Use Raspberry Pi's [rpi-image-gen](https://github.com/raspberrypi/rpi-image-gen) on a supported ARM64 Debian/Raspberry Pi OS builder. Provision SSH with your public key; no password is bundled.

```bash
export SSH_PUBLIC_KEY="$HOME/.ssh/id_ed25519.pub"
bash image/build-image.sh
```

First run clones the upstream builder and prints dependency instructions. Run `sudo .build/rpi-image-gen/install_deps.sh` then run the script again. The builder's output should be checked under `.build/rpi-image-gen/work`. Do not release until the image has been boot-tested on a Raspberry Pi 4B.

## Dashboard
Reach `http://kufgem-infoscreen.local:8080` if mDNS resolution works, otherwise use the Pi's LAN IP at port 8080. Log in using the per-device admin token (retrieve on the Pi over SSH):

```bash
sudo cat /etc/kufgem-infoscreen/admin-token
```

The dashboard uses an HTTP bearer token. **Keep it on a trusted internal network only**: HTTP is not encrypted. For broader deployment, add TLS and firewall rules before opening access. No user-account database is used.

## Updating
The `.deb` installation is functional for manual install. **A signed public APT repository has not yet been published**, so `sudo apt install kufgem-infoscreen` on a fresh Raspberry Pi OS installation is not available yet. A later OS image will have the signed APT source baked in.

## Limitations
Weather, train and road widgets are placeholders; image backgrounds, external data connectors, multi-display control and any packaged update repository are not yet implemented. There is no backup system by design. Local layout settings will be lost if the Pi or SD card is replaced.

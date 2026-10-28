# KUFGEM InfoScreen OS

Native, browser-free information display for Raspberry Pi 3B+, with a separate web management dashboard.

> **Status:** Foundation / planning. No installable OS image or APT package has been released yet.

## Goals
- Raspberry Pi 3 Model B+ (1 GB RAM), Raspberry Pi OS Lite 64-bit base.
- Native fullscreen HDMI rendering without Chromium or a desktop.
- Responsive web dashboard accessed from another computer.
- Adjustable background images, colors, fonts, widget positions and sizes.
- Widgets for clock, weather, Austrian train departures, traffic and company announcements.
- Extensible widget architecture and resilient live-data caching.
- Reproducible OS image builds; signed ARM64 Debian packages and embedded APT source.
- Boot-time autostart and crash recovery with systemd.
- No personal user data or backup system. Display configuration is stored locally and can be reset on replacement hardware.

## Planned repository structure

```text
display/            Native renderer; SDL2/DRM-KMS proof of concept first
backend/            API, config, caching and data connectors
dashboard/          Browser-based editor (production build served by backend)
widgets/            Widget implementations / interfaces
packaging/          Debian packaging and systemd units
image/              Custom Raspberry Pi OS image recipes
.github/workflows/  CI and release automation
tests/              Automated tests
```

## v0.1.0-alpha acceptance criteria
1. Validate direct HDMI output via DRM/KMS on the actual Raspberry Pi 3B+.
2. Boot into fullscreen clock display with a configurable image background.
3. Edit and apply the layout from another computer via the local web dashboard.
4. Start automatically on boot; restart after a crash.
5. Build an installable `kufgem-infoscreen` ARM64 Debian package.
6. Build a flashable `.img.xz` with InfoScreen and its APT repository preconfigured.
7. Test the full install/boot/update cycle on real hardware.

## Installation (future release)

Flash a published InfoScreen OS image using Raspberry Pi Imager, then boot the Pi. The software should start automatically. Future versions will update through:

```bash
sudo apt update
sudo apt upgrade
```

There is **no installable release yet**. Do not attempt `apt install kufgem-infoscreen` until the package and signed repository have been published.

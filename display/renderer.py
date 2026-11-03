#!/usr/bin/env python3
"""Native full-screen display. Editor-only dark cards never render on the screen."""
import datetime
import json
import os
import pathlib
import shutil
import socket
import sys
import threading
import time

import pygame

DATA = pathlib.Path(os.environ.get("INFOSCREEN_DATA_DIR", "/var/lib/kufgem-infoscreen"))
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
clock = pygame.time.Clock()
layout = {}
background_image = None
background_mtime = None
last_load = 0.0
weather_data = {}
weather_lock = threading.Lock()
last_weather_request = 0.0

TITLES = {
    "clock": "UHR", "date": "DATUM", "weather": "WETTER",
    "traffic": "VERKEHR", "departures": "ABFAHRTEN",
    "hostname": "GERÄT", "uptime": "LAUFZEIT",
    "system": "SYSTEM",
}


def color(value, default="#ffffff"):
    try:
        return pygame.Color(value)
    except (TypeError, ValueError):
        return pygame.Color(default)


# Explicit regular files avoid pygame SysFont selecting Lato Hairline/Thin
# when the family contains multiple installed weights.
FONT_FILES = {
    "lato": (
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Semibold.ttf",
    ),
    "liberation": (
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ),
    "dejavu": (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
}
FONT_CACHE = {}

def font(size, bold=False):
    family = layout.get("fontFamily", "lato")
    regular, heavier = FONT_FILES.get(family, FONT_FILES["lato"])
    path = heavier if bold else regular
    if not pathlib.Path(path).is_file():
        path = regular
    if not pathlib.Path(path).is_file():
        path = pygame.font.match_font("dejavusans") or None
    key = (path, max(13, int(size)))
    if key not in FONT_CACHE:
        FONT_CACHE[key] = pygame.font.Font(path, key[1])
    return FONT_CACHE[key]


def draw_text(value, x, y, size, ink, width, shadow=True, bold=False):
    """One or two uncluttered lines, fitted to the widget width."""
    value = str(value).strip()
    if not value or width < 12:
        return
    size = max(14, int(size))
    face = font(size, bold)
    lines = []
    for paragraph in value.splitlines()[:2]:
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = (line + " " + word).strip()
            if line and face.size(candidate)[0] > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        if len(lines) >= 2:
            break
    if not lines:
        return
    for index, line in enumerate(lines[:2]):
        while line and face.size(line)[0] > width:
            line = line[:-1]
        if not line:
            continue
        surface = face.render(line, True, color(ink))
        px, py = int(x), int(y + index * size * 1.3)
        if shadow:
            # Single soft drop shadow, never an outlined/WordArt look.
            shadow_surface = face.render(line, True, (12, 20, 32))
            shadow_surface.set_alpha(130)
            screen.blit(shadow_surface, (px + 1, py + 2))
        screen.blit(surface, (px, py))


def weather_worker():
    global weather_data
    try:
        if "/opt/kufgem-infoscreen/backend" not in sys.path:
            sys.path.insert(0, "/opt/kufgem-infoscreen/backend")
        import app
        values = app.widget_data().get("widgets", {})
        with weather_lock:
            weather_data = values
    except Exception:
        pass


def widget_value(widget):
    kind = widget.get("type")
    source = widget.get("source") or {}
    now = datetime.datetime.now()
    if kind == "clock":
        return now.strftime("%H:%M")
    if kind == "date":
        return now.strftime("%d. %B %Y")
    if kind == "message":
        return widget.get("text", "").strip()
    if kind == "hostname":
        return socket.gethostname()
    if kind == "uptime":
        try:
            seconds = int(float(pathlib.Path("/proc/uptime").read_text().split()[0]))
            return f"{seconds // 86400} T · {(seconds % 86400) // 3600} Std."
        except (OSError, ValueError, IndexError):
            return ""
    if kind == "system":
        try:
            disk = shutil.disk_usage("/")
            return f"{disk.free // (1024**3)} GB frei"
        except OSError:
            return ""
    if kind == "divider":
        return "──────────"
    if kind in ("weather", "traffic", "departures"):
        if source.get("provider") == "manual":
            return source.get("text", "").strip()
        if kind == "weather" and source.get("provider") == "open-meteo":
            with weather_lock:
                data = weather_data.get(widget.get("id"), {})
            return data.get("text", "").strip() if data.get("ok") else ""
        return ""
    return ""


def redraw():
    width, height = screen.get_size()
    screen.fill(color(layout.get("background", "#101b2d"), "#101b2d"))
    if background_image is not None:
        screen.blit(pygame.transform.smoothscale(background_image, (width, height)), (0, 0))

    # The real InfoScreen deliberately ignores editor-only overlayOpacity,
    # widgetOpacity, panelOpacity and radius. No dark boxes on the live display.
    # The layout title is metadata in the editor, not a second overlay on
    # top of a clock. A screen heading is opt-in for layouts that need one.
    title = layout.get("title", "KUFGEM InfoScreen")
    if layout.get("showScreenTitle", False) and title:
        draw_text(title, width * .035, height * .026, height * .020,
                  "#ffffff", width * .9)

    for widget in layout.get("widgets", []):
        try:
            kind = widget["type"]
            value = widget_value(widget)
            if not value and widget.get("showIfEmpty", False) is not True:
                continue
            if not value:
                continue
            x = widget["x"] * width / 100
            y = widget["y"] * height / 100
            available_width = max(16, widget["w"] * width / 100)
            available_height = max(16, widget["h"] * height / 100)
            ink = widget.get("color", "#ffffff")
            scale = max(.6, min(1.6, widget.get("fontScale", 50) / 50))
            padding = max(4, height * .008)
            if kind in ("message", "divider"):
                # Keep information panels visually quiet, without giant bold
                # headings sitting on top of the background photo.
                base = .035 if kind == "message" else .022
                draw_text(value, x + padding, y + padding,
                          min(height * base * scale, available_height * .32),
                          ink, available_width - padding * 2, bold=False)
                continue
            small_label = widget.get("title") or TITLES.get(kind, kind.upper())
            draw_text(small_label, x + padding, y + padding,
                      min(height * .016, available_height * .14),
                      "#ffffff", available_width - padding * 2, bold=False)
            base = .045 if kind == "clock" else .033 if kind == "date" else .030
            draw_text(value, x + padding, y + padding + height * .031,
                      min(height * base * scale, available_height * .32),
                      ink, available_width - padding * 2, bold=False)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit
    now = time.monotonic()
    if now - last_load > 1:
        last_load = now
        pic = DATA / "background.img"
        try:
            mtime = pic.stat().st_mtime_ns
            if mtime != background_mtime:
                background_image = pygame.image.load(str(pic)).convert()
                background_mtime = mtime
        except (OSError, pygame.error):
            background_image = None
            background_mtime = None
        try:
            candidate = json.loads((DATA / "layout.json").read_text(encoding="utf-8"))
            if isinstance(candidate, dict) and isinstance(candidate.get("widgets"), list):
                layout = candidate
        except (OSError, ValueError):
            pass
    if now - last_weather_request > 60:
        last_weather_request = now
        threading.Thread(target=weather_worker, daemon=True).start()
    if not layout:
        layout = {"title": "KUFGEM InfoScreen", "widgets": [
            {"type": "clock", "x": 6, "y": 20, "w": 40, "h": 24}
        ]}
    redraw()
    pygame.display.flip()
    clock.tick(10)

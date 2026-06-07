#!/usr/bin/env python3
# <xbar.title>Solo - Active Projects</xbar.title>
# <xbar.version>1.0</xbar.version>
# <xbar.author>Slava Abakumov</xbar.author>
# <xbar.author.github>slaFFik</xbar.author.github>
# <xbar.desc>Shows Solo projects with a running process; toggle to show all.</xbar.desc>
# <xbar.abouturl>https://github.com/slaFFik/solo-menubar</xbar.abouturl>
# <xbar.image>https://raw.githubusercontent.com/slaFFik/solo-menubar/refs/heads/main/assets/screenshot.png</xbar.image>
# <xbar.dependencies>python3,Solo</xbar.dependencies>
#
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
# <swiftbar.refreshOnOpen>true</swiftbar.refreshOnOpen>
#
# Reads Solo's local HTTP control plane (no auth token needed for the bare
# read-only endpoints) and lists Solo projects. By default it shows only those
# with a running process; a menu toggle switches to all projects. Solo must be
# running with the HTTP API enabled.
#
# Symlink this file into your SwiftBar plugin folder. With no interval in the
# filename (solo-menubar.py), SwiftBar refreshes it only when the menu opens (via
# the swiftbar.refreshOnOpen flag above) and on launch — no background polling.
# Add an interval to poll too, e.g. solo-menubar.30s.py for every 30 seconds.

import base64
import json
import os
import struct
import sys
import urllib.request
import zlib

DISCOVERY = os.path.expanduser("~/.config/soloterm/http-api.json")
DEFAULT_ORIGIN = "http://127.0.0.1:24678"

# Persisted UI preferences, toggled from the menu and re-read on every refresh.
# Kept out of Solo's own config dir so it is clearly ours.
SETTINGS = os.path.expanduser("~/.config/solo-menubar/settings.json")

# Menu bar icon: base64-encoded PNG embedded directly so SwiftBar does not
# treat a sidecar image file as its own (broken) plugin. To change the icon,
# regenerate ICON_B64 from a PNG, e.g.:
#   python3 -c "import base64;print(base64.b64encode(open('icon.png','rb').read()).decode())"
ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAAAXNSR0IArs4c6QAAAHhlWElmTU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAACQAAAAAQAAAJAAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAACSgAwAEAAAAAQAAACQAAAAA+INbXQAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAA3FJREFUWAntWE1oE0EUfrO7SZo2tUmbWtSikP4lFIvY4slLFapnvYhIC97Eg0KxIHi0B0UEEb2K9VLw4kUL9SCKtiAeq9TaUpRKwSbpr7ZJdnd8b3SbNNnupDEpFfpgdt+8N/O9b+d/h0GGtKAopnEFTV2Y6jF5MtzFVBMINoNp2FTUe59RLHBmKZGmpj4A3o95zbJt01tnwK9/+jJ1h+Kp9PhL5haqCuW3WTAm6woGq5ejsfgoC4dDzcxQPiKJ7W6Z7O/WVWBtCpK5apEpi7SJQsm6ELA9IaEb3hCYag1wxYfvumwQaZ7q/KlbA4RFQtgUg8SKiapmcH4Zm0sMYPJBxZEO8V6rDwP4I0LXy8NgaHsFqO46IGxbeVAdIkQYhCUEsUUMzFgxhZ1BFxGi2bRT5CARKtXULuQjPURoR8kuIVl37LbQbgvJWkDm/9/HkFv2gbl+5sq1OVi2tMPr7kbQ3Q3AzBUHyLSLK5WYYaClvqaNEm1LhOi4lPQek0BudLtX3280SHJ5jyHDtQ9UfRrhuAQy081FHcO1P9PoqOfdQkt1/aAmJrADdEfAbOdq1VnQPc1QNdub7bLN50GIAeMcTDqgeY/aguRjJIx8REooVdkOnoU34FkeAo6HrEJE0X/gcfA7JCrPgCf2whFCSsjwHYZYxwgw45cjkJPTQGcsdB60n+NOxYRvc0KM/pAwmavAcS3hWpUUTFoAsQSmwLbvws0JKRqwlm4ojz6BNXMJcQpYFDMZ8iR448+AhXsAEgvoSWZ61/XNCWER1n5DnG+Ld8Y9JQLz0WvrBLIV23XI9JQDLE4C59T7xRWBidhmWYUtsG0LxU9exOZ5DNp0PyjuGtuKhRrNZBT0SCvET/SA/93THBgiRD/+G3rF8AVg9sLNnMLFNGiLc3ZwCSI0g6mBvKq/GpiqQnDoIURPX8KZ9Y8DmUBthOlJjPEAA6oiZkaRb0RoGNMlMhrzMTh0fwCCH0agaewRmUomrDEAFecGYPn1y3QMDsPWZcMYWl2A64PveCe4qmvThUqopeJzsPL2Fe7XYk1KgWG2ivshvI7BechvlzC2FJoz6B2fmLwr7oei8fhIMBhYwW20E2sKmxSheAVSSKaPyBDkevBobH601u8fxG5TcMcIoM+HicZYKYRm9jQerQbBNLvHJ6eeW0F+A/ke69L4jOXQAAAAAElFTkSuQmCC"


def icon_param():
    return "image=" + ICON_B64


# Active-project indicator: a small green donut. SwiftBar renders SF Symbols as
# template (monochrome) images and tints them to the menu's label color, so
# sfcolor/sfconfig can't actually colorize them in a dropdown — a base64 PNG via
# image= is the only way to get a true-color glyph. We draw it here at runtime
# with the standard library so the plugin keeps zero third-party dependencies.
# Tune these three:
RING_COLOR = (0x1B, 0x88, 0x2D)     # #1B882D — active project
INACTIVE_COLOR = (0x8E, 0x8E, 0x93)  # systemGray ring — idle project (only in "all" view)
INACTIVE_LABEL = "#333333,#9b9b9b"   # idle project name (light,dark): dim but readable
BRANCH_COLOR = "#666666,#9b9b9b"     # the "└ N TODOs · M scratchpads" tree row
RING_PT = 9                      # on-screen diameter, in points
RING_STROKE = 0.22               # ring thickness as a fraction of the diameter
RING_DROP = 1.5                  # points to sink the ring. SwiftBar centers the
                                 # icon on the font's box, which rides above
                                 # lowercase text; this drops it onto the optical
                                 # center. Raise to move down, lower to move up.


def _png(width, height, rgba, dpi):
    """Encode a row-major RGBA byte buffer (4 bytes/px) as a PNG."""
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    # pHYs carries the resolution so NSImage reports the intended point size;
    # baking 144 dpi means the 2x-pixel PNG renders crisply at RING_PT on Retina.
    ppm = int(round(dpi / 0.0254))
    phys = struct.pack(">IIB", ppm, ppm, 1)
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (none) for each scanline
        raw.extend(rgba[y * stride:(y + 1) * stride])
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", ihdr) +
            chunk(b"pHYs", phys) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            chunk(b"IEND", b""))


def ring_b64(color=RING_COLOR):
    """Anti-aliased donut as a base64 PNG (supersampled, then averaged)."""
    px = RING_PT * 2            # render at 2x; pHYs below bakes the matching dpi
    ss = 4                      # supersample factor for smooth edges
    n = px * ss
    outer = n / 2 - ss          # a hair of padding so the ring never clips
    inner = outer * (1 - 2 * RING_STROKE)
    center = (n - 1) / 2
    cov = [0.0] * (px * px)
    for sy in range(n):
        dy = sy - center
        row = (sy // ss) * px
        for sx in range(n):
            dx = sx - center
            if inner <= (dx * dx + dy * dy) ** 0.5 <= outer:
                cov[row + sx // ss] += 1
    area = ss * ss
    r, g, b = color
    # Transparent rows on top sink the (center-aligned) icon: with bottom padding
    # zero, the ring's center lands pad/2 px below the canvas center. At 2x, that
    # is RING_DROP points lower when pad = RING_DROP * 4.
    pad = int(round(RING_DROP * 4))
    height = px + pad
    out = bytearray(px * height * 4)
    base = pad * px
    for i, c in enumerate(cov):
        j = (base + i) * 4
        out[j], out[j + 1], out[j + 2] = r, g, b
        out[j + 3] = int(round(255 * c / area))
    return base64.b64encode(_png(px, height, bytes(out), 144)).decode()


def origin():
    """Base URL of Solo's HTTP API. Port can change across Solo restarts,
    so prefer the value Solo writes to its discovery file."""
    try:
        with open(DISCOVERY) as f:
            return json.load(f).get("origin", DEFAULT_ORIGIN)
    except Exception:
        return DEFAULT_ORIGIN


def get(path):
    with urllib.request.urlopen(origin() + path, timeout=2) as r:
        return json.load(r)


def load_settings():
    try:
        with open(SETTINGS) as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    with open(SETTINGS, "w") as f:
        json.dump(data, f)


def toggle_setting(key):
    s = load_settings()
    s[key] = not s.get(key, False)
    save_settings(s)


def api_config():
    """(baseUrl, token) for Solo's authenticated /api endpoints, read from the
    same discovery file as origin(). The token is local — Solo writes it there —
    so todo/scratchpad counts still need nothing from the user. (None, None) if
    unavailable."""
    try:
        with open(DISCOVERY) as f:
            cfg = json.load(f)
        base = cfg.get("baseUrl") or cfg.get("origin", DEFAULT_ORIGIN) + "/api"
        return base, cfg.get("token")
    except Exception:
        return None, None


def get_auth(base, token, path):
    req = urllib.request.Request(base + path)
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=2) as r:
        return json.load(r).get("data", {})


def project_counts(base, token, pid, want_todos, want_pads):
    """(open todo count, unarchived scratchpad count) for a project — only what
    is asked for. Failures degrade to zero so the menu never breaks."""
    todos = pads = 0
    try:
        if want_todos:
            data = get_auth(base, token, f"/projects/{pid}/todos")
            todos = sum(1 for t in data.get("todos", []) if not t.get("completed"))
        if want_pads:
            data = get_auth(base, token, f"/projects/{pid}/scratchpads")
            pads = sum(1 for s in data.get("scratchpads", []) if not s.get("archived"))
    except Exception:
        pass
    return todos, pads


def count_row(todos, pads, show_todos, show_pads):
    """The combined '└ N TODOs · M scratchpads' label, or None when there is
    nothing to show. Only enabled, non-zero counts appear."""
    parts = []
    if show_todos and todos:
        parts.append(f"{todos} TODO" + ("" if todos == 1 else "s"))
    if show_pads and pads:
        parts.append(f"{pads} scratchpad" + ("" if pads == 1 else "s"))
    return "└ " + " · ".join(parts) if parts else None


def deeplink(project_id, process_id, name):
    """Solo deep link to a specific process. The slug before '--' is cosmetic;
    Solo resolves the target by the trailing numeric process id."""
    slug = "".join(c if c.isalnum() else "-" for c in name.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-") or "x"
    return f"solo://proj/{project_id}/process/{slug}--{process_id}"


def clean(text):
    """Make a name safe for a SwiftBar line: '|' starts the params section and a
    newline starts a new menu item, so neutralize the pipe and collapse any
    whitespace (newlines, tabs) to single spaces."""
    return " ".join(text.replace("|", "│").split())


def main():
    try:
        # GET /projects -> every project, each with a nested processes[] list
        # ({id, name, command, status, ...}). Superset of /processes, so it
        # serves both the "active only" and "all projects" views.
        projects = get("/projects")
    except Exception:
        print(f" | {icon_param()}")
        print("---")
        print("Solo not running or HTTP API off | color=#999999")
        print("Open Solo | bash=/usr/bin/open param1=-a param2=Solo terminal=false")
        return

    settings = load_settings()
    show_all = bool(settings.get("show_all", False))
    show_todos = bool(settings.get("show_todos", False))
    show_pads = bool(settings.get("show_scratchpads", False))

    # Todo/scratchpad counts come from authenticated /api endpoints; fetch the
    # local token only when a counts toggle is on, and degrade if it's missing.
    api_base, token = api_config() if (show_todos or show_pads) else (None, None)
    counts_on = bool(token) and (show_todos or show_pads)

    # Menu bar title: Solo logo only.
    print(f" | {icon_param()}")
    print("---")

    visible = []
    for proj in projects:
        running = [p for p in proj.get("processes", []) if p.get("status") == "running"]
        if running or show_all:
            visible.append((proj, running))

    if not visible:
        print("No active projects | color=#999999")
    else:
        active_icon = ring_b64()
        idle_icon = ring_b64(INACTIVE_COLOR) if show_all else None
        for proj, running in sorted(visible, key=lambda v: v[0]["name"].lower()):
            pid, name = proj["id"], proj["name"]
            procs = proj.get("processes", [])
            # Open Solo focused on a process; prefer a running one. A bare
            # solo://proj/{id} link opens Settings, not the project, so we always
            # target a process — the header and the counts row share this link.
            target = running[0] if running else (procs[0] if procs else None)
            href = f" href={deeplink(pid, target['id'], target['name'])}" if target else ""
            if running:
                print(f"{clean(name)} |{href} image={active_icon}")
                # Each running agent deep-links to its own process.
                for x in running:
                    print(f"--{clean(x['name'])} | href={deeplink(pid, x['id'], x['name'])}")
            else:
                # Idle project (only in "all" view): grey ring, dimmed.
                print(f"{clean(name)} |{href} image={idle_icon} color={INACTIVE_LABEL}")
            # Optional '└ N TODOs · M scratchpads' tree row, under any project.
            if counts_on:
                todos, pads = project_counts(api_base, token, pid, show_todos, show_pads)
                row = count_row(todos, pads, show_todos, show_pads)
                if row:
                    print(f"--{row} |{href} color={BRANCH_COLOR}")

    print("---")
    py, script = sys.executable, os.path.abspath(__file__)

    def toggle(label, key, on):
        return (f"{label} | checked={'true' if on else 'false'} bash={py} "
                f"param1={script} param2=--toggle-{key.replace('_', '-')} "
                f"terminal=false refresh=true")

    print(toggle("Show all projects", "show_all", show_all))
    print(toggle("Show TODOs", "show_todos", show_todos))
    print(toggle("Show Scratchpads", "show_scratchpads", show_pads))
    print("Open Solo | bash=/usr/bin/open param1=-a param2=Solo terminal=false")
    print("Refresh | refresh=true")


if __name__ == "__main__":
    KEYS = {"show_all", "show_todos", "show_scratchpads"}
    toggled = next((a[len("--toggle-"):].replace("-", "_")
                    for a in sys.argv[1:] if a.startswith("--toggle-")), None)
    if toggled in KEYS:
        toggle_setting(toggled)
    else:
        main()

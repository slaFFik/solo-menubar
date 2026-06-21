#!/usr/bin/env python3
# <xbar.title>Solo - Active Projects</xbar.title>
# <xbar.version>1.2.0</xbar.version>
# <xbar.author>Slava Abakumov</xbar.author>
# <xbar.author.github>slaFFik</xbar.author.github>
# <xbar.desc>Shows Solo projects with a running agent; click to open it in Solo, ⌥-click to stop; toggle to display the number of TODOs/scratchpads per project.</xbar.desc>
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
# Reads Solo's local HTTP control plane and lists Solo projects. Since Solo
# 0.8.2 every endpoint lives under /api behind bearer auth; the token comes
# from Solo's own discovery file, so the widget still needs nothing from the
# user. By default it shows only projects with a running process; a menu
# toggle switches to all projects. Clicking a running process opens it in
# Solo; ⌥-click stops it. Solo (>= 0.8.2) must be running with the HTTP API
# enabled.
#
# Symlink this file into your SwiftBar plugin folder. With no interval in the
# filename (solo-menubar.py), SwiftBar refreshes it only when the menu opens (via
# the swiftbar.refreshOnOpen flag above) and on launch — no background polling.
# Add an interval to poll too, e.g. solo-menubar.30s.py for every 30 seconds.

import base64
import json
import os
import sqlite3
import struct
import sys
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

DISCOVERY = os.path.expanduser("~/.config/soloterm/http-api.json")
# Solo's persistent store. The discovery file above only exists while a Solo
# with the API on is alive; the database remembers the user's settings across
# quits, which is what lets the error row tell "Solo closed" from "API off".
SOLO_DB = os.path.expanduser("~/.config/soloterm/solo.db")
API_VERSION = "1"  # Solo's bump-on-break HTTP API contract version we speak

# Solo is strictly local, so bypass proxies: the default urllib opener honors
# http_proxy/https_proxy and macOS system proxy settings, which would route
# 127.0.0.1 — bearer token included — through a proxy and break the menu.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

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


class ApiChanged(Exception):
    """The discovery file advertises an API contract this plugin doesn't speak."""


def api_config():
    """(base URL, token) of Solo's authenticated /api endpoints, from the
    discovery file Solo maintains. The port can change across Solo restarts and
    every request needs the bearer token, so both come from there. Raises when
    the file, token, or base URL is missing — the caller shows the 'not
    running' row."""
    with open(DISCOVERY) as f:
        cfg = json.load(f)
    # An apiVersion other than ours deserves its own row — 'not running' would
    # misdiagnose a Solo update. Absent means an old/stale file; let the
    # request itself fail into the generic row.
    version = cfg.get("apiVersion")
    if version is not None and str(version) != API_VERSION:
        raise ApiChanged(version)
    base = cfg.get("apiBaseUrl") or cfg["origin"] + "/api"
    return base, cfg["token"]


def load_settings():
    try:
        with open(SETTINGS) as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    # Write-then-rename: SwiftBar runs a toggle process and a refresh render
    # concurrently, so a reader must never see a half-written file, and a
    # killed toggle must not leave corrupt JSON that resets every preference.
    tmp = SETTINGS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, SETTINGS)


def toggle_setting(key):
    s = load_settings()
    s[key] = not s.get(key, False)
    save_settings(s)


def get_auth(base, token, path):
    req = urllib.request.Request(base + path)
    req.add_header("Authorization", "Bearer " + token)
    with OPENER.open(req, timeout=2) as r:
        # Index strictly: if Solo ever changes the envelope, fail into the
        # error row rather than render a healthy-looking empty menu.
        return json.load(r)["data"]


def post_auth(base, token, path):
    """POST to one of Solo's authenticated lifecycle endpoints. They take no
    body (data=b"" just forces the POST method), so this returns the parsed
    envelope's data without sending anything. Used by the Stop action."""
    req = urllib.request.Request(base + path, data=b"", method="POST")
    req.add_header("Authorization", "Bearer " + token)
    with OPENER.open(req, timeout=8) as r:
        return json.load(r)["data"]


def stop_process(process_id):
    """Stop one running Solo process, fired from a menu click. Best-effort and
    silent: a SwiftBar bash action has nowhere to surface an error, and the
    follow-up refresh just re-lists the process if the stop didn't take.
    Blocking on the POST is the whole point — it makes SwiftBar's refresh=true
    land only after Solo has actually replied, so the row visibly disappears.
    int() both coerces the id for the path and rejects junk into the no-op."""
    try:
        base, token = api_config()
        post_auth(base, token, f"/processes/{int(process_id)}/stop")
    except Exception:
        pass


def get_all(base, token, path, key):
    """Every item from a paginated list endpoint, following nextOffset pages
    until hasMore goes false. Asks for big pages (the server clamps at its own
    maximum) so the common case is a single request. A cursor that stalls or
    disappears raises instead of looping forever or silently truncating."""
    sep = "&" if "?" in path else "?"
    items, offset = [], 0
    while True:
        data = get_auth(base, token, f"{path}{sep}limit=200&offset={offset}")
        items.extend(data[key])
        if not data.get("hasMore"):
            return items
        nxt = data.get("nextOffset")
        if nxt is None or nxt <= offset:
            raise ValueError(f"pagination stalled at offset {offset}")
        offset = nxt


def project_counts(base, token, pid, want_todos, want_pads):
    """(open todo count, unarchived scratchpad count) for a project — only what
    is asked for. The server filters (completed=false; scratchpads exclude
    archived unless asked) and reports totalCount, so limit=1 fetches each
    count without the items. Failures degrade to zero so the menu never
    breaks."""
    todos = pads = 0
    try:
        if want_todos:
            data = get_auth(base, token, f"/projects/{pid}/todos?completed=false&limit=1")
            todos = data.get("totalCount", 0)
        if want_pads:
            data = get_auth(base, token, f"/projects/{pid}/scratchpads?limit=1")
            pads = data.get("totalCount", 0)
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
    Solo resolves the target by the trailing numeric process id. Keep the slug
    ASCII-only: SwiftBar hrefs are not percent-encoded, and a non-ASCII URL is
    a dead (silently ignored) link on older macOS."""
    slug = "".join(c if (c.isascii() and c.isalnum()) else "-" for c in name.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-") or "x"
    return f"solo://proj/{project_id}/process/{slug}--{process_id}"


def project_label(proj):
    """The name Solo's own UI shows: displayName when set, else name."""
    return proj.get("displayName") or proj.get("name", "")


def clean(text):
    """Make a name safe for a SwiftBar line: '|' starts the params section, a
    newline starts a new menu item, and a leading '--' would turn the row into
    a submenu entry of whatever came before it. Neutralize the pipe, collapse
    any whitespace to single spaces, and swap a leading ASCII dash for the
    look-alike Unicode hyphen so dashed names keep their nesting level."""
    s = " ".join(text.replace("|", "│").split())
    if s.startswith("-"):
        s = "‐" + s[1:]
    return s


STOP_GLYPH = "■"   # ■ filled square — leads the "Stop" label in the ⌥ view


def process_rows(py, script, proj_id, proc):
    """The two SwiftBar lines for one running process, sharing a single visible
    row via the Option-key alternate mechanism:

      * the primary row opens the process in Solo (a plain href leaf, so one
        click still focuses that window — the original behavior), and
      * the alternate row (alternate=true → shown only while ⌥ is held) replaces
        it in place with a Stop action that refreshes the menu, so the row drops
        out the moment Solo confirms the stop.

    Both are at the same submenu level and the alternate immediately follows its
    primary, which is how SwiftBar pairs them. The primary's tooltip advertises
    the otherwise-hidden ⌥ action."""
    name = clean(proc["name"])
    proc_id = proc["id"]
    primary = (f"--{name} | href={deeplink(proj_id, proc_id, proc['name'])} "
               f'tooltip="Click to open in Solo · hold ⌥ to stop"')
    stop = (f"--{STOP_GLYPH} Stop {name} | alternate=true "
            f'bash="{py}" param1="{script}" '
            f'param2=--stop-process param3={proc_id} '
            f'terminal=false refresh=true tooltip="Click to stop"')
    return [primary, stop]


def project_rows(api_base, token, projects, processes, show_all, show_todos, show_pads,
                 py, script):
    """The menu's project section, as a list of SwiftBar lines."""
    procs_by_project = {}
    for p in processes:
        procs_by_project.setdefault(p.get("projectId"), []).append(p)

    visible = []
    for proj in projects:
        procs = procs_by_project.get(proj["id"], [])
        running = [p for p in procs if p.get("status") == "running"]
        if running or show_all:
            visible.append((proj, procs, running))

    if not visible:
        return ["No active projects | color=#999999"]

    # Count fetches are independent per project; fan them out so menu-open
    # latency is the slowest request, not the sum of up to two per project.
    counts = {}
    if show_todos or show_pads:
        pids = [proj["id"] for proj, _, _ in visible]
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = ex.map(
                lambda pid: project_counts(api_base, token, pid, show_todos, show_pads),
                pids)
            counts = dict(zip(pids, results))

    rows = []
    active_icon = ring_b64()
    idle_icon = ring_b64(INACTIVE_COLOR) if show_all else None
    for proj, procs, running in sorted(visible, key=lambda v: project_label(v[0]).lower()):
        pid, name = proj["id"], project_label(proj)
        # Open Solo focused on a process; prefer a running one. A bare
        # solo://proj/{id} link opens Settings, not the project, so we always
        # target a process — the header and the counts row share this link.
        target = running[0] if running else (procs[0] if procs else None)
        href = f" href={deeplink(pid, target['id'], target['name'])}" if target else ""
        if running:
            rows.append(f"{clean(name)} |{href} image={active_icon}")
            # Each running process is one visible row: click opens it in Solo,
            # ⌥-click stops it (the alternate row emitted alongside).
            for x in running:
                rows.extend(process_rows(py, script, pid, x))
        else:
            # Idle project (only in "all" view): grey ring, dimmed.
            rows.append(f"{clean(name)} |{href} image={idle_icon} color={INACTIVE_LABEL}")
        # Optional '└ N TODOs · M scratchpads' tree row, under any project.
        if pid in counts:
            row = count_row(*counts[pid], show_todos, show_pads)
            if row:
                rows.append(f"--{row} |{href} color={BRANCH_COLOR}")
    return rows


def api_enabled_setting():
    """What Solo's own settings say about its HTTP API: True, False, or None
    when the database can't answer (missing, locked, or the key was renamed —
    Solo stores the toggle as 'raycast_api_enabled', the API's original
    Raycast-extension name). None makes the caller fall back to discovery-file
    heuristics, so a Solo schema change degrades to the old messages rather
    than misreporting the toggle's state."""
    try:
        # mode=ro so a read can never create or repair files in Solo's dir;
        # the db is WAL, so reading doesn't block a live Solo writing it.
        con = sqlite3.connect(f"file:{SOLO_DB}?mode=ro", uri=True, timeout=0.5)
        try:
            row = con.execute(
                "SELECT value FROM settings WHERE key = 'raycast_api_enabled'"
            ).fetchone()
        finally:
            con.close()
        return None if row is None else {"true": True, "false": False}.get(row[0])
    except Exception:
        return None


def failure_message():
    """The most truthful error row for a failed refresh, judged from what the
    failed request itself can't see. Three witnesses: Solo's settings database
    (is the HTTP API turned on — survives quitting Solo), the discovery file
    (did a live Solo publish the API — removed on clean quit), and the
    publishing pid (is that Solo still alive; signal 0 probes it without
    touching the process)."""
    enabled = api_enabled_setting()
    try:
        with open(DISCOVERY) as f:
            pid = json.load(f)["pid"]
        os.kill(pid, 0)
    except PermissionError:
        pass  # the pid exists but isn't ours — still proof Solo is alive
    except FileNotFoundError:
        # No published API. The settings db says whether that's because the
        # toggle is off or because Solo (which removes the file on quit)
        # simply isn't running.
        if enabled:
            return "Solo not running — open it"
        if enabled is None:
            return "Solo HTTP API not enabled — turn it on in Solo settings"
        return "Solo HTTP API disabled — turn it on in Solo settings"
    except Exception:
        # Unreadable file or dead pid: the Solo that published the API is
        # gone (a crash leaves this stale file behind).
        if enabled:
            return "Solo not running — open it"
        if enabled is None:
            return "Solo not running — open it, or re-enable its HTTP API"
        return "Solo not running — open it and re-enable its HTTP API"
    return "Solo is running, but its HTTP API isn't responding"


def error_menu(message):
    print(f" | {icon_param()}")
    print("---")
    print(f"{message} | color=#999999")
    print("Open Solo | bash=/usr/bin/open param1=-a param2=Solo terminal=false")


def main():
    settings = load_settings()
    show_all = bool(settings.get("show_all", False))
    show_todos = bool(settings.get("show_todos", False))
    show_pads = bool(settings.get("show_scratchpads", False))
    # How SwiftBar must re-invoke this script for click actions (toggles and
    # the per-process Stop button). Computed once and shared by both.
    py, script = sys.executable, os.path.abspath(__file__)

    # Build every project row before printing anything: stdout IS the menu, so
    # a failure mid-print would leave a truncated menu with no toggles. Any
    # failure here — Solo down, auth, a pagination stall, an API shape change —
    # lands on an error row instead.
    try:
        api_base, token = api_config()
        # Projects come flat (no nested process list), so pair them with
        # /processes and join on projectId. The "active only" view needs just
        # the running processes; "all projects" also needs idle ones for their
        # deep links. One endpoint covers every kind Solo tracks — commands,
        # terminals, and agents alike — so nothing extra to fetch per kind.
        projects = get_all(api_base, token, "/projects", "projects")
        path = "/processes" if show_all else "/processes?status=running"
        processes = get_all(api_base, token, path, "processes")
        rows = project_rows(api_base, token, projects, processes,
                            show_all, show_todos, show_pads, py, script)
    except ApiChanged:
        error_menu("Solo API changed — update this plugin")
        print("Plugin releases | href=https://github.com/slaFFik/solo-menubar/releases")
        return
    except Exception:
        error_menu(failure_message())
        return

    # Menu bar title: Solo logo only.
    print(f" | {icon_param()}")
    print("---")
    for row in rows:
        print(row)

    print("---")

    def toggle(label, key, on):
        # Quote bash/param values: SwiftBar splits unquoted params on spaces,
        # which silently breaks paths like .../Application Support/... .
        return (f'{label} | checked={"true" if on else "false"} bash="{py}" '
                f'param1="{script}" param2=--toggle-{key.replace("_", "-")} '
                f"terminal=false refresh=true")

    print(toggle(f"Show all projects ({len(projects)})", "show_all", show_all))
    print(toggle("Show TODOs", "show_todos", show_todos))
    print(toggle("Show Scratchpads", "show_scratchpads", show_pads))
    print("Open Solo | bash=/usr/bin/open param1=-a param2=Solo terminal=false")
    print("Refresh | refresh=true")


if __name__ == "__main__":
    KEYS = {"show_all", "show_todos", "show_scratchpads"}
    args = sys.argv[1:]
    toggled = next((a[len("--toggle-"):].replace("-", "_")
                    for a in args if a.startswith("--toggle-")), None)
    if "--stop-process" in args:
        i = args.index("--stop-process")
        stop_process(args[i + 1] if i + 1 < len(args) else "")
    elif toggled in KEYS:
        toggle_setting(toggled)
    else:
        main()

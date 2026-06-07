#!/usr/bin/env python3
# <xbar.title>Solo - Active Projects</xbar.title>
# <xbar.version>1.0</xbar.version>
# <xbar.author>Slava Abakumov</xbar.author>
# <xbar.author.github>slaFFik</xbar.author.github>
# <xbar.desc>Shows Solo projects that currently have a running process.</xbar.desc>
# <xbar.abouturl>https://github.com/slaFFik/solo-menubar</xbar.abouturl>
# <xbar.image></xbar.image>
# <xbar.dependencies>python3,Solo</xbar.dependencies>
#
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
#
# Reads Solo's local HTTP control plane (no auth token needed for the bare
# read-only endpoints) and lists every project with at least one running
# process. Solo must be running with the HTTP API enabled.
#
# Drop this file in your SwiftBar plugin folder. The "5s" in the filename
# sets the refresh interval (every 5 seconds).

import base64
import json
import os
import urllib.request
from collections import defaultdict

DISCOVERY = os.path.expanduser("~/.config/soloterm/http-api.json")
DEFAULT_ORIGIN = "http://127.0.0.1:24678"

# Menu bar icon: base64-encoded PNG embedded directly so SwiftBar does not
# treat a sidecar image file as its own (broken) plugin. To change the icon,
# regenerate ICON_B64 from a PNG, e.g.:
#   python3 -c "import base64;print(base64.b64encode(open('icon.png','rb').read()).decode())"
ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAAAXNSR0IArs4c6QAAAHhlWElmTU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAACQAAAAAQAAAJAAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAACSgAwAEAAAAAQAAACQAAAAA+INbXQAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAA3FJREFUWAntWE1oE0EUfrO7SZo2tUmbWtSikP4lFIvY4slLFapnvYhIC97Eg0KxIHi0B0UEEb2K9VLw4kUL9SCKtiAeq9TaUpRKwSbpr7ZJdnd8b3SbNNnupDEpFfpgdt+8N/O9b+d/h0GGtKAopnEFTV2Y6jF5MtzFVBMINoNp2FTUe59RLHBmKZGmpj4A3o95zbJt01tnwK9/+jJ1h+Kp9PhL5haqCuW3WTAm6woGq5ejsfgoC4dDzcxQPiKJ7W6Z7O/WVWBtCpK5apEpi7SJQsm6ELA9IaEb3hCYag1wxYfvumwQaZ7q/KlbA4RFQtgUg8SKiapmcH4Zm0sMYPJBxZEO8V6rDwP4I0LXy8NgaHsFqO46IGxbeVAdIkQYhCUEsUUMzFgxhZ1BFxGi2bRT5CARKtXULuQjPURoR8kuIVl37LbQbgvJWkDm/9/HkFv2gbl+5sq1OVi2tMPr7kbQ3Q3AzBUHyLSLK5WYYaClvqaNEm1LhOi4lPQek0BudLtX3280SHJ5jyHDtQ9UfRrhuAQy081FHcO1P9PoqOfdQkt1/aAmJrADdEfAbOdq1VnQPc1QNdub7bLN50GIAeMcTDqgeY/aguRjJIx8REooVdkOnoU34FkeAo6HrEJE0X/gcfA7JCrPgCf2whFCSsjwHYZYxwgw45cjkJPTQGcsdB60n+NOxYRvc0KM/pAwmavAcS3hWpUUTFoAsQSmwLbvws0JKRqwlm4ojz6BNXMJcQpYFDMZ8iR448+AhXsAEgvoSWZ61/XNCWER1n5DnG+Ld8Y9JQLz0WvrBLIV23XI9JQDLE4C59T7xRWBidhmWYUtsG0LxU9exOZ5DNp0PyjuGtuKhRrNZBT0SCvET/SA/93THBgiRD/+G3rF8AVg9sLNnMLFNGiLc3ZwCSI0g6mBvKq/GpiqQnDoIURPX8KZ9Y8DmUBthOlJjPEAA6oiZkaRb0RoGNMlMhrzMTh0fwCCH0agaewRmUomrDEAFecGYPn1y3QMDsPWZcMYWl2A64PveCe4qmvThUqopeJzsPL2Fe7XYk1KgWG2ivshvI7BechvlzC2FJoz6B2fmLwr7oei8fhIMBhYwW20E2sKmxSheAVSSKaPyBDkevBobH601u8fxG5TcMcIoM+HicZYKYRm9jQerQbBNLvHJ6eeW0F+A/ke69L4jOXQAAAAAElFTkSuQmCC"


def icon_param():
    return "image=" + ICON_B64


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


def deeplink(project_id, process_id, name):
    """Solo deep link to a specific process. The slug before '--' is cosmetic;
    Solo resolves the target by the trailing numeric process id."""
    slug = "".join(c if c.isalnum() else "-" for c in name.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-") or "x"
    return f"solo://proj/{project_id}/process/{slug}--{process_id}"


def main():
    try:
        # No-auth, snake_case endpoint: [{id,name,command,status,project_id,project_name}]
        procs = get("/processes")
    except Exception:
        print(f" | {icon_param()}")
        print("---")
        print("Solo not running or HTTP API off | color=#999999")
        print("Open Solo | bash=/usr/bin/open param1=-a param2=Solo terminal=false")
        return

    groups = defaultdict(list)
    for p in procs:
        groups[(p["project_id"], p["project_name"])].append(p)

    # Active project == has at least one process with status "running".
    active = {
        k: v for k, v in groups.items()
        if any(x.get("status") == "running" for x in v)
    }

    # Menu bar title: Solo logo only.
    print(f" | {icon_param()}")
    print("---")

    if not active:
        print("No active projects | color=#999999")
    else:
        for (proj_id, name), plist in sorted(active.items(), key=lambda kv: kv[0][1].lower()):
            running = [x for x in plist if x.get("status") == "running"]
            # Project header opens Solo at the project's first running process.
            head = running[0]
            print(f"{name} | href={deeplink(proj_id, head['id'], head['name'])} "
                  f"sfimage=circle.fill sfcolor=#34c759")
            # Each agent row deep-links to its own process.
            for x in running:
                print(f"--{x['name']} | href={deeplink(proj_id, x['id'], x['name'])}")

    print("---")
    print("Open Solo | bash=/usr/bin/open param1=-a param2=Solo terminal=false")
    print("Refresh | refresh=true")


if __name__ == "__main__":
    main()

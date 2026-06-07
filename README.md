# Solo Menubar

A tiny macOS menu bar widget that shows which of your [Solo](https://soloterm.com) projects have a **running agent or process** — and lets you jump straight into any of them with a single click.

Built as a [SwiftBar](https://github.com/swiftbar/SwiftBar) (or [xbar](https://github.com/matryer/xbar)) plugin. Pure Python, no third‑party dependencies, no API token.

```
 ◆  ← Solo logo in the menu bar
 ─────────────────────────────
 ● lgtm                        → opens Solo at this project
     └ Terminal                → opens that exact terminal
 ● solo-counselors
     └ Claude
 ● wp-pdf-plugin
     └ Claude
     └ codex-pr676-review
 ─────────────────────────────
 Open Solo
 Refresh
```

## What it does

- Puts the Solo logo in your menu bar.
- Click it to see every project that currently has at least one **running** process (i.e. an "active" project).
- Each project — and each individual agent/terminal under it — is a clickable **deep link** that opens Solo focused on that exact process.
- Refreshes automatically every 5 seconds.
- Shows a friendly *"Solo not running"* state when Solo is closed or its HTTP API is off.

## Requirements

- macOS
- [SwiftBar](https://github.com/swiftbar/SwiftBar) — `brew install swiftbar` (xbar works too)
- Python 3 (`python3` on your `PATH`; only the standard library is used)
- [Solo](https://soloterm.com) running with its **HTTP API enabled**

### Enable Solo's HTTP API

The plugin reads Solo's local control plane. Enable the HTTP API in Solo's settings — Solo then writes a discovery file to `~/.config/soloterm/http-api.json`. The plugin only uses the **read‑only, unauthenticated** endpoints, so it never needs your API token.

## Installation

```bash
# 1. Clone
git clone https://github.com/slaFFik/solo-menubar.git ~/Projects/solo-menubar

# 2. Make sure it's executable
chmod +x ~/Projects/solo-menubar/solo.5s.py

# 3. Symlink it into your SwiftBar plugin folder
ln -s ~/Projects/solo-menubar/solo.5s.py ~/Documents/SwiftBar/solo.5s.py
```

Point SwiftBar at your plugin folder (e.g. `~/Documents/SwiftBar`) and the icon appears right away. SwiftBar follows the symlink, so you can keep editing the file in the repo and SwiftBar always runs the latest version.

## How it works

Every 5 seconds the plugin:

1. Reads `origin` from `~/.config/soloterm/http-api.json` (falls back to `http://127.0.0.1:24678`), so it survives Solo restarting on a different port.
2. Calls `GET /processes` — Solo's no‑auth local endpoint.
3. Groups processes by project and keeps any project that has a process whose `status` is `running`.
4. Renders a clickable deep link per project/process:
   `solo://proj/{project_id}/process/{slug}--{process_id}`

The deep‑link *slug* is cosmetic — Solo resolves the target by the trailing process id — and that id is Solo's stable database id, so links keep working even after a process restarts.

## Configuration

**Refresh interval** — encoded in the filename. Rename the file to change it:

| Filename | Interval |
| --- | --- |
| `solo.2s.py` | 2 seconds |
| `solo.5s.py` | 5 seconds *(default)* |
| `solo.10s.py` | 10 seconds |
| `solo.1m.py` | 1 minute |

**Menu bar icon** — the icon is a base64‑encoded PNG embedded in the script (`ICON_B64`) so SwiftBar doesn't mistake a sidecar image file for another plugin. To swap it, regenerate the constant from any PNG:

```bash
python3 -c "import base64;print(base64.b64encode(open('icon.png','rb').read()).decode())"
```

> **Tip:** bake a Retina‑friendly resolution into the PNG so it fits the menu bar. `sips -s dpiWidth 144 -s dpiHeight 144 icon.png` makes a 36px image render at 18pt — the macOS menu‑bar sweet spot.

## Troubleshooting

- **"Solo not running or HTTP API off"** — start Solo and enable its HTTP API in settings.
- **Nothing shows in the menu bar** — confirm SwiftBar's plugin folder is set, the file is executable (`chmod +x`), and `python3` is installed (`xcode-select --install`).
- **Menu doesn't update while it's open** — macOS renders a menu at the moment you open it; close and reopen to see fresh data. The data itself keeps refreshing in the background.

## Credits

- [Solo](https://soloterm.com) by Aaron Francis.
- Plugin by [Slava Abakumov](https://github.com/slaFFik).

## License

[MIT](LICENSE)

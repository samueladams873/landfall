"""Build the readiness report as a single, self-contained HTML file."""
from __future__ import annotations

from datetime import datetime
from html import escape

from landfall import __version__
from landfall.mapping import GROUP_ALT, GROUP_NONE, GROUP_SAME, GROUPS, MatchResult
from landfall.scan.hardware import hardware_notes

_GROUP_HELP = {
    GROUP_SAME: "The same app is available on Linux.",
    GROUP_ALT: "A different free app does the same job on Linux.",
    GROUP_NONE: "Only runs through Wine, or Landfall doesn't know this app yet.",
}

_CSS = """
body{font-family:system-ui,Segoe UI,Ubuntu,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1d2330}
h1{margin-bottom:.2rem} .muted{color:#667} h2{margin-top:2rem;border-bottom:2px solid #dde}
table{border-collapse:collapse;width:100%} td,th{text-align:left;padding:.4rem .5rem;border-bottom:1px solid #eef;vertical-align:top}
.new{background:#fff1c2;border-radius:4px;padding:0 .3rem;font-size:.85em}
.notes li{margin:.3rem 0}
"""


def option_text(option: dict) -> str:
    text = option["name"]
    if option.get("new"):
        text += " (new, Oct 2026)"
    return text


def _option_html(option: dict) -> str:
    name = escape(option["name"])
    link = option.get("url") or (f"https://flathub.org/apps/{option['flatpak']}"
                                 if option.get("flatpak") else "")
    out = f'<a href="{escape(link)}">{name}</a>' if link else name
    if option.get("new"):
        out += ' <span class="new">new, Oct 2026</span>'
    return out


def _hw_rows(hw: dict) -> str:
    rows = [
        ("Windows", hw.get("windows")), ("Computer", hw.get("model")),
        ("Processor", ", ".join(hw.get("cpu", [])) or "Unknown"),
        ("Memory", f"{hw.get('ram_gb', 0)} GB"),
        ("Graphics", ", ".join(hw.get("gpu", [])) or "Unknown"),
        ("Wi-Fi", ", ".join(hw.get("wifi", [])) or "None found"),
        ("Ethernet", ", ".join(hw.get("ethernet", [])) or "None found"),
        ("Bluetooth", ", ".join(hw.get("bluetooth", [])) or "None found"),
        ("Webcam", ", ".join(hw.get("webcam", [])) or "None found"),
        ("Printers", ", ".join(hw.get("printers", [])) or "None found"),
        ("Disks", ", ".join(hw.get("disks", [])) or "Unknown"),
        ("Boot mode", hw.get("boot_mode")), ("Secure Boot", hw.get("secure_boot")),
    ]
    return "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)


def build_html(grouped: dict[str, list[MatchResult]], hw: dict) -> str:
    total = sum(len(v) for v in grouped.values())
    ready = len(grouped[GROUP_SAME]) + len(grouped[GROUP_ALT])
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>Landfall readiness report</title><style>{_CSS}</style></head><body>",
        "<h1>Linux readiness report</h1>",
        f"<p class='muted'>Made by Landfall {escape(__version__)} on "
        f"{datetime.now():%B %d, %Y at %I:%M %p}. Nothing on this PC was changed.</p>",
        f"<p><b>{ready} of {total}</b> of your apps work on Linux or have a Linux alternative.</p>",
    ]
    notes = hardware_notes(hw)
    if notes:
        parts.append("<h2>Things to know</h2><ul class='notes'>")
        parts += [f"<li>{escape(n)}</li>" for n in notes]
        parts.append("</ul>")
    for group in GROUPS:
        items = grouped[group]
        parts.append(f"<h2>{escape(group)} ({len(items)})</h2>")
        parts.append(f"<p class='muted'>{escape(_GROUP_HELP[group])}</p>")
        if not items:
            parts.append("<p>None.</p>")
            continue
        parts.append("<table><tr><th>Your Windows app</th><th>On Linux</th></tr>")
        for r in items:
            linux = "<br>".join(_option_html(o) for o in r.options) or "Unknown"
            parts.append(f"<tr><td>{escape(r.app['name'])}</td><td>{linux}</td></tr>")
        parts.append("</table>")
    parts.append(f"<h2>Your hardware</h2><table>{_hw_rows(hw)}</table>")
    parts.append("<p class='muted'>Landfall is free and open source: "
                 "<a href='https://github.com/samueladams873/landfall'>github.com/samueladams873/landfall</a></p>")
    parts.append("</body></html>")
    return "\n".join(parts)

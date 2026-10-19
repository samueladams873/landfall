"""Match installed Windows apps against the Windows -> Linux app map."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "app_map.json"

# Groups shown in the report, in display order.
GROUP_SAME = "Works on Linux"
GROUP_ALT = "Has a Linux alternative"
GROUP_NONE = "Needs Wine or no match yet"
GROUPS = (GROUP_SAME, GROUP_ALT, GROUP_NONE)

_STATUS_TO_GROUP = {"same": GROUP_SAME, "alternative": GROUP_ALT, "wine": GROUP_NONE,
                    "none": GROUP_NONE}


@dataclass
class MatchResult:
    app: dict                      # the installed app (name, version, publisher)
    group: str
    entry: dict | None = None      # the app_map entry, or None if unknown
    options: list = field(default_factory=list)


def load_map(path: Path = DATA_FILE) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data["apps"]
    for entry in entries:
        entry["_compiled"] = [re.compile(p, re.IGNORECASE) for p in entry["patterns"]]
    return entries


def builtin_apps(entries: list[dict] | None = None) -> list[dict]:
    """Programs that come with every copy of Windows (Notepad, Paint, Photos...). They never
    show up as installed programs, so they're always added to what the scan found."""
    entries = entries if entries is not None else load_map()
    return [{"name": e["windows"], "icon": e.get("exe", ""), "source": "Built into Windows",
             "builtin": True} for e in entries if e.get("builtin")]


def match_app(app: dict, entries: list[dict]) -> MatchResult:
    name = app.get("name", "").strip()
    for entry in entries:
        if any(rx.search(name) for rx in entry["_compiled"]):
            return MatchResult(app, _STATUS_TO_GROUP[entry["status"]], entry, entry["linux"])
    return MatchResult(app, GROUP_NONE)


def match_all(apps: list[dict], entries: list[dict] | None = None) -> dict[str, list[MatchResult]]:
    entries = entries if entries is not None else load_map()
    grouped: dict[str, list[MatchResult]] = {g: [] for g in GROUPS}
    for app in sorted(apps, key=lambda a: a.get("name", "").lower()):
        result = match_app(app, entries)
        grouped[result.group].append(result)
    return grouped


@dataclass
class Category:
    """One job, like "Web browser": the Windows apps doing it, and the Linux options."""
    name: str
    windows_apps: list = field(default_factory=list)
    options: list = field(default_factory=list)
    recommended: set = field(default_factory=set)   # option keys picked to start with


def option_key(opt: dict) -> str:
    return opt.get("flatpak") or opt.get("url") or opt["name"]


def by_category(grouped: dict[str, list[MatchResult]]) -> tuple[list[Category], list[dict]]:
    """Merge apps doing the same job, so e.g. Chrome + Edge + Firefox become ONE browser
    choice and no Linux app is ever offered twice. Returns (categories, apps_with_no_match)."""
    cats: dict[str, Category] = {}
    unmatched = []
    for results in grouped.values():
        for r in results:
            if not r.entry or not r.options:
                unmatched.append(r.app)
                continue
            cat = cats.setdefault(r.entry.get("category", r.entry["windows"]),
                                  Category(r.entry.get("category", r.entry["windows"])))
            cat.windows_apps.append(r.app)
            keys = {option_key(o): n for n, o in enumerate(cat.options)}
            for i, opt in enumerate(r.options):
                k = option_key(opt)
                if k not in keys:
                    keys[k] = len(cat.options)
                    cat.options.append(opt)
                elif i == 0 and r.entry.get("status") == "same":
                    # the same app the user already has: its own wording ("your data comes
                    # over as it is") beats a generic description from another app
                    cat.options[keys[k]] = opt
            cat.recommended.add(option_key(r.options[0]))
    for cat in cats.values():  # recommended picks first, then the rest in map order
        cat.options.sort(key=lambda o: option_key(o) not in cat.recommended)
    return sorted(cats.values(), key=lambda c: c.name), unmatched

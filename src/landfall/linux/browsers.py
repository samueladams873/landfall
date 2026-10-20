"""Put the bookmarks, history and passwords from Windows into the browser the user picked.

What can be done automatically, and how:
* Firefox -> Firefox: places.sqlite (bookmarks + history), logins.json + key4.db (passwords)
  are copied into the new profile. They are not tied to Windows, so they work as they are.
* any -> Firefox: a bookmarks.html is placed in the profile and Firefox told (prefs.js,
  browser.places.importBookmarksHTML) to load it on its next start.
* any -> Chromium/Chrome/Brave/Vivaldi: bookmarks are written into the profile's Bookmarks
  file (merged into an "Imported from ..." folder if the browser already has some).
* Chromium-family passwords arrive as the CSV the user exported on Windows. Browsers only
  import those through their own Import button, so Landfall opens that page for the user.
"""
from __future__ import annotations

import html
import json
import shutil
import sqlite3
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from landfall.sysenv import run, system_env

# Where each Linux browser keeps its profile, by how it was installed.
# Firefox 147+ puts new Linux profiles in the XDG config folder; older ones use ~/.mozilla.
FIREFOX_ROOTS = {
    "flatpak": [".var/app/org.mozilla.firefox/.mozilla/firefox",
                ".var/app/org.mozilla.firefox/config/mozilla/firefox"],
    "snap": ["snap/firefox/common/.mozilla/firefox",
             "snap/firefox/common/.config/mozilla/firefox"],
    "deb": [".mozilla/firefox", ".config/mozilla/firefox"],
}
CHROMIUM_TARGETS = {
    # browser: [(how, launch command, profile dir relative to home)]
    "chromium": [("flatpak", ["flatpak", "run", "org.chromium.Chromium"],
                  ".var/app/org.chromium.Chromium/config/chromium"),
                 ("snap", ["snap", "run", "chromium"], "snap/chromium/common/chromium"),
                 ("deb", ["chromium"], ".config/chromium")],
    "chrome": [("flatpak", ["flatpak", "run", "com.google.Chrome"],
                ".var/app/com.google.Chrome/config/google-chrome"),
               ("deb", ["google-chrome"], ".config/google-chrome")],
    "brave": [("flatpak", ["flatpak", "run", "com.brave.Browser"],
               ".var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser"),
              ("snap", ["snap", "run", "brave"], "snap/brave/current/.config/BraveSoftware/Brave-Browser"),
              ("deb", ["brave-browser"], ".config/BraveSoftware/Brave-Browser")],
    "vivaldi": [("flatpak", ["flatpak", "run", "com.vivaldi.Vivaldi"],
                 ".var/app/com.vivaldi.Vivaldi/config/vivaldi"),
                ("deb", ["vivaldi"], ".config/vivaldi")],
}
FLATPAK_TO_BROWSER = {"org.mozilla.firefox": "firefox", "org.chromium.Chromium": "chromium",
                      "com.google.Chrome": "chrome", "com.brave.Browser": "brave",
                      "com.vivaldi.Vivaldi": "vivaldi"}
# Firefox shows an easy Import button on about:logins; Chrome-family on their password page.
IMPORT_PAGES = {"firefox": "about:logins", "chromium": "chrome://password-manager/settings",
                "chrome": "chrome://password-manager/settings",
                "brave": "brave://password-manager/settings", "vivaldi": "vivaldi://settings/passwords"}


@dataclass
class Target:
    browser: str                 # firefox / chromium / chrome / brave / vivaldi
    how: str                     # flatpak / snap / deb
    launch: list                 # command that starts it
    profile_root: Path           # firefox: dir with profiles.ini; chromium: "User Data" dir
    other_roots: list = field(default_factory=list)   # other places that browser may use

    @property
    def name(self) -> str:
        return {"firefox": "Firefox", "chromium": "Chromium", "chrome": "Google Chrome",
                "brave": "Brave", "vivaldi": "Vivaldi"}[self.browser]


@dataclass
class BrowserResult:
    source: str                  # "Microsoft Edge"
    target: str                  # "Firefox"
    bookmarks: int = 0
    history: bool = False
    passwords: str = ""          # "copied" / "file" / ""
    password_file: Path | None = None
    import_command: list = field(default_factory=list)
    import_url: str = ""         # the address to paste if the page opens wrong
    problem: str = ""


# --- finding the browser on Linux ------------------------------------------------------------
def _have(cmd: str) -> bool:
    return shutil.which(cmd, path=system_env().get("PATH")) is not None


def find_target(browser: str, home: Path, flatpaks: set, snaps: set) -> Target | None:
    if browser == "firefox":
        options = [("flatpak", ["flatpak", "run", "org.mozilla.firefox"], "org.mozilla.firefox" in flatpaks),
                   ("snap", ["snap", "run", "firefox"], "firefox" in snaps),
                   ("deb", ["firefox"], _have("firefox") and "firefox" not in snaps)]
        for how, cmd, present in options:
            if present:
                roots = [home / r for r in FIREFOX_ROOTS[how]]
                return Target("firefox", how, cmd, roots[0], roots[1:])
        return None
    for how, cmd, rel in CHROMIUM_TARGETS.get(browser, []):
        present = {"flatpak": lambda: cmd[2] in flatpaks,
                   "snap": lambda: cmd[2] in snaps,
                   "deb": lambda: _have(cmd[0])}[how]()
        if present:
            return Target(browser, how, cmd, home / rel)
    return None


def choose_targets(picked_flatpaks: list[str], home: Path, flatpaks: set, snaps: set) -> list:
    """The browsers the user picked on Windows, in their order; Firefox if nothing was picked
    but it's on the PC (it comes with Ubuntu)."""
    wanted = [FLATPAK_TO_BROWSER[f] for f in picked_flatpaks if f in FLATPAK_TO_BROWSER]
    targets = [t for b in dict.fromkeys(wanted) if (t := find_target(b, home, flatpaks, snaps))]
    if not targets:
        fallback = find_target("firefox", home, flatpaks, snaps)
        targets = [fallback] if fallback else []
    return targets


def match_target(source_family: str, source_browser: str, targets: list) -> Target | None:
    """Same browser first, then same family (Edge -> Chromium), then the first pick."""
    for t in targets:
        if t.browser == source_browser:
            return t
    family = [t for t in targets if (t.browser == "firefox") == (source_family == "firefox")]
    return (family or targets or [None])[0]


# --- making sure a profile exists ------------------------------------------------------------
def _start_once(target: Target, extra_args: list, seconds: int = 12) -> None:
    """Start the browser hidden for a few seconds so it creates its own profile, then close it."""
    try:
        proc = subprocess.Popen(target.launch + extra_args, env=system_env(),
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return
    deadline = time.time() + seconds
    while time.time() < deadline and proc.poll() is None:
        time.sleep(0.5)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
    time.sleep(1)


def _firefox_default(root: Path) -> Path | None:
    import configparser
    for name in ("installs.ini", "profiles.ini"):
        cfg = configparser.ConfigParser(interpolation=None)
        try:
            cfg.read(root / name, encoding="utf-8")
        except configparser.Error:
            continue
        for section in cfg.sections():
            if name == "installs.ini":
                rel = cfg.get(section, "Default", fallback="")
            elif cfg.get(section, "Default", fallback="") == "1":
                rel = cfg.get(section, "Path", fallback="")
            else:
                continue
            if rel and (root / rel).is_dir():
                return root / rel
    found = sorted(root.glob("*.default-release"))
    return found[0] if found else None


def firefox_profile(target: Target) -> Path | None:
    """The profile Firefox will open, creating it (by starting Firefox hidden) if needed."""
    roots = [target.profile_root] + list(target.other_roots)

    def find():
        for root in roots:
            prof = _firefox_default(root)
            if prof:
                return prof
        return None

    prof = find()
    if prof is None:
        _start_once(target, ["--headless", "--no-remote", "about:blank"])
        prof = find()
    return prof


def chromium_profile(target: Target) -> Path:
    prof = target.profile_root / "Default"
    if not prof.exists():
        _start_once(target, ["--headless=new", "--no-first-run", "about:blank"])
    prof.mkdir(parents=True, exist_ok=True)
    return prof


# --- bookmarks, in a neutral form: [{"title", "url"} or {"title", "children": [...]}] ---------
def read_chromium_bookmarks(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))

    def conv(node):
        if node.get("type") == "url":
            return {"title": node.get("name", ""), "url": node.get("url", "")}
        return {"title": node.get("name", ""), "children": [conv(c) for c in node.get("children", [])]}

    roots = data.get("roots", {})
    out = []
    for key, title in (("bookmark_bar", "Bookmarks bar"), ("other", "Other bookmarks"),
                       ("synced", "Mobile bookmarks")):
        if isinstance(roots.get(key), dict) and roots[key].get("children"):
            out.append({"title": title, "children": [conv(c) for c in roots[key]["children"]]})
    return out


def read_firefox_bookmarks(places: Path) -> list:
    con = sqlite3.connect(f"file:{places}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT b.id, b.parent, b.type, b.title, p.url, b.guid "
                           "FROM moz_bookmarks b LEFT JOIN moz_places p ON b.fk = p.id "
                           "ORDER BY b.parent, b.position").fetchall()
    finally:
        con.close()
    kids: dict = {}
    for row in rows:
        kids.setdefault(row[1], []).append(row)

    def build(bid):
        out = []
        for _id, _parent, typ, title, url, _pos in kids.get(bid, []):
            if typ == 1 and url and not url.startswith("place:"):
                out.append({"title": title or url, "url": url})
            elif typ == 2:
                out.append({"title": title or "Folder", "children": build(_id)})
        return out

    names = {"toolbar_____": "Bookmarks bar", "menu________": "Bookmarks menu",
             "unfiled_____": "Other bookmarks", "mobile______": "Mobile bookmarks"}
    tops = []
    for _id, _parent, _typ, _title, _url, guid in kids.get(1, []):     # root's children
        if guid not in names:                                           # skips the tags folder
            continue
        children = build(_id)
        if children:
            tops.append({"title": names[guid], "children": children})
    return tops


def count_links(tree: list) -> int:
    return sum(1 if "url" in n else count_links(n.get("children", [])) for n in tree)


def to_bookmarks_html(tree: list, title: str) -> str:
    """Netscape bookmarks file. The old browser's bookmarks *bar* becomes Firefox's toolbar
    (PERSONAL_TOOLBAR_FOLDER), so it shows along the top like it did on Windows; everything
    else goes into an "Imported from ..." folder in the Bookmarks menu."""
    def emit(nodes, depth):
        pad = "    " * depth
        lines = []
        for n in nodes:
            if "url" in n:
                lines.append(f'{pad}<DT><A HREF="{html.escape(n["url"], True)}">'
                             f'{html.escape(n["title"])}</A>')
            else:
                lines.append(f"{pad}<DT><H3>{html.escape(n['title'])}</H3>")
                lines.append(f"{pad}<DL><p>")
                lines += emit(n.get("children", []), depth + 1)
                lines.append(f"{pad}</DL><p>")
        return lines

    bar = [n for n in tree if n.get("title") == "Bookmarks bar" and "children" in n]
    rest = [n for n in tree if n not in bar]
    body = []
    if bar:
        body.append('    <DT><H3 PERSONAL_TOOLBAR_FOLDER="true">Bookmarks Toolbar</H3>')
        body.append("    <DL><p>")
        body += emit(bar[0]["children"], 2)
        body.append("    </DL><p>")
    if rest:
        body += emit([{"title": title, "children": rest}], 1)
    return ("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n"
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n'
            "<TITLE>Bookmarks</TITLE>\n<H1>Bookmarks</H1>\n<DL><p>\n" + "\n".join(body)
            + "\n</DL><p>\n")


def _chromium_node(n, counter):
    counter[0] += 1
    base = {"date_added": "13300000000000000", "guid": str(uuid.uuid4()), "id": str(counter[0]),
            "name": n["title"]}
    if "url" in n:
        return {**base, "type": "url", "url": n["url"]}
    return {**base, "type": "folder", "date_modified": "0",
            "children": [_chromium_node(c, counter) for c in n.get("children", [])]}


def write_chromium_bookmarks(prof: Path, tree: list, folder_title: str) -> None:
    """Add an "Imported from ..." folder to the bookmarks bar (keeps existing bookmarks)."""
    path = prof / "Bookmarks"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"roots": {k: {"children": [], "date_added": "13300000000000000",
                              "date_modified": "0", "guid": str(uuid.uuid4()), "id": str(i),
                              "name": n, "type": "folder"}
                          for i, (k, n) in enumerate((("bookmark_bar", "Bookmarks bar"),
                                                      ("other", "Other bookmarks"),
                                                      ("synced", "Mobile bookmarks")), 1)},
                "version": 1}
    data.pop("checksum", None)          # the browser rebuilds it; a stale one gets rejected

    def max_id(node):
        ids = [int(node.get("id", 0))] if str(node.get("id", "0")).isdigit() else [0]
        return max(ids + [max_id(c) for c in node.get("children", [])])

    counter = [max(max_id(r) for r in data["roots"].values() if isinstance(r, dict)) + 1]
    bar = data["roots"]["bookmark_bar"]
    bar.setdefault("children", []).append(
        _chromium_node({"title": folder_title, "children": tree}, counter))
    path.write_text(json.dumps(data, indent=3), encoding="utf-8")


# --- the import -------------------------------------------------------------------------------
def import_browser(rec: dict, src: Path, target: Target, home: Path) -> BrowserResult:
    """rec: the manifest entry; src: unpacked landfall/browsers/<key>/ folder."""
    res = BrowserResult(rec["name"], target.name)
    try:
        if rec["family"] == "firefox":
            tree = read_firefox_bookmarks(src / "places.sqlite") if (src / "places.sqlite").exists() else []
        else:
            tree = read_chromium_bookmarks(src / "Bookmarks") if (src / "Bookmarks").exists() else []
    except (OSError, ValueError, sqlite3.Error) as err:
        res.problem = f"Couldn't read the bookmarks ({err})."
        tree = []
    res.bookmarks = count_links(tree)

    if target.browser == "firefox":
        prof = firefox_profile(target)
        if prof is None:
            res.problem = "Couldn't set up a Firefox profile."
            return res
        for _ in range(60):                       # never write while Firefox is open
            if not (prof / "lock").is_symlink():
                break
            time.sleep(1)
        else:
            res.problem = "Firefox stayed open, so its bookmarks weren't changed. Close it and try again."
            return res
        if rec["family"] == "firefox":
            # the same browser: bring everything over exactly as it was
            for name in ("places.sqlite", "favicons.sqlite", "logins.json", "key4.db"):
                if (src / name).exists():
                    for stale in (name + "-wal", name + "-shm"):
                        (prof / stale).unlink(missing_ok=True)
                    shutil.copy2(src / name, prof / name)
            res.history = (src / "places.sqlite").exists()
            if (src / "logins.json").exists() and (src / "key4.db").exists():
                res.passwords = "copied"
        elif tree:
            (prof / "bookmarks.html").write_text(
                to_bookmarks_html(tree, f"Imported from {rec['name']}"), encoding="utf-8")
            with open(prof / "prefs.js", "a", encoding="utf-8") as f:
                f.write('\nuser_pref("browser.places.importBookmarksHTML", true);\n')
                if any(n.get("title") == "Bookmarks bar" for n in tree):
                    # their favorites bar was always showing on Windows; keep it that way
                    f.write('user_pref("browser.toolbars.bookmarks.visibility", "always");\n')
    else:
        prof = chromium_profile(target)
        if rec["family"] == "chromium" and not (prof / "History").exists() and (src / "History").exists():
            shutil.copy2(src / "History", prof / "History")
            res.history = True
        if tree:
            write_chromium_bookmarks(prof, tree, f"Imported from {rec['name']}")

    csv = src / "passwords.csv"
    if csv.exists() and res.passwords != "copied":
        keep = home / ".local/share/landfall" / f"{rec['key']}-passwords.csv"
        keep.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(csv, keep)
        keep.chmod(0o600)
        res.passwords, res.password_file = "file", keep
        res.import_url = IMPORT_PAGES[target.browser]
        res.import_command = (target.launch + _new_window_flag(target) + [res.import_url])
    return res


def _new_window_flag(target) -> list:
    # --new-window forces the page even when the browser is already open; Firefox opens
    # about:logins correctly without it.
    return [] if target.browser == "firefox" else ["--new-window"]


def open_import_page(res: BrowserResult) -> None:
    if res.import_command:
        subprocess.Popen(res.import_command, env=system_env(), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)

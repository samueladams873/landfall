import re

from landfall.mapping import GROUP_ALT, GROUP_NONE, GROUP_SAME, load_map, match_all
from landfall.report import build_html
from landfall.scan.apps import clean
from landfall.scan.hardware import hardware_notes

FAKE_APPS = [
    {"name": "Google Chrome", "version": "130", "publisher": "Google LLC"},
    {"name": "Adobe Photoshop 2025", "version": "26", "publisher": "Adobe"},
    {"name": "Battle.net", "version": "", "publisher": "Blizzard"},
    {"name": "Some Obscure Tool", "version": "1", "publisher": "Nobody"},
]

FAKE_HW = {"windows": "Windows 10", "model": "Dell OptiPlex", "cpu": ["Intel i7"],
           "ram_gb": 8, "gpu": ["NVIDIA GeForce GTX 1050"], "wifi": [], "ethernet": [],
           "bluetooth": [], "webcam": [], "printers": [], "disks": [],
           "boot_mode": "UEFI", "secure_boot": "On"}


def test_map_is_valid():
    entries = load_map()
    assert len(entries) >= 30
    for e in entries:
        assert e["status"] in {"same", "alternative", "wine", "none"}
        assert e["category"], e["windows"]
        assert e["linux"] or e["status"] == "none", e["windows"]
        for opt in e["linux"]:
            assert opt["name"]
            if "flatpak" in opt:
                assert re.fullmatch(r"[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+){2,}", opt["flatpak"])


def test_grouping():
    grouped = match_all(FAKE_APPS)
    names = {g: [r.app["name"] for r in grouped[g]] for g in grouped}
    assert names[GROUP_SAME] == ["Google Chrome"]
    assert names[GROUP_ALT] == ["Adobe Photoshop 2025"]
    assert set(names[GROUP_NONE]) == {"Battle.net", "Some Obscure Tool"}


def test_photoshop_lists_proven_pick_first_and_new_last():
    grouped = match_all(FAKE_APPS)
    opts = grouped[GROUP_ALT][0].options
    assert opts[0]["name"] == "GIMP"
    assert any(o["name"] == "PhotoCraft" and o.get("new") for o in opts)


def test_clean_drops_noise_and_duplicates():
    raw = [
        {"name": "Google Chrome"}, {"name": "Google Chrome"},
        {"name": "Microsoft Visual C++ 2022 X64 Minimum Runtime"},
        {"name": "Security Update for Windows (KB5034441)"},
        {"name": "Hidden thing", "system_component": True},
        {"name": ""},
        {"name": "Oracle VM VirtualBox Guest Additions 7.2.16"},
        {"name": "Mozilla Maintenance Service"},
    ]
    assert [a["name"] for a in clean(raw)] == ["Google Chrome"]


def test_hardware_notes():
    notes = hardware_notes(FAKE_HW)
    assert any("NVIDIA" in n for n in notes)
    assert any("Secure Boot" in n for n in notes)


def test_report_html():
    html = build_html(match_all(FAKE_APPS), FAKE_HW)
    assert "2 of 4" in html
    assert "PhotoCraft" in html and "new, Oct 2026" in html
    assert "https://flathub.org/apps/com.google.Chrome" in html
    assert "Nothing on this PC was changed" in html


def test_never_offers_microsoft_apps_on_linux():
    """Roger's rule: nobody wants Microsoft Edge (or any Microsoft app) on Linux."""
    for e in load_map():
        for opt in e["linux"]:
            blob = " ".join(str(v) for v in opt.values()).lower()
            assert "microsoft" not in blob and "edge" not in blob, (e["windows"], opt["name"])


def test_browsers_become_one_choice_without_repeats():
    from landfall.mapping import by_category
    grouped = match_all([{"name": "Microsoft Edge"}, {"name": "Google Chrome"},
                         {"name": "Mozilla Firefox (x64 en-US)"}])
    cats, _ = by_category(grouped)
    assert [c.name for c in cats] == ["Web browser"]
    names = [o["name"] for o in cats[0].options]
    assert len(names) == len(set(names))
    assert "Firefox" in names and "Microsoft Edge" not in names


def test_builtin_windows_programs_always_get_alternatives():
    from landfall.mapping import builtin_apps, by_category
    built = builtin_apps()
    names = {a["name"] for a in built}
    assert {"Notepad", "Paint", "Snipping Tool", "Windows Media Player"} <= names
    cats, _ = by_category(match_all(built))
    by_name = {c.name: c for c in cats}
    assert by_name["Drawing"].options[0]["name"] == "Pinta"          # Paint -> Pinta first
    assert by_name["Text editor"].windows_apps[0]["name"] == "Notepad"


def test_microsoft_and_system_apps_get_linux_alternatives():
    """Roger: OneDrive, Mail, Teams, Defender and Windows' own tools all need Linux options."""
    from landfall.mapping import builtin_apps, by_category
    entries = {e["windows"]: e for e in load_map()}
    for name in ("Microsoft OneDrive", "Microsoft Teams", "Mail and Calendar", "Windows Security",
                 "OneDrive", "Disk Cleanup", "Remote Desktop Connection", "Phone Link"):
        assert entries[name]["linux"], name
    scanned = [{"name": "Microsoft OneDrive"}]
    names = [a["name"] for a in builtin_apps(scanned=scanned)]
    assert "OneDrive" not in names            # not listed twice
    cats, _ = by_category(match_all(scanned + builtin_apps(scanned=scanned)))
    cloud = {c.name: c for c in cats}["Cloud storage"]
    assert [a["name"] for a in cloud.windows_apps] == ["Microsoft OneDrive"]
    assert cloud.options[0].get("included")   # Online Accounts comes with Ubuntu


def test_builtin_dedupe_uses_whole_names():
    from landfall.mapping import builtin_apps
    names = [a["name"] for a in builtin_apps(scanned=[{"name": "Notepad++ (64-bit x64)"},
                                                      {"name": "Mailbird"},
                                                      {"name": "Microsoft Edge"}])]
    assert "Notepad" in names and "Mail and Calendar" in names
    assert "Microsoft Edge" not in names


def test_obvious_programs_every_linux_pc_has_are_not_listed():
    """Roger: no Calculator, Clock, Camera, Solitaire... Linux already has them."""
    from landfall.mapping import builtin_apps
    names = {a["name"] for a in builtin_apps()}
    for obvious in ("Calculator", "Alarms & Clock", "Camera", "Microsoft Solitaire Collection",
                    "Weather", "Maps", "File Explorer", "Task Manager", "Microsoft Store"):
        assert obvious not in names, obvious


def test_rogers_real_vm_scan():
    """The apps Roger's Windows 10 VM actually reported on Oct 19 2026."""
    from landfall.mapping import builtin_apps, by_category
    scanned = [{"name": n} for n in (
        "Mozilla Firefox (x64 en-US)", "Steam", "Adobe Acrobat (64-bit)", "iTunes",
        "McAfee Security Scan Plus", "Microsoft 365 - en-us", "Microsoft Edge",
        "Microsoft OneDrive", "\u00b5Torrent")]
    grouped = match_all(scanned + builtin_apps(scanned=scanned))
    unmatched = [r.app["name"] for r in grouped[GROUP_NONE] if not r.options]
    assert unmatched == [], unmatched
    cats = {c.name: c for c in by_category(grouped)[0]}
    games = [a["name"] for a in cats["Games"].windows_apps]
    assert games == ["Steam"]                                   # Game Bar isn't a game store
    assert "Xbox Game Bar" in [a["name"] for a in cats["Screen recording"].windows_apps]
    browsers = [a["name"] for a in cats["Web browser"].windows_apps]
    assert sorted(browsers) == ["Microsoft Edge", "Mozilla Firefox (x64 en-US)"]
    assert cats["Web browser"].options[0]["name"] == "Firefox"

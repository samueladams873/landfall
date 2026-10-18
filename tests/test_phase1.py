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
        assert e["status"] in {"same", "alternative", "wine"}
        assert e["linux"], e["windows"]
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
    assert opts[-1]["name"] == "PhotoCraft" and opts[-1]["new"]


def test_clean_drops_noise_and_duplicates():
    raw = [
        {"name": "Google Chrome"}, {"name": "Google Chrome"},
        {"name": "Microsoft Visual C++ 2022 X64 Minimum Runtime"},
        {"name": "Security Update for Windows (KB5034441)"},
        {"name": "Hidden thing", "system_component": True},
        {"name": ""},
        {"name": "Oracle VM VirtualBox Guest Additions 7.2.16"},
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

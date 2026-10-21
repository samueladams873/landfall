"""Pure-logic tests for the Linux import wizard's routing decisions:
where each folder lands, which browser inherits bookmarks/passwords, and
how chosen-size accounting works. These paths decide where the user's data
goes, so a bug here moves files or passwords to the wrong place silently."""
from pathlib import Path
from types import SimpleNamespace

from landfall.linux.importer import Importer


# --- _planned_target: which browser inherits a profile's data -------------

def test_firefox_profile_goes_to_firefox_when_firefox_picked():
    rec = {"family": "firefox"}
    assert Importer._planned_target(rec, ["Firefox", "Brave Browser"]) == "Firefox"


def test_chromium_profile_goes_to_a_picked_chromium_browser():
    rec = {"family": "chromium"}
    # Firefox must not capture a Chromium profile; first non-Firefox wins.
    assert Importer._planned_target(rec, ["Firefox", "Brave Browser"]) == "Brave Browser"
    assert Importer._planned_target(rec, ["Chromium", "Brave Browser"]) == "Chromium"


def test_chromium_profile_falls_back_to_firefox_when_only_firefox_picked():
    rec = {"family": "chromium"}
    assert Importer._planned_target(rec, ["Firefox"]) == "Firefox"


def test_firefox_profile_falls_back_to_first_pick_when_firefox_not_chosen():
    rec = {"family": "firefox"}
    # No Firefox installed -> data still has somewhere to go (first pick).
    assert Importer._planned_target(rec, ["Brave Browser"]) == "Brave Browser"


def test_nothing_picked_defaults_to_firefox():
    assert Importer._planned_target({"family": "chromium"}, []) == "Firefox"
    assert Importer._planned_target({"family": "firefox"}, []) == "Firefox"


# --- dest_for: where each folder lands on Linux ---------------------------

def _importer_with(dests, manifest):
    return SimpleNamespace(dests=dests, manifest=manifest)

def test_standard_folder_goes_to_its_linux_twin():
    home = Path("/home/tux")
    ns = _importer_with({"Documents": home / "Documents"}, {"extra_folders": []})
    assert Importer.dest_for(ns, "Documents") == home / "Documents"


def test_extra_folder_goes_under_from_windows_even_if_name_matches_a_twin():
    home = Path.home()
    # "Documents" is a known twin, but if the user added it as an extra it must
    # NOT clobber the real ~/Documents.
    ns = _importer_with({"Documents": home / "Documents"},
                        {"extra_folders": ["Documents"]})
    assert Importer.dest_for(ns, "Documents") == home / "From Windows" / "Documents"


def test_unknown_folder_goes_under_from_windows():
    ns = _importer_with({"Documents": Path.home() / "Documents"}, {"extra_folders": []})
    assert Importer.dest_for(ns, "Projects") == Path.home() / "From Windows" / "Projects"


def test_dest_for_handles_missing_manifest():
    ns = _importer_with({"Documents": Path.home() / "Documents"}, {})
    assert Importer.dest_for(ns, "Documents") == Path.home() / "Documents"


# --- chosen_bytes: size accounting for the chosen folders -----------------

def test_chosen_bytes_sums_only_files_under_chosen_folders():
    manifest = {"files": [
        {"path": "Documents/letter.txt", "size": 100},
        {"path": "Documents/Taxes/2025.pdf", "size": 5000},
        {"path": "Pictures/dog.jpg", "size": 20000},
    ]}
    ns = SimpleNamespace(manifest=manifest, chosen_folders=lambda: ["Documents"])
    assert Importer.chosen_bytes(ns) == 5100  # Pictures excluded

    ns.chosen_folders = lambda: ["Documents", "Pictures"]
    assert Importer.chosen_bytes(ns) == 25100

    ns.chosen_folders = lambda: []
    assert Importer.chosen_bytes(ns) == 0


# --- _space_ok: refuse to start a move that won't fit ---------------------

def test_space_ok_needs_double_the_payload_plus_headroom(monkeypatch):
    from landfall.linux import importer as imp
    manifest = {"files": [{"path": "Documents/big.bin", "size": 1000 * 1024 ** 2}]}  # 1000 MB
    ns = SimpleNamespace(manifest=manifest, chosen_folders=lambda: ["Documents"])
    ns.chosen_bytes = lambda: Importer.chosen_bytes(ns)  # exercise the real accounting

    # Unpacking needs ~2x payload + 200MB headroom = ~2200MB. 3000MB free -> ok.
    monkeypatch.setattr(imp.shutil, "disk_usage",
                        lambda p: SimpleNamespace(free=3000 * 1024 ** 2))
    assert Importer._space_ok(ns) is True

    # Only 1500MB free -> not enough room, must refuse.
    monkeypatch.setattr(imp.shutil, "disk_usage",
                        lambda p: SimpleNamespace(free=1500 * 1024 ** 2))
    assert Importer._space_ok(ns) is False


def test_space_ok_is_false_without_a_manifest():
    assert Importer._space_ok(SimpleNamespace(manifest=None)) is False

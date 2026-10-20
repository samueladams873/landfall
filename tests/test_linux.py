import pytest

from landfall.linux.apps import choices_from_manifest
from landfall.linux.dirs import user_dirs
from landfall.linux.restore import (RestoreCancelled, WrongPassword, find_bundles,
                                    read_manifest, restore)
from landfall.mapping import load_map, match_all
from landfall.pack import pack
from landfall.scan.folders import FolderInfo, measure


@pytest.fixture
def made(tmp_path):
    win = tmp_path / "win"
    (win / "Documents" / "Taxes").mkdir(parents=True)
    (win / "Documents" / "letter.txt").write_text("Dear Grandma")
    (win / "Documents" / "Taxes" / "2025.pdf").write_bytes(b"%PDF" + b"x" * 5000)
    (win / "Pictures").mkdir()
    (win / "Pictures" / "dog.jpg").write_bytes(b"\xff\xd8" + b"y" * 20000)
    folders = [measure(FolderInfo(n, win / n)) for n in ("Documents", "Pictures")]
    usb = tmp_path / "media" / "user" / "SANDISK"
    usb.mkdir(parents=True)
    grouped = match_all([{"name": "Google Chrome"}, {"name": "Adobe Photoshop 2025"}])
    apps = [{"name": r.app["name"], "group": g, "linux": r.options}
            for g, rs in grouped.items() for r in rs]
    pack(folders, "hunter22", usb, {"apps": apps})
    home = tmp_path / "home"
    dests = {"Documents": home / "Documents", "Pictures": home / "Pictures"}
    return tmp_path, home, dests


def test_finds_bundle_on_usb(made):
    tmp, _, _ = made
    found = find_bundles([tmp / "media"])
    assert len(found) == 1 and found[0].move_folder.name == "Landfall Move"


def test_wrong_password(made):
    tmp, _, _ = made
    bundle = find_bundles([tmp / "media"])[0]
    with pytest.raises(WrongPassword):
        read_manifest(bundle, "nope")


def test_restore_puts_files_in_place_and_cleans_up(made):
    tmp, home, dests = made
    bundle = find_bundles([tmp / "media"])[0]
    manifest = read_manifest(bundle, "hunter22")
    r = restore(bundle, "hunter22", ["Documents", "Pictures"], dests, manifest, home=home)
    assert r.restored == 3 and not r.failed
    assert (home / "Documents" / "letter.txt").read_text() == "Dear Grandma"
    assert (home / "Documents" / "Taxes" / "2025.pdf").stat().st_size == 5004
    assert not list(home.glob(".landfall-unpack-*"))  # staging removed


def test_never_overwrites(made):
    tmp, home, dests = made
    (home / "Documents").mkdir(parents=True)
    (home / "Documents" / "letter.txt").write_text("my newer Linux letter")
    bundle = find_bundles([tmp / "media"])[0]
    manifest = read_manifest(bundle, "hunter22")
    r = restore(bundle, "hunter22", ["Documents"], dests, manifest, home=home)
    assert (home / "Documents" / "letter.txt").read_text() == "my newer Linux letter"
    assert (home / "Documents" / "letter (from Windows).txt").read_text() == "Dear Grandma"
    assert len(r.renamed) == 1
    again = restore(bundle, "hunter22", ["Documents"], dests, manifest, home=home)
    assert again.restored == 0 or again.already_there >= 1


def test_only_chosen_folders(made):
    tmp, home, dests = made
    bundle = find_bundles([tmp / "media"])[0]
    manifest = read_manifest(bundle, "hunter22")
    restore(bundle, "hunter22", ["Pictures"], dests, manifest, home=home)
    assert (home / "Pictures" / "dog.jpg").exists()
    assert not (home / "Documents").exists()


def test_cancel_leaves_nothing_behind(made):
    tmp, home, dests = made
    bundle = find_bundles([tmp / "media"])[0]
    manifest = read_manifest(bundle, "hunter22")
    with pytest.raises(RestoreCancelled):
        restore(bundle, "hunter22", ["Documents", "Pictures"], dests, manifest,
                cancelled=lambda: True, home=home)
    assert not (home / "Documents").exists()
    assert not list(home.glob(".landfall-unpack-*"))


def test_old_bundles_get_the_recommended_pick(made):
    tmp, _, _ = made
    manifest = read_manifest(find_bundles([tmp / "media"])[0], "hunter22")
    names = {c.linux_name: c for c in choices_from_manifest(manifest)}
    assert names["Google Chrome"].flatpak == "com.google.Chrome"
    assert names["GIMP"].flatpak == "org.gimp.GIMP"   # first option for Photoshop
    assert "PhotoCraft" not in names                   # extras are only installed if picked


def test_user_picks_are_used_exactly():
    manifest = {"install": [
        {"windows": "Microsoft Edge", "name": "Firefox", "flatpak": "org.mozilla.firefox",
         "commands": ["firefox"], "snap": "firefox"},
        {"windows": "Adobe Photoshop", "name": "PhotoCraft",
         "url": "https://github.com/storytold/photocraft", "new": True},
    ], "apps": [{"name": "Microsoft Edge", "linux": [{"name": "Microsoft Edge"}]}]}
    picks = choices_from_manifest(manifest)
    assert [c.linux_name for c in picks] == ["Firefox", "PhotoCraft"]
    assert picks[1].flatpak is None and picks[1].new


def test_already_present_detects_snap_flatpak_and_command():
    from landfall.linux.apps import AppChoice, already_present
    ff = AppChoice("Microsoft Edge", "Firefox", "org.mozilla.firefox", None,
                   commands=["definitely-not-a-real-command"], snap="firefox")
    assert already_present(ff, set(), {"firefox"})
    assert already_present(ff, {"org.mozilla.firefox"}, set())
    assert not already_present(ff, set(), set())
    sh = AppChoice("x", "Shell", "org.example.Sh", None, commands=["sh"])
    assert already_present(sh, set(), set())


def test_user_dirs_reads_translated_names(tmp_path, monkeypatch):
    cfg = tmp_path / ".config"
    cfg.mkdir()
    (cfg / "user-dirs.dirs").write_text('XDG_PICTURES_DIR="$HOME/Bilder"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    d = user_dirs(tmp_path)
    assert d["Pictures"] == tmp_path / "Bilder"
    assert d["Documents"] == tmp_path / "Documents"


def test_extra_folders_and_files_round_trip(tmp_path):
    """Folders/files the user adds on Windows (with some items unticked) land in
    ~/From Windows on Linux."""
    from landfall.scan.folders import extra_files, extra_folder
    win = tmp_path / "win"
    proj = win / "D-drive" / "Projects"
    (proj / "keep").mkdir(parents=True)
    (proj / "skip").mkdir()
    (proj / "keep" / "plan.txt").write_text("plan")
    (proj / "skip" / "huge.bin").write_bytes(b"x" * 1000)
    (proj / "notes.txt").write_text("notes")
    single = win / "taxes.pdf"
    single.write_bytes(b"%PDF-1")
    docs = win / "Documents"
    docs.mkdir()
    (docs / "a.txt").write_text("a")
    std = measure(FolderInfo("Documents", docs))
    taken = {"Documents"}
    fold = extra_folder(proj, taken)
    fold.excludes = {str(proj / "skip")}
    measure(fold)
    files = measure(extra_files([single], taken | {fold.name}))
    assert fold.name == "Projects" and fold.files == 2          # skip/ left out
    assert files.files == 1
    usb = tmp_path / "usb"
    usb.mkdir()
    pack([std, fold, files], "pw1234", usb,
         {"extra_folders": [fold.name, files.name]})
    bundle = find_bundles([usb])[0]
    manifest = read_manifest(bundle, "pw1234")
    home = tmp_path / "home"
    dests = {"Documents": home / "Documents",
             "Projects": home / "From Windows" / "Projects",
             "Other files": home / "From Windows" / "Other files"}
    r = restore(bundle, "pw1234", manifest["folders"], dests, manifest, home=home)
    assert r.restored == 4
    assert (home / "From Windows" / "Projects" / "keep" / "plan.txt").read_text() == "plan"
    assert not (home / "From Windows" / "Projects" / "skip").exists()
    assert (home / "From Windows" / "Other files" / "taxes.pdf").exists()
    assert (home / "Documents" / "a.txt").exists()


def test_new_apps_show_in_the_menu_without_logging_out(tmp_path):
    from landfall.linux.apps import make_visible
    exp = tmp_path / ".local/share/flatpak/exports/share"
    (exp / "applications").mkdir(parents=True)
    (exp / "applications" / "org.videolan.VLC.desktop").write_text("[Desktop Entry]\nName=VLC\n")
    (exp / "icons/hicolor/128x128/apps").mkdir(parents=True)
    (exp / "icons/hicolor/128x128/apps/org.videolan.VLC.png").write_bytes(b"png")
    assert make_visible(tmp_path) == 1
    link = tmp_path / ".local/share/applications/org.videolan.VLC.desktop"
    assert link.is_symlink() and "VLC" in link.read_text()
    assert (tmp_path / ".local/share/icons/hicolor/128x128/apps/org.videolan.VLC.png").exists()
    assert make_visible(tmp_path) == 0          # running again changes nothing


def test_empty_chosen_folder_is_still_created(made):
    tmp, home, dests = made
    bundle = find_bundles([tmp / "media"])[0]
    manifest = read_manifest(bundle, "hunter22")
    manifest["folders"].append("Saved Games")
    dests["Saved Games"] = home / "From Windows" / "Saved Games"
    restore(bundle, "hunter22", ["Documents", "Saved Games"], dests, manifest, home=home)
    assert (home / "From Windows" / "Saved Games").is_dir()


def test_windows_only_files_are_left_behind_unless_asked(tmp_path):
    desk = tmp_path / "Desktop"
    desk.mkdir()
    for n in ("uTorrent.lnk", "Firefox.exe", "setup.msi", "photo.jpg", "notes.txt"):
        (desk / n).write_text("x")
    f = measure(FolderInfo("Desktop", desk))
    assert sorted(rel.name for _, rel, _ in f.file_list) == ["notes.txt", "photo.jpg"]
    assert f.windows_only == 3
    keep = FolderInfo("Desktop", desk, keep_windows_files=True)
    assert measure(keep).files == 5 and keep.windows_only == 0


def test_windows_web_shortcut_becomes_a_linux_link(tmp_path):
    from landfall.linux.restore import windows_url_to_link
    url = tmp_path / "Bank.url"
    url.write_text("[InternetShortcut]\r\nURL=https://bank.landfall-test.example/\r\n")
    link = windows_url_to_link(url)
    assert link.name == "Bank.desktop" and not url.exists()
    text = link.read_text()
    assert "Type=Link" in text and "URL=https://bank.landfall-test.example/" in text
    odd = tmp_path / "Weird.url"
    odd.write_text("not a shortcut")
    assert windows_url_to_link(odd) == odd               # left alone if it can't be read

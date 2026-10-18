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
    assert len(found) == 1 and found[0].folder.name == "Landfall Move"


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


def test_app_choices(made):
    tmp, _, _ = made
    manifest = read_manifest(find_bundles([tmp / "media"])[0], "hunter22")
    choices = choices_from_manifest(manifest)
    by_name = {c.linux_name: c for c in choices}
    assert by_name["Google Chrome"].flatpak == "com.google.Chrome"
    assert by_name["GIMP"].flatpak == "org.gimp.GIMP"
    assert by_name["PhotoCraft"].new and by_name["PhotoCraft"].url


def test_user_dirs_reads_translated_names(tmp_path, monkeypatch):
    cfg = tmp_path / ".config"
    cfg.mkdir()
    (cfg / "user-dirs.dirs").write_text('XDG_PICTURES_DIR="$HOME/Bilder"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    d = user_dirs(tmp_path)
    assert d["Pictures"] == tmp_path / "Bilder"
    assert d["Documents"] == tmp_path / "Documents"

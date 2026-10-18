import json

import multivolumefile
import py7zr
import pytest

from landfall import pack as pack_mod
from landfall.pack import BUNDLE_NAME, PackCancelled, choose_output_folder, pack, space_needed
from landfall.scan.folders import FolderInfo, human_size, measure


@pytest.fixture
def home(tmp_path):
    docs = tmp_path / "home" / "Documents"
    (docs / "Taxes").mkdir(parents=True)
    (docs / "letter.txt").write_text("Dear Grandma")
    (docs / "Taxes" / "2025.pdf").write_bytes(b"%PDF" + b"x" * 5000)
    (docs / "desktop.ini").write_text("junk")
    pics = tmp_path / "home" / "Pictures"
    pics.mkdir()
    (pics / "dog.jpg").write_bytes(b"\xff\xd8" + b"y" * 20000)
    return tmp_path


def open_bundle(result, password):
    vol = multivolumefile.open(str(result.folder / BUNDLE_NAME), mode="rb")
    return py7zr.SevenZipFile(vol, "r", password=password)


def measured(home):
    base = home / "home"
    return [measure(FolderInfo("Documents", base / "Documents")),
            measure(FolderInfo("Pictures", base / "Pictures"))]


def test_measure_counts_files_and_skips_junk(home):
    docs, pics = measured(home)
    assert docs.files == 2 and pics.files == 1
    assert docs.bytes == 12 + 5004
    assert all(rel.parts[0] == "Documents" for _, rel, _ in docs.file_list)


def test_pack_roundtrip_with_password(home):
    folders = measured(home)
    usb = home / "usb"
    usb.mkdir()
    seen = []
    result = pack(folders, "hunter22", usb, {"apps": [{"name": "Google Chrome"}]},
                  progress=lambda d, t, n: seen.append((d, t)))
    assert result.files == 3 and not result.skipped
    assert (result.folder / "READ ME.txt").exists()
    assert seen[-1][0] == seen[-1][1]

    out = home / "out"
    with open_bundle(result, "hunter22") as z:
        z.extractall(out)
    assert (out / "Documents" / "letter.txt").read_text() == "Dear Grandma"
    assert (out / "Pictures" / "dog.jpg").stat().st_size == 20002
    manifest = json.loads((out / "landfall" / "manifest.json").read_text())
    assert manifest["apps"][0]["name"] == "Google Chrome"
    assert len(manifest["files"]) == 3


def test_wrong_password_is_rejected(home):
    result = pack(measured(home), "right-pass", home)
    with pytest.raises(Exception):
        with open_bundle(result, "wrong-pass") as z:
            z.extractall(home / "nope")


def test_splits_into_parts(home, monkeypatch):
    monkeypatch.setattr(pack_mod, "PART_SIZE", 8000)
    result = pack(measured(home), "pw1234", home)
    assert len(result.parts) >= 3
    with open_bundle(result, "pw1234") as z:
        assert "Pictures/dog.jpg" in z.getnames()


def test_cancel_cleans_up(home):
    usb = home / "usb"
    usb.mkdir()
    with pytest.raises(PackCancelled):
        pack(measured(home), "pw1234", usb, cancelled=lambda: True)
    assert list(usb.iterdir()) == []


def test_never_overwrites_an_earlier_bundle(home):
    first = pack(measured(home), "pw1234", home).folder
    assert choose_output_folder(home) != first
    second = pack(measured(home), "pw1234", home).folder
    assert second.name == "Landfall Move (2)"


def test_space_and_sizes():
    assert space_needed(1_000_000_000) > 1_000_000_000
    assert human_size(1536) == "1.5 KB"

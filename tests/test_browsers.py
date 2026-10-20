import json
import sqlite3

import pytest

from landfall.linux import browsers as lb
from landfall.linux.restore import extract_private, find_bundles, read_manifest
from landfall.pack import browser_folders, browser_records, pack
from landfall.scan.browsers import find_browsers

BOOKMARKS_EDGE = {"roots": {
    "bookmark_bar": {"type": "folder", "name": "Favorites bar", "children": [
        {"type": "url", "name": "TEST 1 - Wikipedia", "url": "https://www.wikipedia.org/"},
        {"type": "folder", "name": "Recipes (test folder)", "children": [
            {"type": "url", "name": "TEST 3 - Allrecipes", "url": "https://www.allrecipes.com/"}]}]},
    "other": {"type": "folder", "name": "Other favorites", "children": [
        {"type": "url", "name": "TEST 2 - Weather", "url": "https://www.weather.gov/"}]},
    "synced": {"type": "folder", "name": "Mobile", "children": []}}, "version": 1}


def make_firefox_places(path):
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url TEXT, title TEXT, visit_count INT);
        CREATE TABLE moz_bookmarks (id INTEGER PRIMARY KEY, type INT, fk INT, parent INT,
                                    position INT, title TEXT, guid TEXT);
        INSERT INTO moz_places VALUES (1,'https://www.wikipedia.org/','Wikipedia',5),
                                      (2,'https://www.weather.gov/','Weather',2),
                                      (3,'https://example.com/never-visited','x',0),
                                      (4,'place:tag=x','tag query',0);
        INSERT INTO moz_bookmarks VALUES (1,2,NULL,0,0,'','root________'),
            (2,2,NULL,1,0,'menu','menu________'), (3,2,NULL,1,1,'toolbar','toolbar_____'),
            (4,2,NULL,1,2,'tags','tags________'), (5,2,NULL,1,3,'unfiled','unfiled_____'),
            (10,2,NULL,3,0,'Landfall Test','f1'), (11,1,1,10,0,'TEST 1 - Wikipedia','b1'),
            (12,1,2,10,1,'TEST 2 - Weather','b2'), (13,2,NULL,4,0,'mytag','t1'),
            (14,1,1,13,0,NULL,'b3'), (15,1,4,5,0,'smart','b4');
    """)
    con.commit()
    con.close()


@pytest.fixture
def windows(tmp_path):
    appdata, local = tmp_path / "Roaming", tmp_path / "Local"
    ff = appdata / "Mozilla/Firefox/Profiles/abcd.default-release"
    ff.mkdir(parents=True)
    (appdata / "Mozilla/Firefox/profiles.ini").write_text(
        "[Profile0]\nName=default-release\nIsRelative=1\nPath=Profiles/abcd.default-release\nDefault=1\n")
    make_firefox_places(ff / "places.sqlite")
    (ff / "logins.json").write_text(json.dumps({"logins": [{"hostname": "https://bank.landfall-test.example"}] * 3}))
    (ff / "key4.db").write_bytes(b"key")
    edge = local / "Microsoft/Edge/User Data/Default"
    edge.mkdir(parents=True)
    (edge / "Bookmarks").write_text(json.dumps(BOOKMARKS_EDGE))
    con = sqlite3.connect(edge / "History")
    con.execute("CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT)")
    con.executemany("INSERT INTO urls (url) VALUES (?)", [("https://a.example",), ("https://b.example",)])
    con.commit()
    con.close()
    csv = tmp_path / "Microsoft Edge Passwords.csv"
    csv.write_text("name,url,username,password\nBank,https://bank.landfall-test.example,roger,Fake-Bank-Pass-111\n")
    return tmp_path, {"APPDATA": str(appdata), "LOCALAPPDATA": str(local)}, csv


def test_finds_and_counts_browsers(windows):
    _, env, _ = windows
    found = {p.browser: p for p in find_browsers(env)}
    ff, edge = found["firefox"], found["edge"]
    assert (ff.bookmarks, ff.history, ff.passwords) == (2, 2, 3)   # tag copies not counted
    assert (edge.bookmarks, edge.history) == (3, 2)
    assert edge.family == "chromium" and edge.password_url.startswith("edge://")


def test_bookmark_trees(windows):
    tmp, env, _ = windows
    ff = tmp / "Roaming/Mozilla/Firefox/Profiles/abcd.default-release/places.sqlite"
    tree = lb.read_firefox_bookmarks(ff)
    titles = [t["title"] for t in tree]
    assert "Bookmarks bar" in titles and all("tag" not in t.lower() for t in titles)
    assert lb.count_links(tree) == 2                      # place: queries and tags skipped
    edge = lb.read_chromium_bookmarks(tmp / "Local/Microsoft/Edge/User Data/Default/Bookmarks")
    assert lb.count_links(edge) == 3
    html = lb.to_bookmarks_html(edge, "Imported from Microsoft Edge")
    assert "TEST 3 - Allrecipes" in html and "<H3>Imported from Microsoft Edge</H3>" in html
    assert 'PERSONAL_TOOLBAR_FOLDER="true"' in html          # favorites bar -> toolbar


def test_full_trip_into_firefox_and_chromium(windows, tmp_path):
    tmp, env, csv = windows
    profiles = find_browsers(env)
    edge = next(p for p in profiles if p.browser == "edge")
    edge.password_csv = csv
    usb = tmp_path / "usb"
    usb.mkdir()
    pack(browser_folders(profiles), "pw1234", usb, {"browsers": browser_records(profiles)})
    bundle = find_bundles([usb])[0]
    manifest = read_manifest(bundle, "pw1234")
    assert manifest["folders"] == []                     # browser data is not a folder
    out = tmp_path / "unpacked"
    extract_private(bundle, "pw1234", "landfall/browsers/", out)
    recs = {r["browser"]: r for r in manifest["browsers"]}

    home = tmp_path / "home"
    ffroot = home / "snap/firefox/common/.mozilla/firefox"
    (ffroot / "xyz.default-release").mkdir(parents=True)
    (ffroot / "profiles.ini").write_text("[Profile0]\nName=default-release\nIsRelative=1\n"
                                         "Path=xyz.default-release\nDefault=1\n")
    firefox = lb.Target("firefox", "snap", ["true"], ffroot)

    res = lb.import_browser(recs["firefox"], out / "landfall/browsers" / recs["firefox"]["key"],
                            firefox, home)
    prof = ffroot / "xyz.default-release"
    assert res.passwords == "copied" and res.history and not res.problem
    assert (prof / "logins.json").exists() and (prof / "key4.db").exists()
    assert (prof / "places.sqlite").stat().st_size > 0

    res = lb.import_browser(recs["edge"], out / "landfall/browsers" / recs["edge"]["key"],
                            firefox, home)
    assert res.bookmarks == 3 and res.passwords == "file"
    assert "Imported from Microsoft Edge" in (prof / "bookmarks.html").read_text()
    prefs = (prof / "prefs.js").read_text()
    assert 'browser.places.importBookmarksHTML", true' in prefs
    assert 'browser.toolbars.bookmarks.visibility", "always"' in prefs
    assert oct(res.password_file.stat().st_mode)[-3:] == "600"
    assert res.import_command == ["true", "about:logins"]

    croot = home / ".config/chromium"
    (croot / "Default").mkdir(parents=True)
    chromium = lb.Target("chromium", "deb", ["true"], croot)
    res = lb.import_browser(recs["edge"], out / "landfall/browsers" / recs["edge"]["key"],
                            chromium, home)
    data = json.loads((croot / "Default/Bookmarks").read_text())
    folder = data["roots"]["bookmark_bar"]["children"][-1]
    assert folder["name"] == "Imported from Microsoft Edge" and "checksum" not in data
    assert res.history and (croot / "Default/History").exists()


def test_existing_chromium_bookmarks_are_kept(tmp_path):
    prof = tmp_path / "Default"
    prof.mkdir()
    (prof / "Bookmarks").write_text(json.dumps({**BOOKMARKS_EDGE, "checksum": "abc"}))
    lb.write_chromium_bookmarks(prof, [{"title": "x", "url": "https://x.example/"}], "Imported from Firefox")
    data = json.loads((prof / "Bookmarks").read_text())
    names = [c["name"] for c in data["roots"]["bookmark_bar"]["children"]]
    assert names[0] == "TEST 1 - Wikipedia" and names[-1] == "Imported from Firefox"
    ids = []

    def walk(n):
        ids.append(n.get("id"))
        for c in n.get("children", []):
            walk(c)
    for r in data["roots"].values():
        if isinstance(r, dict):
            walk(r)
    assert len([i for i in ids if i]) == len(set(i for i in ids if i))   # no duplicate ids


def test_targets_follow_the_users_pick(tmp_path):
    home = tmp_path
    targets = lb.choose_targets(["org.chromium.Chromium"], home, {"org.chromium.Chromium"}, {"firefox"})
    assert [t.browser for t in targets] == ["chromium"]
    assert lb.match_target("firefox", "firefox", targets).browser == "chromium"
    both = lb.choose_targets(["org.mozilla.firefox", "org.chromium.Chromium"], home,
                             {"org.chromium.Chromium"}, {"firefox"})
    assert lb.match_target("chromium", "edge", both).browser == "chromium"
    assert lb.match_target("firefox", "firefox", both).browser == "firefox"
    fallback = lb.choose_targets([], home, set(), {"firefox"})
    assert [t.browser for t in fallback] == ["firefox"] and fallback[0].how == "snap"

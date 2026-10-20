from landfall.linux.system_update import ProgressParser, UpdatePlan, detect, script_for


def test_script_fails_if_the_update_fails_but_not_if_app_refresh_fails():
    s = script_for(UpdatePlan("apt", "Ubuntu"))
    assert "full-upgrade" in s and "|| FAIL=1" in s
    assert s.strip().endswith("exit $FAIL")
    assert "flatpak update" in s and "snap refresh" in s
    assert "DPkg::Lock::Timeout" in s          # waits if the PC is already updating itself
    for tool in ("dnf", "zypper", "pacman"):
        assert "|| FAIL=1" in script_for(UpdatePlan(tool, "x"))


def test_apt_progress_is_read_from_real_output():
    p = ProgressParser("apt")
    assert p.feed("LANDFALL STAGE install") == ("stage", "install")
    assert p.feed("173 upgraded, 2 newly installed, 0 to remove and 0 not upgraded.") == \
        ("progress", 0, 350)
    ev = p.feed("Unpacking gpgconf (2.4.8-4ubuntu3.1) over (2.4.8-4ubuntu3) ...")
    assert ev[:3] == ("progress", 1, 350) and ev[3] == "gpgconf"
    ev = p.feed("Setting up libcurl4t64:amd64 (8.18.0-1ubuntu2.8) ...")
    assert ev[:3] == ("progress", 2, 350) and ev[3] == "libcurl4t64"
    assert p.feed("E: Could not get lock /var/lib/dpkg/lock-frontend")[0] == "item"
    assert p.feed("LANDFALL DONE") == ("stage", "done")


def test_dnf_progress():
    p = ProgressParser("dnf")
    ev = p.feed("  Upgrading        : firefox-131.0-1.fc44.x86_64            12/40 ")
    assert ev[:3] == ("progress", 12, 40)


def test_detects_this_linux(tmp_path):
    osr = tmp_path / "os-release"
    osr.write_text('NAME="Ubuntu"\nVERSION_ID="26.04"\n')
    plan = detect(osr)
    assert plan is None or plan.label == "Ubuntu"

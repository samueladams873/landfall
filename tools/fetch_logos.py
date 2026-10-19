"""Download each Linux app's official icon from Flathub into src/landfall/data/applogos.

Run at build time (GitHub Actions does this before packaging), so the shipped app can show
real logos without ever going online itself.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "landfall" / "data"
OUT = DATA / "applogos"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    apps = json.loads((DATA / "app_map.json").read_text(encoding="utf-8"))["apps"]
    ids = sorted({o["flatpak"] for a in apps for o in a["linux"] if o.get("flatpak")})
    missing = []
    for app_id in ids:
        target = OUT / f"{app_id}.png"
        if target.exists() and target.stat().st_size > 0:
            continue
        try:
            with urllib.request.urlopen(f"https://flathub.org/api/v2/appstream/{app_id}",
                                        timeout=30) as r:
                icon = json.load(r).get("icon")
            if not icon:
                raise ValueError("no icon listed")
            with urllib.request.urlopen(icon, timeout=30) as r:
                target.write_bytes(r.read())
        except Exception as err:  # noqa: BLE001 - report and keep going
            missing.append(f"{app_id}: {err}")
        time.sleep(0.2)
    print(f"{len(ids) - len(missing)} of {len(ids)} logos ready in {OUT}")
    for m in missing:
        print("  missing", m)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

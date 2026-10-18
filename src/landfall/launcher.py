"""Pick the right half of Landfall: the packer on Windows, the unpacker on Linux."""
import os
import sys


def main() -> int:
    mode = os.environ.get("LANDFALL_MODE") or ("pack" if sys.platform == "win32" else "unpack")
    if mode == "pack":
        from landfall.app import main as run
    else:
        from landfall.linux.importer import main as run
    return run()

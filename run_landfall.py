"""Entry point used by PyInstaller."""
import multiprocessing
import sys

if __name__ == "__main__":
    # In a packaged app, a library starting a helper process must not relaunch Landfall
    # from the Welcome page. This makes such helpers run their job and exit.
    multiprocessing.freeze_support()
    from landfall.launcher import main
    sys.exit(main())

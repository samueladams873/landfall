"""Entry point used by PyInstaller to build the Windows .exe."""
import sys

from landfall.app import main

sys.exit(main())

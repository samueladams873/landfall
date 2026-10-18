"""Start system programs safely from the packaged app.

PyInstaller points LD_LIBRARY_PATH (and friends) at Landfall's bundled libraries so
Landfall itself runs. Programs Landfall starts (flatpak, pkexec, xdg-open...) must NOT
inherit that, or they load the wrong library versions and fail. Landfall's own
environment is left untouched; each child gets a cleaned copy.
"""
from __future__ import annotations

import os
import subprocess
import sys

_VARS = ("LD_LIBRARY_PATH", "QT_PLUGIN_PATH", "QML2_IMPORT_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
         "SSL_CERT_FILE", "SSL_CERT_DIR", "GIO_MODULE_DIR", "GTK_PATH", "GDK_PIXBUF_MODULE_FILE")


def system_env() -> dict:
    env = dict(os.environ)
    if getattr(sys, "frozen", False) and sys.platform != "win32":
        for var in _VARS:
            original = env.pop(var + "_ORIG", None)
            if original is not None:
                env[var] = original
            else:
                env.pop(var, None)
    return env


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault("env", system_env())
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run(cmd, **kwargs)


def open_path(target: str) -> None:
    """Open a folder, file or web link with the user's normal apps."""
    if sys.platform == "win32":
        os.startfile(target)  # noqa: S606
    else:
        subprocess.Popen(["xdg-open", target], env=system_env(), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)

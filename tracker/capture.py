"""Fabrique de capture : choisit le backend selon l'OS.

Import PARESSEUX du backend pour ne charger winrt que sur Windows (indispo
sur Linux) et inversement. Le reste du programme ne connait que Snapshot +
l'interface (start / snapshot).
"""
from __future__ import annotations
import sys

from .capture_base import Snapshot  # noqa: F401 (re-export pratique)


def make_capture(allowlist):
    if sys.platform == "win32":
        from .capture_windows import Capture
    elif sys.platform.startswith("linux"):
        from .capture_linux import Capture
    else:
        raise RuntimeError(f"Plateforme non supportee pour la capture : {sys.platform}")
    return Capture(allowlist)

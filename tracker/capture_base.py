"""Type partage entre les backends de capture (Windows SMTC, Linux MPRIS)."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Snapshot:
    wall: float       # time.time() de la capture
    app: str
    title: str
    artist: str
    album: str
    playing: bool
    position: float   # secondes
    duration: float   # secondes

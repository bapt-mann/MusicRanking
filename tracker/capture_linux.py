"""Backend de capture Linux via MPRIS (D-Bus), en shell-out sur `playerctl`.

Valide sur Spotify Linux : la Position avance regulierement (~1/s), mieux
meme que SMTC. On appelle playerctl (paquet systeme a installer) et on
reconstruit le meme Snapshot que le backend Windows.
"""
from __future__ import annotations
import asyncio
import time

from .capture_base import Snapshot

PLAYERCTL = "playerctl"
_META_FMT = "{{mpris:length}}\t{{title}}\t{{artist}}\t{{album}}"


async def _run(args):
    """Lance playerctl, renvoie stdout strippe ou None (erreur / pas de player)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            PLAYERCTL, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return out.decode("utf-8", "replace").strip()


class Capture:
    def __init__(self, allowlist):
        # allowlist ignoree : on cible directement le player MPRIS "spotify"
        self.player = "spotify"

    async def start(self):
        if await _run(["--version"]) is None:
            raise RuntimeError(
                "playerctl introuvable. Installe-le :\n"
                "  Debian/Ubuntu : sudo apt install playerctl\n"
                "  Fedora        : sudo dnf install playerctl\n"
                "  Arch          : sudo pacman -S playerctl"
            )

    async def snapshot(self):
        status, meta, pos = await asyncio.gather(
            _run(["-p", self.player, "status"]),
            _run(["-p", self.player, "metadata", "--format", _META_FMT]),
            _run(["-p", self.player, "position"]),
        )
        if status is None or not meta:
            return None  # Spotify ferme / aucun player

        parts = meta.split("\t")
        if len(parts) < 4:
            return None
        length_us, title, artist, album = parts[0], parts[1], parts[2], parts[3]

        try:
            position = float(pos) if pos else 0.0
        except ValueError:
            position = 0.0
        try:
            duration = int(length_us) / 1_000_000 if length_us else 0.0
        except ValueError:
            duration = 0.0

        return Snapshot(
            wall=time.time(), app="spotify",
            title=title, artist=artist, album=album,
            playing=(status == "Playing"),
            position=position, duration=duration,
        )

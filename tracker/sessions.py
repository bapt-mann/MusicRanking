"""Reconstruction des sessions d'ecoute a partir des instantanes.

Points cles (valides par le probe Phase 0) :
- on suit la POSITION MAX atteinte par morceau ;
- au changement de titre, on cloture l'ancien avec SON max_pos ;
- on IGNORE la position/duree du 1er instantane d'un nouveau titre
  (titre et timeline se desynchronisent ~1 tick a la bascule).
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

from . import config
from .normalize import track_key


def _iso(wall: float) -> str:
    return datetime.fromtimestamp(wall, timezone.utc).isoformat(timespec="seconds")


@dataclass
class _Live:
    title: str
    artist: str
    album: str
    key: str
    started_wall: float
    last_wall: float
    duration: float = 0.0   # rempli au 1er instantane confirmant (evite la desync)
    max_pos: float = 0.0
    samples: int = 0        # 0 = instantane d'ouverture, position non encore fiable


class SessionTracker:
    """Consomme des Snapshot et emet des dict "play" termines via on_emit."""

    def __init__(self, on_emit):
        self.on_emit = on_emit
        self.cur: _Live | None = None
        self.idle = 0

    @staticmethod
    def _ident(title: str, artist: str):
        return (title.strip().lower(), artist.strip().lower())

    def feed(self, snap):
        if snap is None or not snap.playing:
            # Pause/arret : on NE cloture PAS sur une breve pause (sinon un morceau
            # en pause pres de la fin se dedouble). On ferme apres une longue
            # inactivite seulement.
            self.idle += 1
            if self.cur and self.idle * config.POLL_INTERVAL >= config.IDLE_FINALIZE_SEC:
                self._finalize()
            return
        self.idle = 0

        if self.cur is None:
            self._open(snap)
            return

        if self._ident(snap.title, snap.artist) != self._ident(self.cur.title, self.cur.artist):
            self._finalize()          # cloture l'ancien avec son max_pos
            self._open(snap)          # nouvelle session (position ignoree ce tick)
            return

        # meme morceau
        self.cur.samples += 1
        self.cur.last_wall = snap.wall
        if self.cur.duration <= 0 and snap.duration > 0:
            self.cur.duration = snap.duration
        # detection de replay : la position revient VRAIMENT au debut (< 15 s) apres
        # avoir bien avance -> nouvelle ecoute. Le seuil bas evite de declencher sur
        # les sauts de position erratiques (ex. mirroring Spotify Connect).
        if snap.position < 15 and self.cur.max_pos - snap.position > 30:
            self._finalize()
            self._open(snap)
            return
        self.cur.max_pos = max(self.cur.max_pos, snap.position)

    def _open(self, snap):
        # duree/position volontairement NON prises ici (desync titre/timeline)
        self.cur = _Live(
            title=snap.title, artist=snap.artist, album=snap.album,
            key=track_key(snap.title, snap.artist),
            started_wall=snap.wall, last_wall=snap.wall,
        )

    def _finalize(self):
        c, self.cur = self.cur, None
        if c is None or c.duration < config.MIN_TRACK_SEC:
            return
        listened = min(c.max_pos, c.duration)
        pct = listened / c.duration if c.duration > 0 else 0.0
        if pct >= config.COMPLETE_AT:
            pct = 1.0
        self.on_emit({
            "title_raw": c.title, "artist_raw": c.artist, "album_raw": c.album,
            "track_key": c.key,
            "duration_ms": int(c.duration * 1000),
            "listened_ms": int(listened * 1000),
            "percent": round(pct, 4),
            "completed": 1 if pct >= 1.0 else 0,
            "started_at": _iso(c.started_wall),
            "ended_at": _iso(c.last_wall),
        })

    def close(self):
        self._finalize()

"""Reconstruction des sessions d'ecoute a partir des instantanes.

Metrique : on cumule le TEMPS REELLEMENT ECOUTE. Les seeks en arriere ne
comptent pas le saut, mais reecouter un passage rejoue le temps -> le score
d'une ecoute = temps ecoute / duree, qui peut depasser 1.0 (replays) et est
plafonne a config.RATIO_CAP.

Points cles (valides en Phase 0) :
- au changement de titre, on cloture l'ecoute en cours ;
- on ignore la position du 1er instantane d'un nouveau titre (desync
  titre/timeline ~1 tick a la bascule) : elle sert juste a amorcer last_pos ;
- un retour au tout debut (< 15 s) apres avoir bien avance = nouvelle ecoute ;
- on ne peut pas consommer plus de secondes d'audio que de temps reel ecoule.
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
    duration: float = 0.0
    listened: float = 0.0    # secondes reellement ecoutees (cumule, replays compris)
    last_pos: float = -1.0   # derniere position vue (-1 = pas encore amorcee)


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
            # inactivite seulement, et on coupe le fil de position pour ne pas
            # compter la pause comme du temps ecoute.
            self.idle += 1
            if self.cur is not None:
                self.cur.last_pos = -1.0
                if self.idle * config.POLL_INTERVAL >= config.IDLE_FINALIZE_SEC:
                    self._finalize()
            return
        self.idle = 0

        if self.cur is None:
            self._open(snap)
            return

        if self._ident(snap.title, snap.artist) != self._ident(self.cur.title, self.cur.artist):
            self._finalize()      # cloture l'ecoute precedente
            self._open(snap)      # nouvelle ecoute (position ignoree ce tick)
            return

        # meme morceau
        if self.cur.duration <= 0 and snap.duration > 0:
            self.cur.duration = snap.duration

        # retour au tout debut apres avoir bien avance -> nouvelle ecoute (repeat)
        if snap.position < 15 and self.cur.last_pos - snap.position > 30:
            self._finalize()
            self._open(snap)
            return

        # cumul du temps reellement ecoute (borne par le temps reel ecoule)
        if self.cur.last_pos >= 0:
            pos_delta = snap.position - self.cur.last_pos
            wall_delta = snap.wall - self.cur.last_wall
            if pos_delta > 0 and wall_delta > 0:
                self.cur.listened += min(pos_delta, wall_delta + 1.0)
        self.cur.last_pos = snap.position
        self.cur.last_wall = snap.wall

    def _open(self, snap):
        # duree/position NON prises ici (desync titre/timeline a la bascule)
        self.cur = _Live(
            title=snap.title, artist=snap.artist, album=snap.album,
            key=track_key(snap.title, snap.artist),
            started_wall=snap.wall, last_wall=snap.wall,
        )

    def _finalize(self):
        c, self.cur = self.cur, None
        if c is None or c.duration < config.MIN_TRACK_SEC:
            return
        ratio = c.listened / c.duration if c.duration > 0 else 0.0
        ratio = min(ratio, config.RATIO_CAP)
        self.on_emit({
            "title_raw": c.title, "artist_raw": c.artist, "album_raw": c.album,
            "track_key": c.key,
            "duration_ms": int(c.duration * 1000),
            "listened_ms": int(c.listened * 1000),
            "percent": round(ratio, 4),
            "completed": 1 if ratio >= 1.0 else 0,
            "started_at": _iso(c.started_wall),
            "ended_at": _iso(c.last_wall),
        })

    def close(self):
        self._finalize()

"""Backend de capture Windows via SMTC (System Media Transport Controls, winrt).

Filtre par allowlist d'app, priorise la session en lecture, et EXTRAPOLE la
position : SMTC ne la rafraichit pas chaque seconde (elle "gele" plusieurs
secondes puis saute), donc on ajoute le temps ecoule depuis last_updated_time
pour renvoyer une position lisse.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)

from .capture_base import Snapshot

try:
    from pycaw.pycaw import AudioUtilities
    _HAVE_PYCAW = True
except Exception:  # pragma: no cover
    _HAVE_PYCAW = False

PLAYING = 4  # GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING


def _spotify_audio_active() -> bool:
    """True si Spotify a une session audio ACTIVE sur cet appareil (= son local).

    Anti-fantome Spotify Connect : sur un appareil qui n'est qu'un miroir (le son
    sort ailleurs), Spotify n'a pas de session audio active ici - voire pas
    d'endpoint de rendu du tout. Sans pycaw, on ne filtre pas (comportement d'avant).
    """
    if not _HAVE_PYCAW:
        return True
    try:
        sessions = AudioUtilities.GetAllSessions()
    except Exception:
        return False  # pas d'endpoint de sortie -> pas de son local
    for s in sessions:
        try:
            proc = s.Process
            if proc and "spotify" in (proc.name() or "").lower():
                try:
                    state = s.State
                except Exception:
                    state = s._ctl.GetState()
                return state == 1  # 1 = AudioSessionStateActive
        except Exception:
            continue
    return False  # aucune session audio Spotify -> pas de son local


def _matches(app: str, allowlist) -> bool:
    a = (app or "").lower()
    return any(tok in a for tok in allowlist)


class Capture:
    def __init__(self, allowlist):
        self.allowlist = [t.lower() for t in allowlist]
        self._mgr = None

    async def start(self):
        self._mgr = await MediaManager.request_async()

    async def snapshot(self):
        if self._mgr is None:
            await self.start()
        best = None
        for session in self._mgr.get_sessions():
            app = session.source_app_user_model_id
            if not _matches(app, self.allowlist):
                continue
            try:
                props = await session.try_get_media_properties_async()
            except Exception:
                continue

            pb = session.get_playback_info()
            smtc_playing = int(pb.playback_status) == PLAYING

            tl = session.get_timeline_properties()
            pos = tl.position.total_seconds()
            try:
                dur = (tl.end_time - tl.start_time).total_seconds()
            except Exception:
                dur = 0.0

            if smtc_playing:
                lut = tl.last_updated_time
                if lut is not None:
                    if lut.tzinfo is None:
                        lut = lut.replace(tzinfo=timezone.utc)
                    delta = (datetime.now(timezone.utc) - lut).total_seconds()
                    if 0 <= delta < 3600:  # garde-fou
                        pos += delta
            if dur > 0:
                pos = max(0.0, min(pos, dur))

            # anti-fantome : ne compte comme "playing" que si le son sort
            # REELLEMENT sur cet appareil (sinon c'est un miroir Connect).
            playing = smtc_playing and _spotify_audio_active()

            snap = Snapshot(
                wall=time.time(), app=app,
                title=props.title or "", artist=props.artist or "",
                album=props.album_title or "",
                playing=playing, position=pos, duration=dur,
            )
            if playing:
                return snap
            best = best or snap
        return best

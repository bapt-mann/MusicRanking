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

PLAYING = 4  # GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING


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
            playing = int(pb.playback_status) == PLAYING

            tl = session.get_timeline_properties()
            pos = tl.position.total_seconds()
            try:
                dur = (tl.end_time - tl.start_time).total_seconds()
            except Exception:
                dur = 0.0

            if playing:
                lut = tl.last_updated_time
                if lut is not None:
                    if lut.tzinfo is None:
                        lut = lut.replace(tzinfo=timezone.utc)
                    delta = (datetime.now(timezone.utc) - lut).total_seconds()
                    if 0 <= delta < 3600:  # garde-fou
                        pos += delta
            if dur > 0:
                pos = max(0.0, min(pos, dur))

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

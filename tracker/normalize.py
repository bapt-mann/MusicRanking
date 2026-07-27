"""Cle de dedup CONSERVATRICE : on ne fusionne que les variantes cosmetiques.

On enleve "feat. X" et les tags "Remaster(ed)" ; on GARDE distinctes les
versions reelles (Slowed, Live, Remix, Acoustic, Radio Edit...) car ce sont
des morceaux differents. Mieux vaut sous-fusionner que fusionner a tort.
"""
import re

_FEAT = re.compile(r"\s*[\(\[]?\s*feat\.?\s+[^)\]]*[\)\]]?", re.I)
_REMASTER = re.compile(r"\s*[-(\[]\s*re-?master(ed)?[^)\]]*[\)\]]?\s*$", re.I)
_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = _FEAT.sub("", s)
    s = _REMASTER.sub("", s)
    s = _WS.sub(" ", s).strip(" -")
    return s


def track_key(title: str, artist: str) -> str:
    # On garde le 1er artiste (avant virgule / & / feat / x) pour stabiliser la cle.
    a = (artist or "").lower()
    a = re.split(r"[,;&]| feat| x ", a)[0].strip()
    return f"{_norm(title)}|{_norm(a)}"

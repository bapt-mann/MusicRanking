"""Agregation -> tiers, avec dedup des ecoutes simultanees multi-appareils.

Dedup : meme morceau + intervalles [started, ended] qui se chevauchent
(meme compte Spotify sur 2 appareils = UNE ecoute reelle) -> on garde le
meilleur pourcentage. Deux ecoutes sequentielles ne se chevauchent pas.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime

from . import config


def _parse(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _dedup_percents(rows):
    intervals = sorted(
        ((_parse(r["started_at"]), _parse(r["ended_at"]), r["percent"]) for r in rows),
        key=lambda x: (x[0] or datetime.min),
    )
    merged = []  # [start, end, best_pct]
    for s, e, pct in intervals:
        if merged and s is not None and merged[-1][1] is not None and s <= merged[-1][1]:
            if e is not None:
                merged[-1][1] = max(merged[-1][1], e)
            merged[-1][2] = max(merged[-1][2], pct)
        else:
            merged.append([s, e, pct])
    return [m[2] for m in merged]


def tier_for(score):
    for label, lo in config.TIERS:
        if score >= lo:
            return label
    return config.TIERS[-1][0]


def compute(rows):
    by_key = defaultdict(list)
    meta = {}
    for r in rows:
        by_key[r["track_key"]].append(r)
        meta[r["track_key"]] = (r["title_raw"], r["artist_raw"])
    result = []
    for key, rs in by_key.items():
        pcts = _dedup_percents(rs)
        n = len(pcts)
        if n < config.MIN_PLAYS:
            continue
        score = sum(pcts) / n
        title, artist = meta[key]
        result.append({"title": title, "artist": artist,
                       "plays": n, "score": score, "tier": tier_for(score)})
    order = {lbl: i for i, (lbl, _) in enumerate(config.TIERS)}
    result.sort(key=lambda x: (order[x["tier"]], -x["score"]))
    return result


def render(rows):
    res = compute(rows)
    if not res:
        return f"Pas encore assez d'ecoutes (min {config.MIN_PLAYS} par morceau)."
    lines, cur = [], None
    for x in res:
        if x["tier"] != cur:
            cur = x["tier"]
            lines.append(f"\n=== {cur} ===")
        lines.append(f"  {x['score'] * 100:3.0f}%  {x['title']} - {x['artist']}"
                     f"  ({x['plays']} ecoutes)")
    return "\n".join(lines)

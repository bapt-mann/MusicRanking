"""Configuration + identite de l'appareil (persistees dans data/config.json).

IMPORTANT multi-appareils : mets le MEME user_id sur tous tes appareils
(edite data/config.json) pour que la dedup des ecoutes simultanees fonctionne.
"""
from __future__ import annotations
import getpass
import json
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CONFIG_PATH = DATA_DIR / "config.json"
DB_PATH = DATA_DIR / "plays.sqlite3"

# --- Parametres de ranking (ajustables) ---
POLL_INTERVAL = 2.0       # secondes entre deux lectures SMTC
MIN_PLAYS = 4             # ecoutes mini avant d'attribuer un tier a un morceau
RATIO_CAP = 1.5           # plafond du ratio par ecoute (replays comptent, mais borne)
MIN_TRACK_SEC = 30        # ignore les "morceaux" plus courts (pubs, parasites)
IDLE_FINALIZE_SEC = 300   # cloture une session apres X s de pause/arret (evite les doublons)

# Bareme des tiers : (label, seuil bas inclus), ordre decroissant.
TIERS = [("S", 0.80), ("A", 0.70), ("B", 0.60), ("C", 0.50), ("D", 0.0)]

# Apps dont on capture la lecture (match insensible a la casse, sous-chaine).
APP_ALLOWLIST = ["spotify"]  # plus tard : "deezer", etc.


def load() -> dict:
    """Charge la config, genere user_id/device_id au premier lancement."""
    cfg = {}
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    changed = False
    if not cfg.get("user_id"):
        cfg["user_id"] = getpass.getuser() or "me"
        changed = True
    if not cfg.get("device_id"):
        cfg["device_id"] = uuid.uuid4().hex[:8]
        changed = True
    if changed:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg

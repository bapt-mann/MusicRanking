# Spotify Ranking - tracker (Phase 1 - Windows + Linux)

Classe tes morceaux en tiers **S -> D** selon le **% du morceau reellement ecoute**,
capte via l'API media de l'OS (SMTC sur Windows, MPRIS sur Linux) - **sans aucune cle API Spotify**.

## Installation

```bash
python -m pip install -r requirements.txt
```

- **Windows** : les paquets `winrt-*` s'installent tout seuls (capture SMTC).
- **Linux** : installe **playerctl** via ton gestionnaire de paquets (capture MPRIS) :
  `sudo apt install playerctl` (Debian/Ubuntu) - `sudo dnf install playerctl` (Fedora) - `sudo pacman -S playerctl` (Arch).

## Utilisation

```bash
python -m tracker track    # lance le suivi en direct (Ctrl+C pour arreter)
python -m tracker rank     # affiche ta tier list
python -m tracker recent   # 20 dernieres ecoutes enregistrees
```

Lance `track` en tache de fond pendant que tu ecoutes Spotify. Une ecoute est
enregistree a chaque fois qu'un morceau se termine ou que tu changes de titre.

## Multi-appareils (Spotify Connect)

Spotify ne joue l'audio que sur **un** appareil a la fois : une ecoute est donc
unique, meme si 2 PC la captent.

- **Mets le meme `user_id`** sur tous tes appareils : edite `data/config.json`
  et donne la meme valeur partout (ex. `"user_id": "melvin"`).
- Le calcul des tiers **deduplique** automatiquement les ecoutes du meme morceau
  dont les intervalles de temps se chevauchent.

> A tester : si le PC qui ne sort pas le son affiche quand meme `PLAYING` dans
> SMTC, il faudra un "mode strict" (ne compter que l'appareil actif). Cf. probe.

## Reglages

Tout est dans `tracker/config.py` : seuils des tiers, `MIN_PLAYS`,
`POLL_INTERVAL`, allowlist d'apps, `COMPLETE_AT` (anti-skip d'outro).

## Structure

- `capture.py`  - lecture d'un instantane SMTC (+ extrapolation de position)
- `sessions.py` - reconstruction des sessions d'ecoute (max position par morceau)
- `normalize.py`- cle de dedup conservatrice
- `db.py`       - stockage SQLite (schema = contrat pour le futur backend)
- `ranking.py`  - agregation, dedup multi-appareils, attribution des tiers
- `__main__.py` - CLI

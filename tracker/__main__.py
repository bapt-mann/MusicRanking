"""CLI :  python -m tracker track | rank | recent"""
from __future__ import annotations
import argparse
import asyncio
import sys

from . import config, db
from .capture import make_capture
from .ranking import render
from .sessions import SessionTracker


async def _track():
    cfg = config.load()
    con = db.connect()
    count = 0

    def emit(play):
        nonlocal count
        db.insert_play(con, cfg, play)
        count += 1
        print(f"  + {play['percent'] * 100:3.0f}%  "
              f"{play['title_raw']} - {play['artist_raw']}")

    tracker = SessionTracker(emit)
    cap = make_capture(config.APP_ALLOWLIST)
    await cap.start()
    print(f"Tracking... (user={cfg['user_id']} device={cfg['device_id']}) "
          f"- Ctrl+C pour arreter")
    try:
        while True:
            tracker.feed(await cap.snapshot())
            await asyncio.sleep(config.POLL_INTERVAL)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        tracker.close()
        con.close()
        print(f"\nArret. {count} ecoute(s) enregistree(s) cette session.")


def _rank():
    cfg = config.load()
    con = db.connect()
    print(render(db.fetch_plays(con, cfg["user_id"])))
    con.close()


def _recent():
    cfg = config.load()
    con = db.connect()
    for r in db.fetch_plays(con, cfg["user_id"])[-20:]:
        print(f"{r['started_at']}  {r['percent'] * 100:3.0f}%  "
              f"{r['title_raw']} - {r['artist_raw']}")
    con.close()


def main():
    # Console Windows : force l'UTF-8 pour les titres stylises (phonk & co.)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(prog="tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("track", help="lance le suivi en direct")
    sub.add_parser("rank", help="affiche la tier list")
    sub.add_parser("recent", help="20 dernieres ecoutes")
    args = parser.parse_args()
    if args.cmd == "track":
        asyncio.run(_track())
    elif args.cmd == "rank":
        _rank()
    elif args.cmd == "recent":
        _recent()


if __name__ == "__main__":
    main()

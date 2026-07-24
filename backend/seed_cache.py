"""
Seed the SQLite cache in one shot so the app never hits stats.nba.com on a
user request.

The API endpoints already read exclusively through the cache layer
(`nba_client` -> `cache.cached`). The problem this script solves is *coverage*:
the engine data (roster, league Base/Advanced stats, positions) gets warmed by
the first /api/roster call, but **shot charts are only fetched lazily, one
player at a time, when someone opens that player's detail page**. Until then
(and after the entry expires) every player-detail request makes a live
`shotchartdetail` call — the slowest nba_api endpoint — which is what makes the
detail page hang on "Loading player...".

Run this once (after install, or whenever you change SEASON) and every
detail-page request is served entirely from `cache.db`:

    python seed_cache.py                # warm anything missing / expired
    python seed_cache.py --force        # clear the cache first, re-pull all
    python seed_cache.py --season 2024-25

It reuses the same cached wrappers the API uses, so it writes the exact keys the
API reads — no separate code path to drift out of sync.
"""
import argparse
import time

import cache
import config
import nba_client


def _warm(label, key, fetch):
    """Call a cached fetcher; report whether it was already cached or pulled live."""
    cached = cache.get(key) is not None
    t0 = time.time()
    try:
        fetch()
    except Exception as e:  # one failure shouldn't abort the whole seed
        print(f"  [FAIL] {label:<28} {e}")
        return False
    dt = time.time() - t0
    print(f"  [{'hit ' if cached else 'PULL'}] {label:<28} {dt:5.1f}s")
    return True


def seed(season=None, force=False):
    season = season or config.SEASON
    print(f"Seeding cache for {config.TEAM_NAME}  |  season {season}")
    print(f"cache db: {config.CACHE_DB}")
    if force:
        cache.clear()
        print("cleared existing cache (--force)\n")

    t_start = time.time()

    # 1. Engine inputs (what build_engine + the roster grid need).
    print("Engine data:")
    _warm("roster", f"roster:{config.TEAM_ID}:{season}",
          lambda: nba_client.get_roster(season=season))
    _warm("league stats (Base)", f"leaguestats:Base:{season}",
          lambda: nba_client.get_league_stats("Base", season))
    _warm("league stats (Advanced)", f"leaguestats:Advanced:{season}",
          lambda: nba_client.get_league_stats("Advanced", season))
    _warm("positions (all 30 rosters)", f"positions:{season}",
          lambda: nba_client.get_league_positions(season))

    # 2. Shot charts for every player on the roster — the part that was never
    #    seeded and forced a live call on each detail-page load.
    roster = nba_client.get_roster(season=season)
    print(f"\nShot charts ({len(roster)} players):")
    ok = 0
    for rp in roster:
        pid, name = rp["PLAYER_ID"], rp["PLAYER"]
        if _warm(name, f"shotchart:{pid}:{season}",
                 lambda pid=pid: nba_client.get_shotchart(pid, season=season)):
            ok += 1

    print(f"\nDone in {time.time() - t_start:.1f}s. "
          f"Shot charts cached: {ok}/{len(roster)}.")
    print("All /api/player/<id> requests now read from SQLite; no live nba_api "
          "calls on the detail page.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Warm the SQLite cache for the dashboard.")
    ap.add_argument("--season", default=None, help='e.g. "2025-26" (default: config.SEASON)')
    ap.add_argument("--force", action="store_true", help="clear the cache before seeding")
    args = ap.parse_args()
    seed(season=args.season, force=args.force)

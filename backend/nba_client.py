"""
Thin, cached wrappers around nba_api endpoints.

Every function returns plain JSON-serializable Python (lists of dicts / dicts)
so results can be cached in SQLite and served by Flask without pandas leaking
out. All live calls go through the cache layer with per-endpoint TTLs.
"""
import json
import time

import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (
    commonteamroster,
    leaguedashplayerstats,
    shotchartdetail,
)

import cache
import config


def _records(df):
    """DataFrame -> list[dict] with native Python types and NaN -> None."""
    return json.loads(df.to_json(orient="records"))


def _polite():
    time.sleep(config.NBA_SLEEP)


# --------------------------------------------------------------------------
# Roster
# --------------------------------------------------------------------------
def get_roster(team_id=None, season=None):
    team_id = team_id or config.TEAM_ID
    season = season or config.SEASON
    key = f"roster:{team_id}:{season}"

    def produce():
        _polite()
        df = commonteamroster.CommonTeamRoster(
            team_id=team_id, season=season, timeout=config.NBA_TIMEOUT
        ).get_data_frames()[0]
        keep = ["PLAYER_ID", "PLAYER", "NUM", "POSITION", "HEIGHT", "WEIGHT", "AGE", "EXP"]
        keep = [c for c in keep if c in df.columns]
        return _records(df[keep])

    return cache.cached(key, config.TTL_ROSTER, produce)


# --------------------------------------------------------------------------
# League-wide player stats (Base or Advanced)
# --------------------------------------------------------------------------
def get_league_stats(measure, season=None):
    """measure in {'Base', 'Advanced'} -> list of per-game player rows."""
    season = season or config.SEASON
    key = f"leaguestats:{measure}:{season}"

    def produce():
        _polite()
        df = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            per_mode_detailed="PerGame",
            measure_type_detailed_defense=measure,
            timeout=config.NBA_TIMEOUT,
        ).get_data_frames()[0]
        return _records(df)

    return cache.cached(key, config.TTL_LEAGUE_STATS, produce)


# --------------------------------------------------------------------------
# League-wide positions (pull all 30 rosters once, cached)
# --------------------------------------------------------------------------
def _position_bucket(pos):
    """Normalize NBA position strings to Guard / Forward / Big buckets."""
    if not pos:
        return "Forward"
    p = pos.upper()
    if "C" in p:          # C, F-C, C-F -> Big
        return "Big"
    if "G" in p:          # G, G-F, F-G -> Guard
        return "Guard"
    return "Forward"      # F


def get_league_positions(season=None):
    """Return {player_id(str): {'position': str, 'bucket': str}} for the league."""
    season = season or config.SEASON
    key = f"positions:{season}"

    def produce():
        out = {}
        for t in teams.get_teams():
            try:
                _polite()
                df = commonteamroster.CommonTeamRoster(
                    team_id=t["id"], season=season, timeout=config.NBA_TIMEOUT
                ).get_data_frames()[0]
            except Exception as e:  # one flaky team shouldn't kill the whole map
                print(f"[positions] {t['abbreviation']} failed: {e}")
                continue
            for _, row in df.iterrows():
                pid = str(int(row["PLAYER_ID"]))
                pos = str(row.get("POSITION") or "").strip()
                out[pid] = {"position": pos, "bucket": _position_bucket(pos)}
        print(f"[positions] mapped {len(out)} players across the league")
        return out

    return cache.cached(key, config.TTL_POSITIONS, produce)


# --------------------------------------------------------------------------
# Shot chart (per player) + league averages by zone
# --------------------------------------------------------------------------
def get_shotchart(player_id, team_id=None, season=None):
    team_id = team_id or config.TEAM_ID
    season = season or config.SEASON
    key = f"shotchart:{player_id}:{season}"

    def produce():
        _polite()
        frames = shotchartdetail.ShotChartDetail(
            team_id=team_id,
            player_id=player_id,
            season_nullable=season,
            season_type_all_star=config.SEASON_TYPE,
            context_measure_simple="FGA",
            timeout=config.NBA_TIMEOUT,
        ).get_data_frames()
        detail = frames[0][
            ["SHOT_ZONE_BASIC", "SHOT_ATTEMPTED_FLAG", "SHOT_MADE_FLAG"]
        ]
        league = frames[1][["SHOT_ZONE_BASIC", "FGA", "FGM"]]
        return {"detail": _records(detail), "league": _records(league)}

    return cache.cached(key, config.TTL_SHOTCHART, produce)


def get_team():
    t = teams.find_teams_by_full_name(config.TEAM_NAME)
    return t[0] if t else {"id": config.TEAM_ID, "full_name": config.TEAM_NAME}

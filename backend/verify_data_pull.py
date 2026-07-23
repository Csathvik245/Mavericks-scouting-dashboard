"""
Step 1 probe: confirm nba_api pulls REAL current Mavericks roster + stats.
Run this and read the printed output before building anything else.
"""
import sys
import time

from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashplayerstats

# nba_api hits stats.nba.com; it can be slow/flaky. Give it room.
TIMEOUT = 60

# Most recent COMPLETED season as of mid-2026 offseason.
SEASON = "2025-26"


def find_mavs():
    mavs = teams.find_teams_by_full_name("Dallas Mavericks")
    if not mavs:
        # fallback: search by nickname
        mavs = [t for t in teams.get_teams() if t["nickname"] == "Mavericks"]
    team = mavs[0]
    print(f"[team] {team['full_name']}  id={team['id']}  abbr={team['abbreviation']}")
    return team["id"]


def get_roster(team_id):
    print(f"\n[roster] fetching {SEASON} roster for team {team_id} ...")
    r = commonteamroster.CommonTeamRoster(
        team_id=team_id, season=SEASON, timeout=TIMEOUT
    )
    df = r.get_data_frames()[0]
    cols = [c for c in ["PLAYER", "PLAYER_ID", "NUM", "POSITION", "HEIGHT", "WEIGHT", "AGE", "EXP"] if c in df.columns]
    print(df[cols].to_string(index=False))
    print(f"[roster] {len(df)} players")
    return df


def get_league_player_stats():
    print(f"\n[stats] fetching league-wide per-game player stats for {SEASON} ...")
    s = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base",
        timeout=TIMEOUT,
    )
    df = s.get_data_frames()[0]
    print(f"[stats] league rows: {len(df)}  cols: {len(df.columns)}")
    return df


def main():
    team_id = find_mavs()
    time.sleep(0.6)
    roster = get_roster(team_id)
    time.sleep(0.6)
    league = get_league_player_stats()

    # Join Mavs roster to their real stats to prove the pipeline end-to-end.
    mavs_ids = set(roster["PLAYER_ID"].tolist())
    mavs_stats = league[league["PLAYER_ID"].isin(mavs_ids)].copy()
    show = ["PLAYER_NAME", "GP", "MIN", "PTS", "REB", "AST", "FG_PCT", "FG3_PCT", "FT_PCT", "TOV", "PLUS_MINUS"]
    show = [c for c in show if c in mavs_stats.columns]
    mavs_stats = mavs_stats.sort_values("MIN", ascending=False)
    print(f"\n[mavs stats] {len(mavs_stats)} Mavericks players matched to real {SEASON} stats:")
    print(mavs_stats[show].to_string(index=False))

    if len(mavs_stats) == 0:
        print("\n!!! NO MAVS STATS MATCHED — investigate season/roster mismatch.")
        sys.exit(1)
    print("\n[OK] Step 1 confirmed: real roster + real stats pulled and joined.")


if __name__ == "__main__":
    main()

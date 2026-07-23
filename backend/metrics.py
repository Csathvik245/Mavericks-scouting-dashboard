"""
Weakness engine.

Idea: for each metric we rank a Maverick against a league comparison pool of
rotation players and measure how far into the "bad" tail they sit
(weakness_score, 0-100). Position-sensitive metrics (rebounding, playmaking,
blocks, steals, fouls) are compared within the player's position bucket so a
center isn't dinged for a guard-like assist rate. Shooting/efficiency/ball
-security metrics are compared league-wide. Volume guards prevent false
positives on tiny samples (e.g. 4 three-point attempts all year).
"""
import bisect

import config
import nba_client

# --------------------------------------------------------------------------
# Metric catalog
# --------------------------------------------------------------------------
# direction: 'higher_better' -> low value is the weakness
#            'lower_better'  -> high value is the weakness
# source:    'base' or 'advanced' league dashboard
# fmt:       'pct01' (0-1 fraction), 'rating', 'num1', 'num2'
# position_relative: compare within Guard/Forward/Big bucket
# volume:    optional {'field','source','min'} guard on per-game volume
METRICS = [
    # --- Shooting ---------------------------------------------------------
    {"key": "fg3_pct", "label": "3-Point %", "category": "Shooting",
     "source": "base", "field": "FG3_PCT", "direction": "higher_better",
     "fmt": "pct01", "position_relative": False,
     "volume": {"field": "FG3A", "source": "base", "min": 2.0},
     "desc": "3-point accuracy (min 2.0 attempts/game to qualify)."},
    {"key": "ft_pct", "label": "Free Throw %", "category": "Shooting",
     "source": "base", "field": "FT_PCT", "direction": "higher_better",
     "fmt": "pct01", "position_relative": False,
     "volume": {"field": "FTA", "source": "base", "min": 1.5},
     "desc": "Free-throw accuracy (min 1.5 attempts/game to qualify)."},
    # --- Scoring efficiency ----------------------------------------------
    {"key": "ts_pct", "label": "True Shooting %", "category": "Efficiency",
     "source": "advanced", "field": "TS_PCT", "direction": "higher_better",
     "fmt": "pct01", "position_relative": False,
     "desc": "Points per shooting possession incl. FTs & 3s. Best single scoring-efficiency stat."},
    {"key": "efg_pct", "label": "Effective FG %", "category": "Efficiency",
     "source": "advanced", "field": "EFG_PCT", "direction": "higher_better",
     "fmt": "pct01", "position_relative": False,
     "desc": "FG% adjusted for the extra value of made 3s."},
    {"key": "ftr", "label": "Free Throw Rate", "category": "Efficiency",
     "source": "derived", "field": "FTR", "direction": "higher_better",
     "fmt": "num2", "position_relative": False,
     "volume": {"field": "FGA", "source": "base", "min": 5.0},
     "desc": "FTA / FGA — how often a player pressures the rim & draws fouls."},
    # --- Ball security ----------------------------------------------------
    {"key": "tov_pct", "label": "Turnover %", "category": "Ball Security",
     "source": "advanced", "field": "TM_TOV_PCT", "direction": "lower_better",
     "fmt": "pct100", "position_relative": False,
     "desc": "Share of possessions ending in a turnover. Lower is better."},
    {"key": "ast_to", "label": "Assist / Turnover", "category": "Ball Security",
     "source": "advanced", "field": "AST_TO", "direction": "higher_better",
     "fmt": "num2", "position_relative": True,
     "desc": "Assists per turnover, compared within position group."},
    # --- Playmaking -------------------------------------------------------
    {"key": "ast_pct", "label": "Assist %", "category": "Playmaking",
     "source": "advanced", "field": "AST_PCT", "direction": "higher_better",
     "fmt": "pct01", "position_relative": True,
     "desc": "Share of teammate FGs a player assists while on court (position-relative)."},
    # --- Rebounding -------------------------------------------------------
    {"key": "dreb_pct", "label": "Defensive Rebound %", "category": "Rebounding",
     "source": "advanced", "field": "DREB_PCT", "direction": "higher_better",
     "fmt": "pct01", "position_relative": True,
     "desc": "Share of available defensive rebounds grabbed (position-relative)."},
    {"key": "oreb_pct", "label": "Offensive Rebound %", "category": "Rebounding",
     "source": "advanced", "field": "OREB_PCT", "direction": "higher_better",
     "fmt": "pct01", "position_relative": True,
     "desc": "Share of available offensive rebounds grabbed (position-relative)."},
    # --- Defense / physicality -------------------------------------------
    {"key": "def_rating", "label": "Defensive Rating", "category": "Defense",
     "source": "advanced", "field": "DEF_RATING", "direction": "lower_better",
     "fmt": "rating", "position_relative": False,
     "desc": "Points allowed per 100 possessions with the player on court. Lower is better (team-context stat)."},
    {"key": "stl_rate", "label": "Steals / game", "category": "Defense",
     "source": "base", "field": "STL", "direction": "higher_better",
     "fmt": "num1", "position_relative": True,
     "desc": "Steals per game, compared within position group."},
    {"key": "blk_rate", "label": "Blocks / game", "category": "Defense",
     "source": "base", "field": "BLK", "direction": "higher_better",
     "fmt": "num1", "position_relative": True,
     "desc": "Blocks per game, compared within position group."},
    {"key": "foul_rate", "label": "Fouls / game", "category": "Defense",
     "source": "base", "field": "PF", "direction": "lower_better",
     "fmt": "num1", "position_relative": True,
     "desc": "Personal fouls per game (position-relative). Lower is better."},
]

CATEGORY_ORDER = ["Shooting", "Efficiency", "Ball Security", "Playmaking",
                  "Rebounding", "Defense"]
MIN_BUCKET_POOL = 12  # need at least this many players in a bucket to use it


# --------------------------------------------------------------------------
# Value formatting
# --------------------------------------------------------------------------
def fmt_value(v, fmt):
    if v is None:
        return "—"
    if fmt == "pct01":
        return f"{v * 100:.1f}%"
    if fmt == "pct100":          # value already in percent points (e.g. TM_TOV_PCT)
        return f"{v:.1f}%"
    if fmt == "rating":
        return f"{v:.1f}"
    if fmt == "num1":
        return f"{v:.1f}"
    if fmt == "num2":
        return f"{v:.2f}"
    return str(v)


# --------------------------------------------------------------------------
# Percentile
# --------------------------------------------------------------------------
def _percentile(sorted_vals, v):
    """Midrank percentile (0-100) of v within sorted_vals."""
    n = len(sorted_vals)
    if n == 0:
        return None
    less = bisect.bisect_left(sorted_vals, v)
    upper = bisect.bisect_right(sorted_vals, v)
    equal = upper - less
    return (less + 0.5 * equal) / n * 100.0


# --------------------------------------------------------------------------
# Engine construction
# --------------------------------------------------------------------------
def _get(row, source, field):
    return row.get(field)


def build_engine(season=None):
    """Load + merge league stats, attach positions, precompute comparison pools."""
    season = season or config.SEASON
    base = nba_client.get_league_stats("Base", season)
    adv = nba_client.get_league_stats("Advanced", season)
    positions = nba_client.get_league_positions(season)

    adv_by_id = {r["PLAYER_ID"]: r for r in adv}
    players = {}
    for b in base:
        pid = b["PLAYER_ID"]
        a = adv_by_id.get(pid, {})
        row = dict(b)
        # merge advanced-only fields
        for k, v in a.items():
            if k not in row:
                row[k] = v
        # derived: free-throw rate
        fga = b.get("FGA") or 0
        row["FTR"] = (b.get("FTA") / fga) if fga else None
        # position bucket
        info = positions.get(str(pid)) or positions.get(pid)
        row["POS_BUCKET"] = info["bucket"] if info else None
        row["POSITION"] = info["position"] if info else None
        players[pid] = row

    # Comparison pool = league rotation players.
    pool_rows = [
        r for r in players.values()
        if (r.get("MIN") or 0) >= config.POOL_MIN_MINUTES
        and (r.get("GP") or 0) >= config.POOL_MIN_GAMES
    ]

    # Precompute sorted value arrays per metric field, league-wide and per bucket.
    league_pool = {}
    bucket_pool = {"Guard": {}, "Forward": {}, "Big": {}}
    fields = {(m["field"]) for m in METRICS}
    for field in fields:
        vals = [r[field] for r in pool_rows if r.get(field) is not None]
        league_pool[field] = sorted(vals)
        for bucket in bucket_pool:
            bvals = [
                r[field] for r in pool_rows
                if r.get("POS_BUCKET") == bucket and r.get(field) is not None
            ]
            bucket_pool[bucket][field] = sorted(bvals)

    return {
        "season": season,
        "players": players,
        "pool_size": len(pool_rows),
        "league_pool": league_pool,
        "bucket_pool": bucket_pool,
    }


# --------------------------------------------------------------------------
# Per-player analysis
# --------------------------------------------------------------------------
def _severity(score):
    if score >= config.SEVERE_SCORE:
        return "severe"
    if score >= config.NOTABLE_SCORE:
        return "notable"
    return "mild"


def _volume_ok(player_row, metric):
    vol = metric.get("volume")
    if not vol:
        return True
    val = player_row.get(vol["field"])
    return val is not None and val >= vol["min"]


def analyze_player(engine, player_row):
    """Return every metric's standing + the subset flagged as weaknesses."""
    bucket = player_row.get("POS_BUCKET")
    breakdown = []
    weaknesses = []

    for m in METRICS:
        field = m["field"]
        value = player_row.get(field)
        entry = {
            "key": m["key"], "label": m["label"], "category": m["category"],
            "desc": m["desc"], "direction": m["direction"], "fmt": m["fmt"],
            "position_relative": m["position_relative"],
            "value": value, "display": fmt_value(value, m["fmt"]),
        }

        if value is None:
            entry.update({"applicable": False, "reason": "no data"})
            breakdown.append(entry)
            continue
        if not _volume_ok(player_row, m):
            vol = m["volume"]
            entry.update({"applicable": False,
                          "reason": f"below volume threshold ({vol['field']} < {vol['min']})"})
            breakdown.append(entry)
            continue

        # choose pool
        pool = None
        pool_scope = "league"
        if m["position_relative"] and bucket:
            bp = engine["bucket_pool"][bucket].get(field, [])
            if len(bp) >= MIN_BUCKET_POOL:
                pool = bp
                pool_scope = bucket.lower()
        if pool is None:
            pool = engine["league_pool"].get(field, [])

        pct = _percentile(pool, value)
        if pct is None:
            entry.update({"applicable": False, "reason": "empty comparison pool"})
            breakdown.append(entry)
            continue

        weakness_score = (100 - pct) if m["direction"] == "higher_better" else pct
        # percentile "rank" as commonly read: higher = better performance
        good_percentile = pct if m["direction"] == "higher_better" else (100 - pct)

        median = pool[len(pool) // 2] if pool else None
        entry.update({
            "applicable": True,
            "percentile": round(good_percentile, 1),
            "weakness_score": round(weakness_score, 1),
            "pool_scope": pool_scope,
            "pool_n": len(pool),
            "league_median": median,
            "league_median_display": fmt_value(median, m["fmt"]),
            "is_weakness": weakness_score >= config.WEAKNESS_FLAG_SCORE,
            "severity": _severity(weakness_score) if weakness_score >= config.WEAKNESS_FLAG_SCORE else None,
        })
        breakdown.append(entry)
        if entry["is_weakness"]:
            weaknesses.append(entry)

    weaknesses.sort(key=lambda e: e["weakness_score"], reverse=True)
    breakdown.sort(key=lambda e: (CATEGORY_ORDER.index(e["category"]), -(e.get("weakness_score") or 0)))
    return weaknesses, breakdown


def sample_flags(player_row):
    """Confidence flags for small-sample players."""
    gp = player_row.get("GP") or 0
    mn = player_row.get("MIN") or 0
    if gp < config.PLAYER_MIN_GAMES:
        return {"analyzable": False,
                "note": f"Only {gp} games played - too small a sample to analyze."}
    low = gp < config.LOW_SAMPLE_GAMES or mn < config.LOW_SAMPLE_MINUTES
    return {
        "analyzable": True,
        "low_confidence": low,
        "note": (f"Limited sample ({gp} GP, {mn:.1f} MPG) - treat with caution."
                 if low else None),
    }


# --------------------------------------------------------------------------
# Shot-zone weaknesses
# --------------------------------------------------------------------------
def shot_zone_weaknesses(player_id, team_id=None, season=None):
    data = nba_client.get_shotchart(player_id, team_id, season)
    # aggregate player shots by zone
    pz = {}
    for s in data["detail"]:
        z = s["SHOT_ZONE_BASIC"]
        agg = pz.setdefault(z, {"fga": 0, "fgm": 0})
        agg["fga"] += s.get("SHOT_ATTEMPTED_FLAG", 0) or 0
        agg["fgm"] += s.get("SHOT_MADE_FLAG", 0) or 0
    # aggregate league averages by zone
    lz = {}
    for r in data["league"]:
        z = r["SHOT_ZONE_BASIC"]
        agg = lz.setdefault(z, {"fga": 0, "fgm": 0})
        agg["fga"] += r.get("FGA", 0) or 0
        agg["fgm"] += r.get("FGM", 0) or 0

    zones = []
    for z, p in pz.items():
        if p["fga"] == 0:
            continue
        p_pct = p["fgm"] / p["fga"]
        lg = lz.get(z)
        l_pct = (lg["fgm"] / lg["fga"]) if lg and lg["fga"] else None
        deficit = (l_pct - p_pct) if l_pct is not None else None
        zones.append({
            "zone": z,
            "fga": p["fga"],
            "fgm": p["fgm"],
            "fg_pct": round(p_pct, 3),
            "fg_pct_display": f"{p_pct * 100:.1f}%",
            "league_fg_pct": round(l_pct, 3) if l_pct is not None else None,
            "league_fg_pct_display": f"{l_pct * 100:.1f}%" if l_pct is not None else "—",
            "deficit": round(deficit, 3) if deficit is not None else None,
            "is_weakness": bool(
                deficit is not None
                and p["fga"] >= config.ZONE_MIN_ATTEMPTS
                and deficit >= config.ZONE_MIN_DEFICIT
            ),
        })
    # sort weakness zones first, by (deficit * volume) impact
    zones.sort(key=lambda z: (z["is_weakness"], (z["deficit"] or -1) * z["fga"]), reverse=True)
    return zones

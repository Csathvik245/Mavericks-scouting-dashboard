"""
Service layer: ties nba_client + metrics together into the shapes the API/UI
consume. The engine (merged league stats + pools) is memoized in-process so we
don't re-sort 350 players on every request; underlying data still comes from
the SQLite cache.
"""
import time

import config
import metrics
import nba_client

_engine_cache = {"season": None, "built_at": 0, "engine": None}
_ENGINE_TTL = 300  # seconds; data itself is SQLite-cached far longer


def get_engine(season=None):
    season = season or config.SEASON
    now = time.time()
    if (_engine_cache["engine"] is not None
            and _engine_cache["season"] == season
            and now - _engine_cache["built_at"] < _ENGINE_TTL):
        return _engine_cache["engine"]
    engine = metrics.build_engine(season)
    _engine_cache.update(season=season, built_at=now, engine=engine)
    return engine


HEADLINE_FIELDS = [
    ("GP", "num0"), ("MIN", "num1"), ("PTS", "num1"), ("REB", "num1"),
    ("AST", "num1"), ("FG_PCT", "pct01"), ("FG3_PCT", "pct01"),
    ("FT_PCT", "pct01"), ("TS_PCT", "pct01"), ("USG_PCT", "pct01"),
    ("PLUS_MINUS", "plus"),
]


def _headline(row):
    out = {}
    for field, fmt in HEADLINE_FIELDS:
        v = row.get(field)
        out[field] = v
        if v is None:
            disp = "—"
        elif fmt == "num0":
            disp = f"{v:.0f}"
        elif fmt == "num1":
            disp = f"{v:.1f}"
        elif fmt == "pct01":
            disp = f"{v * 100:.1f}%"
        elif fmt == "plus":
            disp = f"{v:+.1f}"
        else:
            disp = str(v)
        out[field + "_display"] = disp
    return out


def _player_meta(roster_row, engine_row=None):
    meta = {
        "player_id": roster_row["PLAYER_ID"],
        "name": roster_row["PLAYER"],
        "number": roster_row.get("NUM"),
        "roster_position": roster_row.get("POSITION"),
        "height": roster_row.get("HEIGHT"),
        "weight": roster_row.get("WEIGHT"),
        "age": roster_row.get("AGE"),
        "experience": roster_row.get("EXP"),
    }
    if engine_row:
        meta["position"] = engine_row.get("POSITION") or roster_row.get("POSITION")
        meta["position_bucket"] = engine_row.get("POS_BUCKET")
    else:
        meta["position"] = roster_row.get("POSITION")
        meta["position_bucket"] = None
    return meta


def roster_overview(season=None):
    engine = get_engine(season)
    roster = nba_client.get_roster(season=season)
    players = engine["players"]
    out = []
    for rp in roster:
        row = players.get(rp["PLAYER_ID"])
        meta = _player_meta(rp, row)
        if not row:
            out.append({**meta, "analyzable": False,
                        "status": "did not play this season",
                        "weakness_count": 0, "top_weaknesses": []})
            continue
        flags = metrics.sample_flags(row)
        entry = {**meta, "headline": _headline(row),
                 "analyzable": flags["analyzable"],
                 "low_confidence": flags.get("low_confidence", False),
                 "sample_note": flags.get("note")}
        if not flags["analyzable"]:
            entry.update({"status": flags["note"], "weakness_count": 0,
                          "top_weaknesses": []})
            out.append(entry)
            continue
        weaknesses, _ = metrics.analyze_player(engine, row)
        severe = sum(1 for w in weaknesses if w["severity"] == "severe")
        entry.update({
            "weakness_count": len(weaknesses),
            "severe_count": severe,
            "top_weaknesses": [
                {"label": w["label"], "display": w["display"],
                 "severity": w["severity"], "score": w["weakness_score"],
                 "category": w["category"]}
                for w in weaknesses[:3]
            ],
        })
        out.append(entry)

    # rank: most/most-severe weaknesses first, but analyzable before non
    out.sort(key=lambda e: (
        e["analyzable"],
        e.get("severe_count", 0),
        e.get("weakness_count", 0),
    ), reverse=True)
    return {
        "team": config.TEAM_NAME,
        "season": season or config.SEASON,
        "pool_size": engine["pool_size"],
        "players": out,
    }


def player_detail(player_id, season=None):
    engine = get_engine(season)
    roster = nba_client.get_roster(season=season)
    rp = next((r for r in roster if r["PLAYER_ID"] == player_id), None)
    row = engine["players"].get(player_id)
    if rp is None and row is None:
        return None

    roster_row = rp or {"PLAYER_ID": player_id, "PLAYER": row.get("PLAYER_NAME")}
    meta = _player_meta(roster_row, row)

    if not row:
        return {**meta, "analyzable": False,
                "status": "did not play this season"}

    flags = metrics.sample_flags(row)
    result = {
        **meta,
        "headline": _headline(row),
        "analyzable": flags["analyzable"],
        "low_confidence": flags.get("low_confidence", False),
        "sample_note": flags.get("note"),
    }
    if not flags["analyzable"]:
        result["status"] = flags["note"]
        return result

    weaknesses, breakdown = metrics.analyze_player(engine, row)
    strengths = [b for b in breakdown
                 if b.get("applicable") and (b.get("percentile") or 0) >= 80]
    strengths.sort(key=lambda b: b["percentile"], reverse=True)

    # group breakdown by category for the UI
    grouped = {}
    for b in breakdown:
        grouped.setdefault(b["category"], []).append(b)
    grouped_list = [{"category": cat, "metrics": grouped[cat]}
                    for cat in metrics.CATEGORY_ORDER if cat in grouped]

    try:
        zones = metrics.shot_zone_weaknesses(player_id, season=season)
    except Exception as e:
        zones = []
        result["shot_zone_error"] = str(e)

    result.update({
        "weaknesses": weaknesses,
        "strengths": strengths[:5],
        "breakdown": grouped_list,
        "shot_zones": zones,
    })
    return result


def team_weaknesses(season=None):
    engine = get_engine(season)
    roster = nba_client.get_roster(season=season)
    players = engine["players"]

    metric_tally = {}   # key -> {label, category, players:[...]}
    category_tally = {}
    analyzed = 0
    for rp in roster:
        row = players.get(rp["PLAYER_ID"])
        if not row:
            continue
        flags = metrics.sample_flags(row)
        if not flags["analyzable"]:
            continue
        analyzed += 1
        weaknesses, _ = metrics.analyze_player(engine, row)
        for w in weaknesses:
            m = metric_tally.setdefault(
                w["key"], {"key": w["key"], "label": w["label"],
                           "category": w["category"], "players": []})
            m["players"].append({
                "player_id": rp["PLAYER_ID"], "name": rp["PLAYER"],
                "display": w["display"], "severity": w["severity"],
                "score": w["weakness_score"],
                "low_confidence": flags.get("low_confidence", False),
            })
            category_tally[w["category"]] = category_tally.get(w["category"], 0) + 1

    metric_list = sorted(metric_tally.values(),
                         key=lambda m: (len(m["players"]),
                                        max(p["score"] for p in m["players"])),
                         reverse=True)
    for m in metric_list:
        m["count"] = len(m["players"])
        m["players"].sort(key=lambda p: p["score"], reverse=True)

    categories = sorted(
        ({"category": c, "count": n} for c, n in category_tally.items()),
        key=lambda x: x["count"], reverse=True)

    return {
        "team": config.TEAM_NAME,
        "season": season or config.SEASON,
        "players_analyzed": analyzed,
        "team_weaknesses": metric_list,
        "category_summary": categories,
    }

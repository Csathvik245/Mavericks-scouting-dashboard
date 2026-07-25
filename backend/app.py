"""
Flask API for the Mavericks Weakness Finder.

Endpoints:
  GET  /api/health              service + cache status
  GET  /api/team                team + season metadata, methodology
  GET  /api/roster              every player with a weakness summary (main grid)
  GET  /api/player/<player_id>  full weakness breakdown + shot zones for one player
  GET  /api/team-weaknesses     roster-wide aggregation of shared weak spots
  GET  /api/metrics             the metric catalog (methodology reference)
  POST /api/refresh             clear the cache (force fresh nba_api pull)
"""
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

import cache
import config
import metrics
import nba_client
import service

app = Flask(__name__)
# Restrict to the deployed frontend origin(s) via CORS_ORIGINS; defaults to "*".
CORS(app, origins=config.CORS_ORIGINS)


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "season": config.SEASON,
        "team": config.TEAM_NAME,
        "cache_backend": "sqlite",
        "cache_entries": cache.info(),
    })


@app.get("/api/team")
def team():
    t = nba_client.get_team()
    return jsonify({
        "team_id": t.get("id"),
        "team": config.TEAM_NAME,
        "abbreviation": config.TEAM_ABBR,
        "season": config.SEASON,
        "season_type": config.SEASON_TYPE,
        "methodology": {
            "pool": f"League rotation players (>= {config.POOL_MIN_MINUTES} MPG "
                    f"and >= {config.POOL_MIN_GAMES} GP).",
            "weakness_flag_score": config.WEAKNESS_FLAG_SCORE,
            "position_relative": "Rebounding, playmaking, steals, blocks and "
                                 "fouls are compared within the player's "
                                 "position group (Guard / Forward / Big).",
            "note": "Weakness score is 0-100: how far into the 'bad' tail a "
                    "player sits vs the comparison pool for that metric.",
        },
    })


@app.get("/api/roster")
def roster():
    season = request.args.get("season")
    return jsonify(service.roster_overview(season))


@app.get("/api/player/<int:player_id>")
def player(player_id):
    season = request.args.get("season")
    detail = service.player_detail(player_id, season)
    if detail is None:
        return jsonify({"error": "player not found on roster"}), 404
    return jsonify(detail)


@app.get("/api/team-weaknesses")
def team_weaknesses():
    season = request.args.get("season")
    return jsonify(service.team_weaknesses(season))


@app.get("/api/metrics")
def metric_catalog():
    return jsonify({
        "categories": metrics.CATEGORY_ORDER,
        "metrics": [
            {k: m[k] for k in ("key", "label", "category", "direction",
                               "position_relative", "desc")}
            for m in metrics.METRICS
        ],
    })


@app.post("/api/refresh")
def refresh():
    # In production the cache is a committed read-only snapshot; clearing it
    # would leave the app with nothing to serve and no way to re-pull (no live
    # nba_api access). Disable the destructive refresh in offline mode.
    if config.OFFLINE:
        return jsonify({"error": "refresh disabled in offline mode"}), 403
    cache.clear()
    service._engine_cache.update(engine=None, built_at=0)
    return jsonify({"status": "cache cleared"})


if __name__ == "__main__":
    # Local dev only. In production a WSGI server runs `app:app` (see render.yaml);
    # this block does not execute under gunicorn.
    port = int(os.environ.get("PORT", "5001"))
    print(f"Mavericks Weakness Finder API  |  season {config.SEASON}"
          f"{'  |  OFFLINE' if config.OFFLINE else ''}")
    app.run(host="127.0.0.1", port=port, debug=True)

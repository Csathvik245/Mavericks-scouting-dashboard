"""Central configuration for the Mavericks Weakness Finder backend."""
import os

# Dallas Mavericks
TEAM_ID = 1610612742
TEAM_ABBR = "DAL"
TEAM_NAME = "Dallas Mavericks"

# Most recent completed season as of the 2026 offseason.
# Override with env var SEASON (format "2025-26") to run a different season.
SEASON = os.environ.get("SEASON", "2025-26")
SEASON_TYPE = "Regular Season"

# nba_api can be slow/flaky; give requests room and be polite between calls.
NBA_TIMEOUT = int(os.environ.get("NBA_TIMEOUT", "60"))
NBA_SLEEP = float(os.environ.get("NBA_SLEEP", "0.6"))  # seconds between live calls

# --- Deployment ----------------------------------------------------------
# OFFLINE_CACHE: serve strictly from the committed cache.db, never call
# stats.nba.com. REQUIRED in production (Render): stats.nba.com blocks
# datacenter IPs and Render's filesystem is ephemeral, so a live pull would
# hang. In offline mode the cache ignores TTL expiry and /api/refresh is
# disabled. Leave unset locally for the normal TTL + live-refresh behavior.
OFFLINE = os.environ.get("OFFLINE_CACHE", "").lower() in ("1", "true", "yes", "on")

# CORS_ORIGINS: comma-separated list of allowed origins for the browser
# frontend (e.g. "https://your-app.vercel.app"). Defaults to "*" so it works
# before you know the deployed URL; set it to your Vercel domain in production.
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]

# --- Cache ---------------------------------------------------------------
# User chose SQLite (no MySQL installed). Schema is portable to MySQL; see README.
CACHE_DB = os.environ.get("CACHE_DB", os.path.join(os.path.dirname(__file__), "cache.db"))
# TTLs in seconds. The default SEASON is a *completed* season, so its data is
# immutable — seed the cache once (see seed_cache.py) and it should stay valid,
# not silently re-expire and force live nba_api calls on a user request. Long
# TTL by default; drop CACHE_TTL for an in-progress season you want to refresh.
CACHE_TTL = int(os.environ.get("CACHE_TTL", str(30 * 24 * 3600)))  # 30 days
TTL_ROSTER = CACHE_TTL
TTL_LEAGUE_STATS = CACHE_TTL
TTL_POSITIONS = CACHE_TTL
TTL_SHOTCHART = CACHE_TTL

# --- Weakness engine thresholds -----------------------------------------
# Comparison pool = league "rotation" players (stable per-game samples).
POOL_MIN_MINUTES = 15.0
POOL_MIN_GAMES = 20

# A Mavericks player is analyzed only with enough sample; below this we still
# report but tag the result as low-confidence.
PLAYER_MIN_GAMES = 10
LOW_SAMPLE_GAMES = 25
LOW_SAMPLE_MINUTES = 12.0

# Weakness score (0-100) = how far into the "bad" tail a player sits.
WEAKNESS_FLAG_SCORE = 65.0     # at/above this we call it a weakness
SEVERE_SCORE = 85.0
NOTABLE_SCORE = 72.0

# Shot-zone weakness: need real volume + a real deficit vs league average.
ZONE_MIN_ATTEMPTS = 20
ZONE_MIN_DEFICIT = 0.03        # 3 percentage points below league FG% in that zone

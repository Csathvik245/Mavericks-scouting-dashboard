import { useEffect, useState } from "react";
import { api } from "./api.js";
import RosterGrid from "./components/RosterGrid.jsx";
import PlayerDetail from "./components/PlayerDetail.jsx";
import TeamWeaknesses from "./components/TeamWeaknesses.jsx";

// Minimal hash routing: #team, #player/<id>, else roster.
function parseHash() {
  const h = window.location.hash;
  const m = h.match(/^#player\/(\d+)/);
  if (m) return { view: "player", playerId: Number(m[1]) };
  if (h === "#team") return { view: "team" };
  return { view: "roster" };
}

export default function App() {
  const [route, setRoute] = useState(parseHash());
  const [team, setTeam] = useState(null);
  const [roster, setRoster] = useState(null);
  const [teamWk, setTeamWk] = useState(null);
  const [player, setPlayer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  // keep route state in sync with the URL hash (back/forward friendly)
  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // initial load
  useEffect(() => {
    Promise.all([api.team(), api.roster()])
      .then(([t, r]) => {
        setTeam(t);
        setRoster(r);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  // fetch on-demand data for the active route
  useEffect(() => {
    setError(null);
    if (route.view === "team" && !teamWk) {
      setBusy(true);
      api.teamWeaknesses().then(setTeamWk).catch((e) => setError(String(e)))
        .finally(() => setBusy(false));
    }
    if (route.view === "player" && route.playerId) {
      if (!player || player.player_id !== route.playerId) {
        setBusy(true);
        api.player(route.playerId)
          .then((p) => { setPlayer(p); window.scrollTo(0, 0); })
          .catch((e) => setError(String(e)))
          .finally(() => setBusy(false));
      }
    }
  }, [route]); // eslint-disable-line react-hooks/exhaustive-deps

  const go = (hash) => { window.location.hash = hash; };

  const activePlayer = route.view === "player";
  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
          <div className="nav-brand">
            Mavericks <span>Weakness Finder</span>
          </div>
          <div className="nav-tabs">
            <button
              className={`nav-tab ${route.view === "roster" ? "active" : ""}`}
              onClick={() => go("")}
            >
              Roster
            </button>
            <button
              className={`nav-tab ${route.view === "team" ? "active" : ""}`}
              onClick={() => go("#team")}
            >
              Team Weak Spots
            </button>
          </div>
          {team && (
            <div className="nav-season">
              {team.season} · {team.season_type}
            </div>
          )}
        </div>
      </nav>

      {error && <div className="error">Error: {error}. Is the backend running on :5001?</div>}
      {loading && <div className="loading">Loading Mavericks data…</div>}

      {!loading && !error && (
        <>
          {activePlayer ? (
            player && player.player_id === route.playerId ? (
              <PlayerDetail data={player} onBack={() => window.history.back()} />
            ) : (
              <div className="loading">Loading player…</div>
            )
          ) : route.view === "team" ? (
            teamWk ? (
              <TeamWeaknesses data={teamWk} onOpen={(id) => go(`#player/${id}`)} />
            ) : (
              <div className="loading">Loading team weaknesses…</div>
            )
          ) : (
            roster && <RosterGrid data={roster} onOpen={(id) => go(`#player/${id}`)} />
          )}
        </>
      )}

      {busy && (
        <div style={{ position: "fixed", bottom: 16, right: 16 }}>
          <span className="badge badge-muted">working…</span>
        </div>
      )}
    </>
  );
}

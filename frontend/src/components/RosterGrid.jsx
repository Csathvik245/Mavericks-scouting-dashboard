import { SEV_COLOR, Stat } from "../ui.jsx";

function PlayerCard({ p, onOpen }) {
  const h = p.headline || {};
  return (
    <div className="pcard" onClick={() => onOpen(p.player_id)}>
      <div className="pcard-top">
        <span className="pcard-num">#{p.number ?? "—"}</span>
        <span className="pcard-name">{p.name}</span>
        <span className="pcard-pos">{p.position || "—"}</span>
      </div>

      {p.analyzable ? (
        <>
          <div className="pcard-stats">
            <Stat k="PPG" v={h.PTS_display} />
            <Stat k="RPG" v={h.REB_display} />
            <Stat k="APG" v={h.AST_display} />
            <Stat k="MPG" v={h.MIN_display} />
            <Stat k="TS%" v={h.TS_PCT_display} />
          </div>

          <div className="wk-head">
            <span className="wk-count">
              {p.weakness_count} weak {p.weakness_count === 1 ? "spot" : "spots"}
            </span>
            {p.severe_count > 0 && (
              <span className="badge badge-severe">{p.severe_count} severe</span>
            )}
          </div>

          <div className="wk-list">
            {p.top_weaknesses.length === 0 && (
              <span className="small muted">No flagged weaknesses — solid across the board.</span>
            )}
            {p.top_weaknesses.map((w) => (
              <div className="wk-row" key={w.label}>
                <span className="wk-dot" style={{ background: SEV_COLOR[w.severity] }} />
                <span className="wk-label">{w.label}</span>
                <span className="wk-val">{w.display}</span>
              </div>
            ))}
          </div>

          {p.low_confidence && (
            <div className="tag-lowconf">⚠ {p.sample_note}</div>
          )}
        </>
      ) : (
        <div className="pcard-dnp">{p.status}</div>
      )}
    </div>
  );
}

export default function RosterGrid({ data, onOpen }) {
  return (
    <div className="page">
      <div className="page-head">
        <h1>{data.team} — Player Weaknesses</h1>
        <p className="page-sub">
          {data.season} regular season · each player ranked against{" "}
          {data.pool_size} league rotation players · sorted by number and
          severity of weaknesses. Click a card for the full breakdown.
        </p>
      </div>
      <div className="grid">
        {data.players.map((p) => (
          <PlayerCard key={p.player_id} p={p} onOpen={onOpen} />
        ))}
      </div>
    </div>
  );
}

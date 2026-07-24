import { PercentileStrip, StripLegend, Stat, ord } from "../ui.jsx";

function WeakRow({ w }) {
  // roster payload carries weakness_score; percentile = 100 - score.
  const pct = Math.max(0, Math.min(100, 100 - w.score));
  return (
    <div
      className="wk-row"
      title={`${w.label}: ${w.display} — ${ord(pct)} percentile (${w.severity})`}
    >
      <div className="wk-line">
        <span className="wk-label">{w.label}</span>
        <span className="wk-val">{w.display}</span>
      </div>
      <div className="wk-line2">
        <span className="wk-pct">{ord(pct)}</span>
        <PercentileStrip percentile={pct} isWeakness compact />
      </div>
    </div>
  );
}

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
              <span className="small muted">
                No flagged weaknesses — solid across the board.
              </span>
            )}
            {p.top_weaknesses.map((w) => (
              <WeakRow w={w} key={w.label} />
            ))}
          </div>

          {p.low_confidence && <div className="tag-lowconf">⚠ {p.sample_note}</div>}
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
        <p className="page-sub tight">
          {data.season} regular season · each player ranked against {data.pool_size}{" "}
          league rotation players, position-adjusted where it matters · sorted by
          count and severity of weaknesses.
        </p>
        <StripLegend className="page-legend" />
      </div>
      <div className="grid">
        {data.players.map((p) => (
          <PlayerCard key={p.player_id} p={p} onOpen={onOpen} />
        ))}
      </div>
    </div>
  );
}

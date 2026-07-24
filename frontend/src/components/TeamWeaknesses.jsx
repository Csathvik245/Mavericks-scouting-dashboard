import { SEV_COLOR } from "../ui.jsx";

const ORDER = ["severe", "notable", "mild"];

// Compact stacked bar: how the flagged players split by severity.
function SeveritySplit({ players }) {
  const counts = { severe: 0, notable: 0, mild: 0 };
  players.forEach((p) => {
    counts[p.severity] = (counts[p.severity] || 0) + 1;
  });
  const total = players.length || 1;
  const parts = ORDER.filter((s) => counts[s] > 0);
  return (
    <div className="sev-split" title={parts.map((s) => `${counts[s]} ${s}`).join(" · ")}>
      <div className="sev-bar">
        {parts.map((s) => (
          <span
            key={s}
            className="sev-seg"
            style={{ width: `${(counts[s] / total) * 100}%`, background: SEV_COLOR[s] }}
          />
        ))}
      </div>
      <div className="sev-legend">
        {counts.severe > 0 && <span className="sev-tag is-severe">{counts.severe} sev</span>}
        {counts.notable > 0 && <span className="sev-tag is-notable">{counts.notable} not</span>}
      </div>
    </div>
  );
}

export default function TeamWeaknesses({ data, onOpen }) {
  return (
    <div className="page">
      <div className="page-head">
        <h1>{data.team} — Team-wide Weak Spots</h1>
        <p className="page-sub tight">
          {data.season} · across {data.players_analyzed} analyzed players. Metrics
          where the most Mavericks land in the weakness range — the roster's shared
          soft spots, most-shared first.
        </p>
      </div>

      <div className="cat-summary">
        {data.category_summary.map((c) => (
          <div className="cat-cell" key={c.category}>
            <span className="cat-n">{c.count}</span>
            <span className="cat-c">{c.category}</span>
          </div>
        ))}
      </div>

      <div className="section">
        <div className="section-head">
          <h2>Most common weaknesses</h2>
          <span className="section-note">count · severity mix · who</span>
        </div>
        {data.team_weaknesses.map((m) => (
          <div className="tw-row" key={m.key}>
            <div className="tw-meta">
              <div className="tw-label">{m.label}</div>
              <div className="tw-cat">{m.category}</div>
            </div>
            <div className="tw-count">
              <span className="tw-num">{m.count}</span>
              <span className="tw-unit">players</span>
            </div>
            <SeveritySplit players={m.players} />
            <div className="tw-players">
              {m.players.map((p) => (
                <button
                  className={`pchip ${p.severity === "severe" ? "pchip--severe" : ""}`}
                  key={p.player_id}
                  onClick={() => onOpen(p.player_id)}
                  title={`${p.display} · ${p.severity}${
                    p.low_confidence ? " · small sample" : ""
                  }`}
                >
                  <span
                    className="pchip-dot"
                    style={{ background: SEV_COLOR[p.severity] }}
                  />
                  {p.name}
                  <span className="pchip-val">{p.display}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

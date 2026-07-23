import { SEV_COLOR } from "../ui.jsx";

export default function TeamWeaknesses({ data, onOpen }) {
  return (
    <div className="page">
      <div className="page-head">
        <h1>{data.team} — Team-wide Weak Spots</h1>
        <p className="page-sub">
          {data.season} · across {data.players_analyzed} analyzed players. Metrics
          where the most Mavericks land in the weakness range — the roster's
          shared soft spots.
        </p>
      </div>

      <div className="cat-summary">
        {data.category_summary.map((c) => (
          <div className="card" key={c.category}>
            <div className="n">{c.count}</div>
            <div className="c">{c.category}</div>
          </div>
        ))}
      </div>

      <div className="section" style={{ marginTop: 8 }}>
        <h2>Most common weaknesses</h2>
        {data.team_weaknesses.map((m) => (
          <div className="tw-row" key={m.key}>
            <div>
              <div style={{ fontWeight: 600 }}>{m.label}</div>
              <div className="small muted">{m.category}</div>
            </div>
            <div className="tw-count">
              {m.count}
              <small>players</small>
            </div>
            <div className="tw-players">
              {m.players.map((p) => (
                <span
                  className="pchip"
                  key={p.player_id}
                  onClick={() => onOpen(p.player_id)}
                  style={{
                    borderColor: SEV_COLOR[p.severity],
                    color: SEV_COLOR[p.severity],
                  }}
                  title={`${p.display} · ${p.severity}${p.low_confidence ? " · small sample" : ""}`}
                >
                  {p.name} {p.display}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

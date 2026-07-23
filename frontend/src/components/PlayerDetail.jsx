import { PercentileBar, SeverityBadge, Stat } from "../ui.jsx";

function MetricRow({ m }) {
  if (!m.applicable) {
    return (
      <div className="mrow na">
        <div className="mrow-label">{m.label}</div>
        <div className="mrow-val">{m.display}</div>
        <div className="mrow-na">not compared — {m.reason}</div>
      </div>
    );
  }
  return (
    <div className={`mrow ${m.is_weakness ? "is-weak" : ""}`}>
      <div className="mrow-label">
        {m.label} {m.is_weakness && <SeverityBadge severity={m.severity} />}
        <small>
          {m.desc}
          {m.position_relative ? " · vs " + m.pool_scope : ""}
        </small>
      </div>
      <div className="mrow-val">{m.display}</div>
      <PercentileBar percentile={m.percentile} />
      <div className="mrow-median">
        {m.percentile.toFixed(0)}th pct
        <br />
        <span className="small">lg med {m.league_median_display}</span>
      </div>
    </div>
  );
}

function ShotZones({ zones }) {
  if (!zones || zones.length === 0) return null;
  return (
    <div className="section">
      <h2>Shooting by court zone</h2>
      <p className="page-sub" style={{ marginBottom: 12 }}>
        Field-goal % per zone vs the league average for that zone. Zones flagged
        red are high-volume spots where the player shoots meaningfully below average.
      </p>
      <div className="zones">
        {zones.map((z) => {
          const below = z.deficit != null && z.deficit > 0;
          return (
            <div className={`zone ${z.is_weakness ? "is-weak" : ""}`} key={z.zone}>
              <div className="zone-name">{z.zone}</div>
              <div className="zone-nums">
                <span>
                  <b>{z.fg_pct_display}</b> ({z.fgm}/{z.fga})
                </span>
                <span className="lg">lg {z.league_fg_pct_display}</span>
              </div>
              {z.deficit != null && (
                <div className={`zone-cmp ${below ? "below" : "above"}`}>
                  {below ? "▼" : "▲"} {Math.abs(z.deficit * 100).toFixed(1)} pts{" "}
                  {below ? "below" : "above"} league
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function PlayerDetail({ data, onBack }) {
  const h = data.headline || {};
  return (
    <div className="page">
      <button className="back-btn" onClick={onBack}>
        ← Back to roster
      </button>

      <div className="detail-head">
        <div>
          <h1>
            {data.number != null && (
              <span className="muted">#{data.number} </span>
            )}
            {data.name}
          </h1>
          <div className="detail-meta">
            {data.position}
            {data.position_bucket ? ` · ${data.position_bucket}` : ""} · {data.height} ·{" "}
            {data.weight} lb · age {data.age} · {data.experience} yr exp
          </div>
        </div>
      </div>

      {!data.analyzable ? (
        <div className="note" style={{ marginTop: 18 }}>{data.status}</div>
      ) : (
        <>
          {data.low_confidence && <div className="note">⚠ {data.sample_note}</div>}

          <div className="detail-statline">
            <Stat k="GP" v={h.GP_display} />
            <Stat k="MPG" v={h.MIN_display} />
            <Stat k="PPG" v={h.PTS_display} />
            <Stat k="RPG" v={h.REB_display} />
            <Stat k="APG" v={h.AST_display} />
            <Stat k="FG%" v={h.FG_PCT_display} />
            <Stat k="3P%" v={h.FG3_PCT_display} />
            <Stat k="TS%" v={h.TS_PCT_display} />
            <Stat k="USG%" v={h.USG_PCT_display} />
            <Stat k="+/-" v={h.PLUS_MINUS_display} />
          </div>

          <div className="section">
            <h2>Key weaknesses ({data.weaknesses.length})</h2>
            {data.weaknesses.length === 0 ? (
              <p className="muted">No metric fell into the weakness range — a well-rounded profile.</p>
            ) : (
              data.weaknesses.map((m) => <MetricRow key={m.key} m={m} />)
            )}
          </div>

          {data.strengths.length > 0 && (
            <div className="section">
              <h2>Relative strengths</h2>
              <div className="chips">
                {data.strengths.map((s) => (
                  <span className="chip" key={s.key}>
                    <b>{s.label}</b> {s.display} · {s.percentile.toFixed(0)}th pct
                  </span>
                ))}
              </div>
            </div>
          )}

          <ShotZones zones={data.shot_zones} />

          <div className="section">
            <h2>Full metric breakdown</h2>
            {data.breakdown.map((cat) => (
              <div className="cat-block" key={cat.category}>
                <h3>{cat.category}</h3>
                {cat.metrics.map((m) => (
                  <MetricRow key={m.key} m={m} />
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

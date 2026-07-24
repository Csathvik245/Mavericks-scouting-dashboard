import {
  PercentileStrip,
  StripLegend,
  SeverityBadge,
  Stat,
  medianDelta,
  poolText,
  ord,
} from "../ui.jsx";

// Headline stats that map onto a graded metric, so the summary line can carry
// the same severity signal as the breakdown below it.
const STAT_METRIC = { "3P%": "fg3_pct", "TS%": "ts_pct" };

function MetricRow({ m }) {
  if (!m.applicable) {
    return (
      <div className="mrow mrow--na">
        <div className="mrow-label">
          <span className="mrow-name">{m.label}</span>
        </div>
        <div className="mrow-value">
          <span className="mrow-val">{m.display}</span>
        </div>
        <div className="mrow-dist mrow-dist--na">not compared — {m.reason}</div>
      </div>
    );
  }

  const delta = medianDelta(m);
  const scope = m.position_relative ? `vs ${m.pool_scope}` : null;

  return (
    <div className={`mrow ${m.is_weakness ? "is-weak" : ""}`}>
      <div className="mrow-label">
        <span className="mrow-name">
          {m.label}
          {m.is_weakness && <SeverityBadge severity={m.severity} />}
        </span>
        <span className="mrow-desc">
          {m.desc}
          {scope ? ` · ${scope}` : ""}
        </span>
      </div>

      <div className="mrow-value">
        <span className="mrow-val">{m.display}</span>
        {delta && (
          <span
            className={`mrow-delta ${
              m.is_weakness ? `is-${m.severity}` : delta.worse ? "" : "is-ok"
            }`}
          >
            {delta.below ? "▼" : "▲"} {delta.mag} vs med
          </span>
        )}
      </div>

      <div className="mrow-dist">
        <PercentileStrip percentile={m.percentile} isWeakness={m.is_weakness} />
        <div className="mrow-caption">
          <span className="mrow-pct">{ord(m.percentile)}</span> pctile · vs{" "}
          {poolText(m)} · med {m.league_median_display}
        </div>

        {/* hover reveals the full supporting detail behind the flag */}
        <div className="mrow-tip" role="tooltip">
          <div className="tip-head">{m.label}</div>
          <dl className="tip-grid">
            <dt>Percentile</dt>
            <dd>
              {ord(m.percentile)} of {poolText(m)}
            </dd>
            <dt>This player</dt>
            <dd>{m.display}</dd>
            <dt>League median</dt>
            <dd>
              {m.league_median_display}
              {delta && (
                <span className="tip-gap">
                  {" "}
                  ({delta.worse ? "−" : "+"}
                  {delta.mag})
                </span>
              )}
            </dd>
            <dt>Compared</dt>
            <dd>
              {m.position_relative
                ? `within ${m.pool_scope}s`
                : "league-wide"}
            </dd>
            {m.is_weakness && (
              <>
                <dt>Flag</dt>
                <dd className={`tip-sev is-${m.severity}`}>
                  {m.severity} · score {m.weakness_score}/100
                </dd>
              </>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
}

function ShotZones({ zones }) {
  if (!zones || zones.length === 0) return null;
  const weak = zones.filter((z) => z.is_weakness).length;
  return (
    <div className="section">
      <div className="section-head">
        <h2>Shooting by court zone</h2>
        <span className="section-note">
          {weak > 0
            ? `${weak} high-volume zone${weak > 1 ? "s" : ""} below league`
            : "no zone flagged"}
        </span>
      </div>
      <p className="page-sub tight">
        FG% per zone vs the league average for that spot. A zone is flagged only
        with real volume (20+ attempts) and a 3+ point deficit — a shot the
        defense can live with.
      </p>
      <div className="zones">
        {zones.map((z) => {
          const below = z.deficit != null && z.deficit > 0;
          return (
            <div className={`zone ${z.is_weakness ? "is-weak" : ""}`} key={z.zone}>
              <div className="zone-top">
                <span className="zone-name">{z.zone}</span>
                {z.deficit != null && (
                  <span className={`zone-cmp ${below ? "below" : "above"}`}>
                    {below ? "▼" : "▲"} {Math.abs(z.deficit * 100).toFixed(1)} pts
                  </span>
                )}
              </div>
              <div className="zone-nums">
                <span className="zone-pct">{z.fg_pct_display}</span>
                <span className="zone-att">
                  {z.fgm}/{z.fga} · lg {z.league_fg_pct_display}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function PlayerDetail({ data, onBack }) {
  const h = data.headline || {};

  // index breakdown metrics so the headline line can flag graded stats
  const byKey = {};
  (data.breakdown || []).forEach((cat) =>
    cat.metrics.forEach((m) => {
      byKey[m.key] = m;
    })
  );
  const flagFor = (label) => {
    const m = byKey[STAT_METRIC[label]];
    return m && m.applicable && m.is_weakness ? m.severity : null;
  };

  return (
    <div className="page">
      <button className="back-btn" onClick={onBack}>
        ← Back to roster
      </button>

      <div className="detail-head">
        <div>
          <h1>
            {data.number != null && <span className="muted">#{data.number} </span>}
            {data.name}
          </h1>
          <div className="detail-meta">
            {data.position}
            {data.position_bucket ? ` · ${data.position_bucket}` : ""} · {data.height} ·{" "}
            {data.weight} lb · age {data.age} · {data.experience} yr exp
          </div>
        </div>
        {data.analyzable && (
          <div className="detail-verdict">
            <span className="verdict-n">{data.weaknesses.length}</span>
            <span className="verdict-l">
              flagged weakness{data.weaknesses.length === 1 ? "" : "es"}
            </span>
          </div>
        )}
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
            <Stat k="3P%" v={h.FG3_PCT_display} flag={flagFor("3P%")} />
            <Stat k="TS%" v={h.TS_PCT_display} flag={flagFor("TS%")} />
            <Stat k="USG%" v={h.USG_PCT_display} />
            <Stat k="+/-" v={h.PLUS_MINUS_display} />
          </div>

          <div className="section">
            <div className="section-head">
              <h2>Key weaknesses</h2>
              <span className="section-note">
                ranked league-wide, position-adjusted where noted
              </span>
            </div>
            {data.weaknesses.length === 0 ? (
              <p className="muted tight">
                No metric fell into the weakness range — a well-rounded profile.
              </p>
            ) : (
              <>
                <StripLegend className="section-legend" />
                {data.weaknesses.map((m) => (
                  <MetricRow key={m.key} m={m} />
                ))}
              </>
            )}
          </div>

          {data.strengths.length > 0 && (
            <div className="section">
              <h2>Relative strengths</h2>
              <div className="chips">
                {data.strengths.map((s) => (
                  <span className="chip" key={s.key}>
                    <b>{s.label}</b> {s.display}
                    <span className="chip-pct">{ord(s.percentile)}</span>
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

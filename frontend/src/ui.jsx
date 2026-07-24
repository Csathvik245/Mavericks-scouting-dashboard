// Small shared presentational helpers.

export const SEV_COLOR = {
  severe: "var(--severe)",
  notable: "var(--notable)",
  mild: "var(--mild)",
};

// Percentile break points, mirrored from backend config thresholds
// (weakness_score = 100 - percentile). These are the zones an analyst reads:
//   <=15  severe tail   |  <=28  notable tail  |  <=35  flagged
//   50 league median    |  >=80  strength territory
export const P = { SEVERE: 15, NOTABLE: 28, FLAG: 35, MEDIAN: 50, STRONG: 80 };

// Proper ordinal ("3rd", "13th", "22nd") — the old UI printed "3th"/"22th".
export function ord(n) {
  n = Math.round(n);
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

export function SeverityBadge({ severity }) {
  if (!severity) return null;
  return <span className={`badge badge-${severity}`}>{severity}</span>;
}

// Marker colour: red/amber are RESERVED for real severity. Everything else
// is neutral ink; genuine strengths get a restrained green.
function markerColor(percentile, isWeakness) {
  if (isWeakness) {
    if (percentile <= P.SEVERE) return "var(--severe)";
    if (percentile <= P.NOTABLE) return "var(--notable)";
    return "var(--mild)"; // 28-35: flagged but only mild — stays neutral grey
  }
  if (percentile >= P.STRONG) return "var(--good)";
  return "var(--ink)";
}

// Where a player sits in the league distribution for one metric: shaded
// severe/notable tails, a league-median reference line, a flag threshold,
// and a marker at the player's percentile. Replaces the plain progress bar.
export function PercentileStrip({ percentile, isWeakness = false, compact = false }) {
  if (percentile == null) return <div className="pstrip pstrip--empty" />;
  const p = Math.max(0, Math.min(100, percentile));
  const color = markerColor(p, isWeakness);
  return (
    <div className={`pstrip ${compact ? "pstrip--compact" : ""}`}>
      <div className="pstrip-track">
        <span className="pstrip-zone pstrip-zone--severe" />
        <span className="pstrip-zone pstrip-zone--notable" />
        {!compact && <span className="pstrip-zone pstrip-zone--strong" />}
      </div>
      <span className="pstrip-flag" />
      <span className="pstrip-median" />
      <span className="pstrip-marker" style={{ left: `${p}%`, "--mk": color }} />
    </div>
  );
}

// One-line key so the shaded zones and reference lines are self-explanatory.
export function StripLegend({ className = "" }) {
  return (
    <div className={`slegend ${className}`}>
      <span className="slegend-item">
        <span className="slegend-swatch sw-severe" /> severe (bottom 15%)
      </span>
      <span className="slegend-item">
        <span className="slegend-swatch sw-notable" /> notable
      </span>
      <span className="slegend-item">
        <span className="slegend-rule sr-flag" /> weakness line
      </span>
      <span className="slegend-item">
        <span className="slegend-rule sr-median" /> league median
      </span>
      <span className="slegend-item">
        <span className="slegend-dot" /> this player
      </span>
    </div>
  );
}

// Signed gap to the league median, formatted in the metric's own units.
function fmtMag(mag, fmt) {
  const a = Math.abs(mag);
  if (fmt === "pct01") return `${(a * 100).toFixed(1)} pts`;
  if (fmt === "pct100") return `${a.toFixed(1)} pts`;
  if (fmt === "num2") return a.toFixed(2);
  return a.toFixed(1); // rating, num1
}

export function medianDelta(m) {
  if (m.value == null || m.league_median == null) return null;
  const diff = m.value - m.league_median;
  const below = diff < 0;
  // "worse" = wrong side of the median for this metric's direction
  const worse = m.direction === "higher_better" ? below : !below;
  return { mag: fmtMag(diff, m.fmt), below, worse };
}

// Human description of the comparison pool for captions / tooltips.
export function poolText(m) {
  if (m.pool_scope && m.pool_scope !== "league") {
    return `${m.pool_n} ${m.pool_scope}s`;
  }
  return `${m.pool_n} rotation players`;
}

export function Stat({ k, v, flag }) {
  return (
    <div className={`stat ${flag ? `stat--flag stat--${flag}` : ""}`}>
      <div className="v">{v}</div>
      <div className="k">{k}</div>
    </div>
  );
}

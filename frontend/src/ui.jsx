// Small shared presentational helpers.

export const SEV_COLOR = {
  severe: "var(--severe)",
  notable: "var(--notable)",
  mild: "var(--mild)",
};

export function SeverityBadge({ severity }) {
  if (!severity) return null;
  return <span className={`badge badge-${severity}`}>{severity}</span>;
}

// Color a percentile (0-100, higher = better) on a restrained scale.
function pctColor(p) {
  if (p >= 66) return "var(--good)";
  if (p >= 45) return "var(--mild)";
  if (p >= 25) return "var(--notable)";
  return "var(--severe)";
}

// Horizontal bar: fill width = percentile, tick at 50 = league average.
export function PercentileBar({ percentile }) {
  if (percentile == null) return <div className="pbar" />;
  const w = Math.max(2, Math.min(100, percentile));
  return (
    <div className="pbar" title={`${percentile.toFixed(0)}th percentile vs pool`}>
      <div
        className="pbar-fill"
        style={{ width: `${w}%`, background: pctColor(percentile) }}
      />
      <div className="pbar-tick" />
    </div>
  );
}

export function Stat({ k, v }) {
  return (
    <div className="stat">
      <div className="v">{v}</div>
      <div className="k">{k}</div>
    </div>
  );
}

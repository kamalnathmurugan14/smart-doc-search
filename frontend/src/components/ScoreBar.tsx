/** One labelled score bar. `value` is the 0..1 bar length; `label` the number shown. */
export function ScoreBar({
  name,
  value,
  label,
  color,
}: {
  name: string;
  value: number;
  label: string;
  color: string;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="bar">
      <span>{name}</span>
      <div
        className="track"
        role="meter"
        aria-label={`${name} score`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="num">{label}</span>
    </div>
  );
}

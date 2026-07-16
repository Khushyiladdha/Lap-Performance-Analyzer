export function Legend({
  left = "Gained",
  right = "Time lost",
}: {
  left?: string;
  right?: string;
}) {
  return (
    <div className="legend">
      <span className="t-label" style={{ color: "var(--gain)" }}>{left}</span>
      <span className="legend__ramp" />
      <span className="t-label" style={{ color: "var(--loss-bright)" }}>{right}</span>
    </div>
  );
}

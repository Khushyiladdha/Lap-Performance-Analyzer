import { useMemo } from "react";
import { f3, type ThermalScale } from "../theme";
import type { ComparisonResponse } from "../types";

const W = 1000;
const H = 84;
const TOP = 14;
const BAR = 56;

// The gap built corner by corner. Segments telescope to the integrated total;
// the measured gap and the reconciliation band are drawn on top so the
// internal-consistency check is visible, not buried.
export function DecompositionBar({
  data,
  scale,
  active,
  onHover,
}: {
  data: ComparisonResponse;
  scale: ThermalScale;
  active: number | null;
  onHover: (n: number | null) => void;
}) {
  const R = data.reconciliation;

  const geom = useMemo(() => {
    const scaleMax = Math.max(0.05, R.integrated_gap_s * 1.06, Math.abs(R.measured_gap_s) * 1.06);
    const sx = (v: number) => 8 + (v / scaleMax) * (W - 16);
    let cum = 0;
    const segs = data.corners.map((c) => {
      const a = cum;
      const b = cum + c.magnitude_s;
      cum = b;
      return {
        n: c.corner,
        x1: sx(Math.min(a, b)),
        x2: sx(Math.max(a, b)),
        col: scale(c.magnitude_s),
      };
    });
    return { sx, segs };
  }, [data, R, scale]);

  return (
    <div className="wfall-wrap">
      <svg className="wfall" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {geom.segs.map((s) => (
          <rect
            key={s.n}
            x={s.x1}
            y={TOP}
            width={Math.max(1.5, s.x2 - s.x1)}
            height={BAR}
            fill={s.col}
            rx={1}
            opacity={active == null ? 0.92 : active === s.n ? 1 : 0.3}
            style={{ cursor: "pointer" }}
            onMouseEnter={() => onHover(s.n)}
            onMouseLeave={() => onHover(null)}
          />
        ))}
        <rect
          x={geom.sx(Math.min(R.measured_gap_s, R.integrated_gap_s))}
          y={TOP - 6}
          width={Math.abs(geom.sx(R.integrated_gap_s) - geom.sx(R.measured_gap_s))}
          height={BAR + 12}
          fill="var(--gain)"
          opacity={0.12}
        />
        <line x1={geom.sx(R.measured_gap_s)} y1={TOP - 6} x2={geom.sx(R.measured_gap_s)} y2={TOP + BAR + 6} stroke="var(--text)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
        <line x1={geom.sx(R.integrated_gap_s)} y1={TOP - 6} x2={geom.sx(R.integrated_gap_s)} y2={TOP + BAR + 6} stroke="var(--loss-strong)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      </svg>

      <div className="wfall-foot">
        <div className="stat">
          <span className="t-label">Attributed (integrated)</span>
          <span className="stat__value" style={{ fontSize: 15 }}>{f3(R.integrated_gap_s)}</span>
        </div>
        <div className="stat">
          <span className="t-label">Measured gap</span>
          <span className="stat__value" style={{ fontSize: 15 }}>{f3(R.measured_gap_s)}</span>
        </div>
        <div className="stat">
          <span className="t-label">Reconciliation error</span>
          <span className="stat__value" style={{ fontSize: 15, color: "var(--text-2)" }}>±{Math.abs(R.reconciliation_error_s).toFixed(3)}s</span>
        </div>
        <div className="stat">
          <span className="t-label">Vehicle-state cross-check</span>
          <span className="stat__value" style={{ fontSize: 15 }}>
            {pct(data.vehicle_state.lockup_delta_agreement)} lockups · {pct(data.vehicle_state.wheelspin_delta_agreement)} spins agree
          </span>
        </div>
      </div>
    </div>
  );
}

const pct = (v: number | null) => (v == null ? "—" : `${Math.round(v * 100)}%`);

import { useMemo } from "react";
import { nearestIndex, type ThermalScale } from "../theme";
import type { ComparisonResponse } from "../types";

// The signature element: the real racing line, each segment stroked by the
// time-delta at that point, with a blurred underlay for the thermal bloom.
// All sizes are derived from the track's own extent, so it renders correctly at
// any coordinate scale — F1 circuit (~10,000 units) or a student autocross (~200).
export function DeltaTrackMap({
  data,
  scale,
  active,
  onHover,
  onPin,
}: {
  data: ComparisonResponse;
  scale: ThermalScale;
  active: number | null;
  onHover: (n: number | null) => void;
  onPin?: (n: number) => void;
}) {
  const dist = data.delta_trace.distance;

  const geom = useMemo(() => {
    const { x: X, y: Y, delta: D } = data.track_map;
    const step = Math.max(1, Math.ceil(X.length / 280)); // cap at ~280 segments
    const xs: number[] = [];
    const ys: number[] = [];
    const ds: number[] = [];
    for (let i = 0; i < X.length; i += step) {
      xs.push(X[i]);
      ys.push(Y[i]);
      ds.push(D[i]);
    }

    const minX = Math.min(...X), maxX = Math.max(...X);
    const minY = Math.min(...Y), maxY = Math.max(...Y);
    const S = Math.max(maxX - minX, maxY - minY) || 1; // track extent
    const pad = 0.06 * S;
    const vb = `${minX - pad} ${-maxY - pad} ${maxX - minX + 2 * pad} ${maxY - minY + 2 * pad}`;

    const ghost =
      `M ${xs[0]} ${-ys[0]} ` +
      xs.slice(1).map((x, i) => `L ${x} ${-ys[i + 1]}`).join(" ");

    const segs = [];
    for (let i = 1; i < xs.length; i++) {
      segs.push({
        d: `M ${xs[i - 1]} ${-ys[i - 1]} L ${xs[i]} ${-ys[i]}`,
        c: scale((ds[i] + ds[i - 1]) / 2),
      });
    }

    const markers = data.corners.map((c) => {
      const i = nearestIndex(dist, c.distance);
      return { n: c.corner, x: X[i], y: -Y[i], lock: c.lockup, col: scale(c.magnitude_s) };
    });

    // everything below scales with the track extent S
    const size = {
      blur: 0.0055 * S,
      ghost: 0.011 * S,
      glow: 0.0085 * S,
      line: 0.0045 * S,
      r: 0.0055 * S,
      rLock: 0.0078 * S,
      rActive: 0.0105 * S,
      ring: 0.0092 * S,
      ringStroke: 0.0012 * S,
      markStroke: 0.0021 * S,
      markStrokeLock: 0.0032 * S,
      font: 0.014 * S,
      labelDy: 0.0155 * S,
      glowPx: 0.0012 * S,
    };

    return { vb, ghost, segs, markers, size };
  }, [data, dist, scale]);

  const z = geom.size;

  return (
    <svg className="rmap" viewBox={geom.vb} preserveAspectRatio="xMidYMid meet">
      <defs>
        <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation={z.blur} />
        </filter>
      </defs>

      <path
        d={geom.ghost}
        fill="none"
        stroke="var(--plot-grid)"
        strokeWidth={z.ghost}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      <g filter="url(#glow)" strokeLinecap="round">
        {geom.segs.map((s, i) => (
          <path key={i} d={s.d} stroke={s.c} strokeWidth={z.glow} opacity={0.5} fill="none" />
        ))}
      </g>
      <g strokeLinecap="round">
        {geom.segs.map((s, i) => (
          <path key={i} d={s.d} stroke={s.c} strokeWidth={z.line} fill="none" />
        ))}
      </g>

      <g>
        {geom.markers.map((m) => {
          const on = active === m.n;
          const r = on ? z.rActive : m.lock ? z.rLock : z.r;
          return (
            <g
              key={m.n}
              style={{
                cursor: "pointer",
                filter: on ? `drop-shadow(0 0 ${z.glowPx}px rgba(240,134,46,0.75))` : "none",
              }}
              onMouseEnter={() => onHover(m.n)}
              onMouseLeave={() => onHover(null)}
              onClick={() => onPin?.(m.n)}
            >
              <circle
                cx={m.x}
                cy={m.y}
                r={r}
                fill="var(--plot-bg)"
                stroke={m.col}
                strokeWidth={m.lock ? z.markStrokeLock : z.markStroke}
              />
              {m.lock && (
                <circle cx={m.x} cy={m.y} r={z.ring} fill="none" stroke="var(--loss)" strokeWidth={z.ringStroke} opacity={0.85} />
              )}
              <text
                x={m.x}
                y={m.y - z.labelDy}
                textAnchor="middle"
                fill={on ? "var(--loss-strong)" : "var(--text-2)"}
                fontSize={z.font}
                fontFamily="var(--font-mono)"
                fontWeight={700}
              >
                T{m.n}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

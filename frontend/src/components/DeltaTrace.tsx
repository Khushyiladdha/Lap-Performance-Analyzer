import { useMemo } from "react";
import { scaleLinear } from "d3-scale";
import { line as d3line, area as d3area } from "d3-shape";
import type { ComparisonResponse } from "../types";

const W = 1000;
const H = 220;
const PAD = 16;

// Cumulative time-delta vs distance. Non-scaling strokes keep lines crisp while
// the viewBox stretches to the container width. Y-domain is fit to this
// dataset's own delta range, so it reads correctly for any gap size.
export function DeltaTrace({
  data,
  active,
}: {
  data: ComparisonResponse;
  active: number | null;
}) {
  const t = data.delta_trace;

  const geom = useMemo(() => {
    const s = t.distance;
    const d = t.delta;
    const maxS = s[s.length - 1];
    const dMin = Math.min(...d);
    const dMax = Math.max(...d);
    const x = scaleLinear().domain([0, maxS]).range([PAD, W - PAD]);
    const y = scaleLinear().domain([dMin, dMax]).nice().range([H - PAD, PAD]);
    const pts = s.map((sv, i) => [sv, d[i]] as [number, number]);
    const linePath = d3line<[number, number]>().x((p) => x(p[0])).y((p) => y(p[1]))(pts)!;
    const areaPath = d3area<[number, number]>()
      .x((p) => x(p[0]))
      .y0(y(0))
      .y1((p) => y(p[1]))(pts)!;
    return { x, zeroY: y(0), linePath, areaPath };
  }, [t]);

  const activeCorner =
    active != null ? data.corners.find((c) => c.corner === active) : null;

  return (
    <svg className="rtrace" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--loss)" stopOpacity="0.4" />
          <stop offset="1" stopColor="var(--loss)" stopOpacity="0" />
        </linearGradient>
      </defs>

      {data.corners.map((c) => (
        <line
          key={c.corner}
          x1={geom.x(c.distance)}
          y1={PAD}
          x2={geom.x(c.distance)}
          y2={H - PAD}
          stroke="var(--plot-grid)"
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />
      ))}

      <line
        x1={PAD}
        y1={geom.zeroY}
        x2={W - PAD}
        y2={geom.zeroY}
        stroke="var(--border)"
        strokeDasharray="3 4"
        vectorEffect="non-scaling-stroke"
      />

      <path d={geom.areaPath} fill="url(#tg)" />
      <path
        d={geom.linePath}
        fill="none"
        stroke="var(--loss-strong)"
        strokeWidth={2.4}
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />

      {activeCorner && (
        <line
          x1={geom.x(activeCorner.distance)}
          y1={PAD}
          x2={geom.x(activeCorner.distance)}
          y2={H - PAD}
          stroke="var(--text)"
          strokeWidth={1}
          opacity={0.55}
          vectorEffect="non-scaling-stroke"
        />
      )}
    </svg>
  );
}

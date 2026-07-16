import { useMemo } from "react";
import { scaleLinear } from "d3-scale";
import { line as d3line, curveLinear, curveStepAfter } from "d3-shape";
import type { ComparisonResponse } from "../types";

const W = 1000, H = 130, PAD = 10;

// A single stacked telemetry channel (Speed / Throttle / Brake), reference vs
// target overlaid on a shared distance axis — the MoTeC-style stacked-trace
// view. `domain` fixes the y-axis for channels with a known physical range
// (throttle 0-100%, brake 0/1); omit it to auto-fit (speed).
export function ChannelOverlay({
  data,
  reference,
  target,
  domain,
  step,
}: {
  data: ComparisonResponse;
  reference: number[];
  target: number[];
  domain?: [number, number];
  step?: boolean;
}) {
  const geom = useMemo(() => {
    const s = data.delta_trace.distance;
    const [vMin, vMax] = domain ?? [Math.min(...reference, ...target), Math.max(...reference, ...target)];
    const x = scaleLinear().domain([0, s[s.length - 1]]).range([PAD, W - PAD]);
    const y = scaleLinear().domain([vMin, vMax]).range([H - PAD, PAD]);
    const curve = step ? curveStepAfter : curveLinear;
    const mk = (arr: number[]) => d3line<number>().x((_, i) => x(s[i])).y((v) => y(v)).curve(curve)(arr)!;
    return { x, refPath: mk(reference), tgtPath: mk(target) };
  }, [data, reference, target, domain, step]);

  return (
    <svg className="rtrace rtrace--sm" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      {data.corners.map((c) => (
        <line key={c.corner} x1={geom.x(c.distance)} y1={PAD} x2={geom.x(c.distance)} y2={H - PAD}
          stroke="var(--plot-grid)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
      ))}
      <path d={geom.refPath} fill="none" stroke="var(--text-3)" strokeWidth={1.6} vectorEffect="non-scaling-stroke" />
      <path d={geom.tgtPath} fill="none" stroke="var(--gain)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

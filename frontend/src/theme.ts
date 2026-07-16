// Thermal colour language: time loss rendered as heat.
// Positive delta (target losing time) -> warm loss ramp (--loss).
// Negative delta (target gaining) -> cool gain ramp (--gain). Neutral = graphite.
//
// The scale is built PER DATASET from its own actual delta range — a Monza gap
// of +0.9s and a Silverstone gap of +5.2s must both saturate correctly, so the
// normalisation can never be a fixed constant tuned to one sample.

type Stop = [number, [number, number, number]];

const LOSS: Stop[] = [
  [0.0, [58, 63, 73]],
  [0.12, [122, 58, 20]],
  [0.32, [196, 90, 24]],
  [0.55, [240, 134, 46]],
  [0.78, [255, 168, 77]],
  [1.0, [255, 214, 158]],
];
const GAIN: Stop[] = [
  [0.0, [58, 63, 73]],
  [0.5, [30, 92, 158]],
  [1.0, [76, 154, 255]],
];

const mix = (a: number, b: number, t: number) => a + (b - a) * t;

function ramp(stops: Stop[], f: number): string {
  const x = Math.max(0, Math.min(1, f));
  for (let i = 1; i < stops.length; i++) {
    if (x <= stops[i][0]) {
      const [f0, c0] = stops[i - 1];
      const [f1, c1] = stops[i];
      const t = (x - f0) / (f1 - f0);
      return `rgb(${(mix(c0[0], c1[0], t) | 0)},${(mix(c0[1], c1[1], t) | 0)},${(mix(c0[2], c1[2], t) | 0)})`;
    }
  }
  const c = stops[stops.length - 1][1];
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

export type ThermalScale = (d: number) => string;

/** Build a colour scale normalised to this dataset's actual loss/gain extremes. */
export function makeThermalScale(values: number[]): ThermalScale {
  let lossMax = 0.05; // floor so a near-flat dataset doesn't divide by ~0
  let gainMax = 0.05;
  for (const v of values) {
    if (v > lossMax) lossMax = v;
    if (-v > gainMax) gainMax = -v;
  }
  return (d: number) => (d >= 0 ? ramp(LOSS, d / lossMax) : ramp(GAIN, Math.min(1, -d / gainMax)));
}

/** Signed seconds, e.g. +0.219s / −0.065s (true minus glyph). */
export const f3 = (v: number): string =>
  (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(3) + "s";

export function nearestIndex(sorted: number[], value: number): number {
  let lo = 0;
  let hi = sorted.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (sorted[mid] < value) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

import { f3, type ThermalScale } from "../theme";
import type { ComparisonResponse, CornerOut } from "../types";

export function cornerLabel(c: CornerOut): string {
  if (c.cause === "time gained by target") return "Gained";
  return c.cause.replace(/\b\w/g, (m) => m.toUpperCase());
}

export function cornerPhrase(c: CornerOut): string {
  switch (c.cause) {
    case "lower apex speed":
      return `${Math.abs(c.apex_speed_delta_kmh ?? 0)} km/h slower through the apex`;
    case "late braking":
      return `braked ${c.brake_point_delta_m} m later into the corner`;
    case "early braking":
      return `braked ${Math.abs(c.brake_point_delta_m ?? 0)} m early`;
    case "time gained by target":
      return `${Math.abs(c.magnitude_s).toFixed(3)}s faster here`;
    case "unclassified":
      return "loss not explained by driver inputs — flagged, not guessed";
    default:
      return "no meaningful difference";
  }
}

export const CONFIDENCE_DOT: Record<string, string> = {
  high: "var(--ok)",
  medium: "var(--warn)",
  low: "var(--bad)",
};

// A deterministic, rule-based corrective suggestion — grounded entirely in the
// already-computed per-corner deltas, never an LLM guess. Direction matters:
// e.g. "late braking" here means the braking point that CAUSED the loss, so
// the fix is to match the earlier reference point, not to brake later still.
export function cornerRecommendation(c: CornerOut): string {
  const t = `Turn ${c.corner}`;
  switch (c.cause) {
    case "early braking": {
      const m = c.brake_point_delta_m != null ? Math.abs(c.brake_point_delta_m) : null;
      return m != null
        ? `Brake ${m} m later into ${t} to carry more entry speed.`
        : `Brake later into ${t} to carry more entry speed.`;
    }
    case "late braking": {
      const m = c.brake_point_delta_m;
      return m != null
        ? `Braking ${m} m later into ${t} cost entry stability — matching the benchmark's brake point should protect exit speed.`
        : `Match the benchmark lap's brake point into ${t} to protect exit speed.`;
    }
    case "lower apex speed": {
      const v = c.apex_speed_delta_kmh != null ? Math.abs(c.apex_speed_delta_kmh) : null;
      return v != null
        ? `Carry more minimum speed through ${t} — aim for roughly ${v} km/h higher through the apex.`
        : `Carry more minimum speed through ${t}.`;
    }
    case "delayed throttle": {
      const m = c.throttle_point_delta_m;
      return m != null
        ? `Get back on throttle earlier exiting ${t} — reapplied ${m} m later than the benchmark lap.`
        : `Get back on throttle earlier exiting ${t}.`;
    }
    case "time gained by target":
      return `No correction needed — ${t} was already a strength on this lap.`;
    case "unclassified":
      return `No clear driver-input signal explains this loss at ${t} — worth reviewing the onboard video.`;
    default:
      return `No significant difference at ${t}.`;
  }
}

export function CornerBreakdownList({
  data,
  scale,
  active,
  onHover,
  onPin,
  limit,
}: {
  data: ComparisonResponse;
  scale: ThermalScale;
  active: number | null;
  onHover: (n: number | null) => void;
  onPin?: (n: number) => void;
  limit?: number;
}) {
  let rows = [...data.corners].sort((a, b) => b.magnitude_s - a.magnitude_s);
  if (limit) rows = rows.slice(0, limit);

  return (
    <div className="corner-list">
      {rows.map((c) => {
        const col = scale(c.magnitude_s);
        const cls = "corner-row" + (active === c.corner ? " corner-row--active" : "");
        return (
          <div
            key={c.corner}
            className={cls}
            style={{ ["--seg" as string]: col } as React.CSSProperties}
            onMouseEnter={() => onHover(c.corner)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onPin?.(c.corner)}
            role={onPin ? "button" : undefined}
            tabIndex={onPin ? 0 : undefined}>
            <div className="corner-row__n">T{c.corner}</div>
            <div>
              <div className={"corner-row__cause" + (c.confidence === "low" ? " corner-row__cause--dim" : "")}>
                {cornerLabel(c)}
              </div>
              <div className="corner-row__detail">{cornerPhrase(c)}</div>
              <div className="corner-row__tags">
                {c.lockup && <span className="ctag ctag--lock">◈ Lockup</span>}
                {c.wheelspin && <span className="ctag ctag--spin">◈ Wheelspin</span>}
                {c.confidence === "low" && <span className="ctag">low confidence</span>}
                {c.confidence === "medium" && <span className="ctag">medium confidence</span>}
              </div>
            </div>
            <div className="corner-row__mag">
              <div className="corner-row__mag-v" style={{ color: col }}>{f3(c.magnitude_s)}</div>
              <div className="corner-row__mag-c">
                <span className="conf-dot" style={{ background: CONFIDENCE_DOT[c.confidence] }} />
                {c.confidence}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

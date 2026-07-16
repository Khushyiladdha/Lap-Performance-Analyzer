import { cornerLabel, cornerPhrase, cornerRecommendation } from "./CornerBreakdownList";
import { f3 } from "../theme";
import type { ComparisonResponse, CornerOut } from "../types";

function fmtLapTime(s: number): string {
  const m = Math.floor(s / 60);
  const rem = (s - m * 60).toFixed(3).padStart(6, "0");
  return `${m}:${rem}`;
}

const ASSUMPTIONS = [
  "Distance-domain comparison, not time-domain.",
  "Same car and driver assumed on both laps.",
  "Per-corner attributions inherit the global reconciliation error shown below.",
];

// Always mounted in the DOM but hidden on screen (print.css); the browser's
// Print → Save as PDF is the "export" — a plain, ink-friendly one-pager.
export function PrintReport({
  data,
  biggest,
}: {
  data: ComparisonResponse;
  biggest: CornerOut;
}) {
  const gap = data.reconciliation.measured_gap_s;
  const isSim = data.source === "sim";
  const rows = [...data.corners].sort((a, b) => b.magnitude_s - a.magnitude_s);

  return (
    <div className="print-report">
      <div className="pr-head">
        <div className="pr-title">Lap Performance Analyzer — Analysis Report</div>
        <div className="pr-meta">
          {isSim ? "Formula Student / imported telemetry" : "Formula 1 · FastF1 telemetry"}
          <br />
          Generated {new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}
        </div>
      </div>

      <div className="pr-section">
        <div className="pr-section__label">Data source</div>
        <div className="pr-kv">
          <div><span className="k">Session</span><span className="v">{data.session_id.replace(/_/g, " · ")}</span></div>
          <div><span className="k">Analysed lap</span><span className="v">L{data.target_lap} · {fmtLapTime(data.target_lap_time_s)}</span></div>
          <div><span className="k">Benchmark lap</span><span className="v">L{data.reference_lap} · {fmtLapTime(data.reference_lap_time_s)}</span></div>
        </div>
      </div>

      <div className="pr-section">
        <div className="pr-section__label">Summary</div>
        <p className="pr-narrative">
          Lap {data.target_lap} ({fmtLapTime(data.target_lap_time_s)}) was {f3(gap)} {gap >= 0 ? "slower" : "faster"} than
          the benchmark, Lap {data.reference_lap} ({fmtLapTime(data.reference_lap_time_s)}). The largest single loss came at
          Turn {biggest.corner}, where {cornerPhrase(biggest)} — flagged with {biggest.confidence} confidence.
        </p>
        {biggest.magnitude_s > 0 && (
          <p className="pr-narrative" style={{ marginTop: 8 }}>
            <b>Suggested correction (rule-based):</b> {cornerRecommendation(biggest)}
          </p>
        )}
        <div className="pr-stats" style={{ marginTop: 12 }}>
          <div><div className="pr-stat__label">Gap</div><div className="pr-stat__value">{f3(gap)}</div></div>
          <div><div className="pr-stat__label">Biggest loss</div><div className="pr-stat__value">Turn {biggest.corner}</div><div className="pr-stat__sub">{f3(biggest.magnitude_s)}</div></div>
          <div><div className="pr-stat__label">Primary cause</div><div className="pr-stat__value">{cornerLabel(biggest)}</div></div>
          <div><div className="pr-stat__label">Lockups</div><div className="pr-stat__value">{data.vehicle_state.lockups_flagged}</div></div>
          <div><div className="pr-stat__label">Wheelspins</div><div className="pr-stat__value">{data.vehicle_state.wheelspins_flagged}</div></div>
        </div>
      </div>

      <div className="pr-section">
        <div className="pr-section__label">Corner-by-corner breakdown</div>
        <table className="pr-table">
          <thead>
            <tr><th>Corner</th><th>Cause</th><th>Magnitude</th><th>Confidence</th><th>Vehicle</th></tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.corner}>
                <td>T{c.corner}</td>
                <td>{cornerLabel(c)} — {cornerPhrase(c)}</td>
                <td>{f3(c.magnitude_s)}</td>
                <td>{c.confidence}</td>
                <td>{[c.lockup && "Lockup", c.wheelspin && "Wheelspin"].filter(Boolean).join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pr-section">
        <div className="pr-section__label">Validation</div>
        <div className="pr-stats">
          <div><div className="pr-stat__label">Integrated</div><div className="pr-stat__value">{f3(data.reconciliation.integrated_gap_s)}</div></div>
          <div><div className="pr-stat__label">Measured</div><div className="pr-stat__value">{f3(data.reconciliation.measured_gap_s)}</div></div>
          <div><div className="pr-stat__label">Recon. error</div><div className="pr-stat__value">±{Math.abs(data.reconciliation.reconciliation_error_s).toFixed(3)}s</div></div>
          <div><div className="pr-stat__label">Within tolerance</div><div className="pr-stat__value">{data.reconciliation.within_tolerance ? "Yes" : "Flagged"}</div></div>
          <div><div className="pr-stat__label">Cross-check</div><div className="pr-stat__value">
            {data.vehicle_state.lockup_delta_agreement != null ? `${Math.round(data.vehicle_state.lockup_delta_agreement * 100)}%` : "—"} /{" "}
            {data.vehicle_state.wheelspin_delta_agreement != null ? `${Math.round(data.vehicle_state.wheelspin_delta_agreement * 100)}%` : "—"}
          </div></div>
        </div>
      </div>

      <div className="pr-section">
        <div className="pr-section__label">Assumptions</div>
        <ul className="pr-list">
          {ASSUMPTIONS.map((a) => <li key={a}>{a}</li>)}
          <li>{isSim ? "Vehicle-state thresholds calibrated from this session's own data." : "Comparable tyre compound and fuel load assumed."}</li>
          <li>{isSim ? "Imported datalogger telemetry only." : "Public FastF1 telemetry only — no proprietary team data."}</li>
        </ul>
      </div>

      <div className="pr-foot">
        <span>Distance-domain telemetry decomposition and causal lap analysis.</span>
        <span>Reconciliation error ±{Math.abs(data.reconciliation.reconciliation_error_s).toFixed(3)}s inherited by all per-corner figures above.</span>
      </div>
    </div>
  );
}

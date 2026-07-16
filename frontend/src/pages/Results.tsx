import { useMemo, useState } from "react";
import { ChannelOverlay } from "../components/ChannelOverlay";
import {
  CONFIDENCE_DOT,
  CornerBreakdownList,
  cornerLabel,
  cornerPhrase,
  cornerRecommendation,
} from "../components/CornerBreakdownList";
import { DecompositionBar } from "../components/DecompositionBar";
import { DeltaTrace } from "../components/DeltaTrace";
import { DeltaTrackMap } from "../components/DeltaTrackMap";
import { PrintReport } from "../components/PrintReport";
import { Badge, Button, InfoTip, Legend, Stat } from "../components/ui";
import { downloadJSON } from "../export";
import { computeAnalysisConfidence } from "../quality";
import { f3, makeThermalScale } from "../theme";
import type { ComparisonResponse } from "../types";
import { useWizard } from "../wizard/WizardContext";
import "./welcome.css";
import "./results.css";
import "./print.css";

const PIPELINE = [
  ["Telemetry", "Two laps of speed, throttle, brake, gear and track position."],
  ["Distance alignment", "Both laps resampled onto one common distance grid."],
  ["Delta analysis", "Cumulative time gained or lost, metre by metre."],
  ["Corner attribution", "Each corner's loss explained — braking, apex or throttle."],
  ["Vehicle detection", "Lockups and wheelspin flagged from the car's own data."],
];

// The engine always processes these channels, regardless of source — a fixed
// description of the pipeline's scope, not a per-request computation.
const CHANNELS_ANALYSED = ["Speed", "Throttle", "Brake", "Gear", "Engine RPM", "Track position (X/Y)", "Distance"];

const LIMITATIONS = [
  "Threshold-based cause classification can misfire on ambiguous inputs (e.g. trail-braking vs late-braking can look similar).",
  "Vehicle-state detection is a derived proxy and can false-positive on legitimate hard driving.",
  "The recommendation below is a deterministic rule applied to the primary cause — not a substitute for reviewing onboard video.",
];

function fmtLapTime(s: number): string {
  const m = Math.floor(s / 60);
  const rem = (s - m * 60).toFixed(3).padStart(6, "0");
  return `${m}:${rem}`;
}

function vehicleSummary(d: ComparisonResponse): string {
  const { lockups_flagged: l, wheelspins_flagged: w } = d.vehicle_state;
  if (l === 0 && w === 0) return "None detected";
  const parts: string[] = [];
  if (l > 0) parts.push(`${l} lockup${l > 1 ? "s" : ""}`);
  if (w > 0) parts.push(`${w} wheelspin${w > 1 ? "s" : ""}`);
  return parts.join(", ");
}

// Real, computed statistics for the narrative — never fabricated. Only
// positive-magnitude (loss) corners count toward "total deficit"; a corner
// where the target gained time doesn't add to how the loss is distributed.
function useNarrativeStats(d: ComparisonResponse) {
  return useMemo(() => {
    const lossCorners = [...d.corners].filter((c) => c.magnitude_s > 0).sort((a, b) => b.magnitude_s - a.magnitude_s);
    const totalLoss = lossCorners.reduce((s, c) => s + c.magnitude_s, 0);
    const topN = lossCorners.slice(0, lossCorners.length >= 2 ? 2 : 1);
    const topPct = totalLoss > 0 ? Math.round((topN.reduce((s, c) => s + c.magnitude_s, 0) / totalLoss) * 100) : 0;
    const topLabel = topN.map((c) => `Turn ${c.corner}`).join(" and ");
    const flaggedLoss = lossCorners.filter((c) => c.lockup || c.wheelspin).reduce((s, c) => s + c.magnitude_s, 0);
    const vehiclePct = totalLoss > 0 ? Math.round((flaggedLoss / totalLoss) * 100) : 0;
    return { totalLoss, topN, topPct, topLabel, vehiclePct };
  }, [d]);
}

export function Results() {
  const { state } = useWizard();
  const d = state.data;
  const [hovered, setHovered] = useState<number | null>(null);
  const [pinned, setPinned] = useState<number | null>(null);
  const [pipelineOpen, setPipelineOpen] = useState(false);
  const [reconOpen, setReconOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const active = hovered ?? pinned;
  const onPin = (n: number) => setPinned((p) => (p === n ? null : n));

  const narrative = useNarrativeStats(d ?? ({ corners: [] } as unknown as ComparisonResponse));

  if (!d) return null;

  const scale = useMemo(() => makeThermalScale(d.delta_trace.delta), [d]);
  const biggest = useMemo(() => [...d.corners].sort((a, b) => b.magnitude_s - a.magnitude_s)[0], [d]);
  const confidence = useMemo(() => computeAnalysisConfidence(d), [d]);
  const speedStats = useMemo(() => {
    const arr = d.delta_trace.target_speed;
    return { top: Math.max(...arr), avg: arr.reduce((a, b) => a + b, 0) / arr.length };
  }, [d]);

  const gap = d.reconciliation.measured_gap_s;
  const isSim = d.source === "sim";
  const tab = state.resultsTab;
  const t = d.delta_trace;
  const { lockups_flagged: lockN, wheelspins_flagged: spinN } = d.vehicle_state;

  const sourceLabel = isSim ? "◈ Self-recorded" : "Formula 1";
  const filename = (ext: string) =>
    `lpa-${d.session_id.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-L${d.target_lap}-vs-L${d.reference_lap}.${ext}`;

  const vehicleSentence =
    narrative.totalLoss <= 0
      ? ""
      : narrative.vehiclePct === 0
        ? " No vehicle instability was detected — the loss is entirely driving line and corner speed."
        : narrative.vehiclePct < 50
          ? ` ${vehicleSummary(d)} were also detected, though driving line and corner speed remain the larger factor.`
          : ` ${vehicleSummary(d)} were detected, accounting for a significant share (${narrative.vehiclePct}%) of the time lost.`;

  return (
    <div className="page">
      <div className="no-print">
      <div className="results__head">
        <div className="t-h1">Analysis Summary</div>
        <Badge tone="accent">{sourceLabel}</Badge>
        <div className="export-actions">
          <Button variant="ghost" size="sm" onClick={() => downloadJSON(d, filename("json"))}>Download JSON</Button>
          <Button variant="secondary" size="sm" onClick={() => window.print()}>Export report</Button>
        </div>
      </div>

      {/* Narrative answers exactly one question: why was this lap slower? */}
      <p className="narrative">
        {narrative.totalLoss > 0 ? (
          <>Lap {d.target_lap} was <b className="num">{f3(Math.abs(gap)).replace("+", "")}</b> {gap >= 0 ? "slower" : "faster"} than
          the benchmark because <b>{narrative.topLabel}</b> cost <b>{narrative.topPct}%</b> of the total deficit, primarily due to{" "}
          {cornerLabel(biggest).toLowerCase()} — flagged with <b>{biggest.confidence}</b> confidence.{vehicleSentence}</>
        ) : (
          <>Lap {d.target_lap} was <b className="num">{f3(Math.abs(gap)).replace("+", "")}</b> {gap >= 0 ? "slower" : "faster"} than
          the benchmark, Lap {d.reference_lap}.{vehicleSentence}</>
        )}
      </p>

      {biggest.magnitude_s > 0 && (
        <div className="recommendation">
          <span className="recommendation__icon">▸</span>
          <div>
            <div className="t-label" style={{ marginBottom: 4 }}>Suggested correction · rule-based</div>
            {cornerRecommendation(biggest)}
          </div>
        </div>
      )}

      <div className="summary-row">
        <div className="summary-cell">
          <Stat label="Overall result" value={`${f3(gap)}`} tone={gap >= 0 ? "loss" : "gain"} sub={gap >= 0 ? "slower" : "faster"} info="Total time difference over the lap, measured from official lap times." />
        </div>
        <div className="summary-cell">
          <Stat label="Primary reason" value={cornerLabel(biggest)} sub={`Turn ${biggest.corner}`} info="The single largest contributor to the time gap, and the driver-input signal that explains it." />
        </div>
        <div className="summary-cell">
          <Stat label="Largest loss" value={`Turn ${biggest.corner}`} sub={`${cornerLabel(biggest)} · ${f3(biggest.magnitude_s)}`} />
        </div>
        <div className="summary-cell">
          <Stat
            label="Vehicle behaviour"
            value={lockN + spinN === 0 ? "None" : `${lockN} Lockup${lockN !== 1 ? "s" : ""}`}
            sub={lockN + spinN === 0 ? "detected" : `${spinN} Wheelspin${spinN !== 1 ? "s" : ""}`}
            info="Detected from Speed, RPM, nGear and Brake — a real vehicle-behaviour signal, not driver input."
          />
        </div>
        <div className="summary-cell">
          <div className="stat">
            <div className="stat__label t-label">
              Confidence
              <InfoTip text="High: one clear signal. Medium: several agreeing signals. Low: signals conflict or the loss is unexplained by driver input." />
            </div>
            <div className="stat__value" style={{ display: "flex", alignItems: "center", gap: 7, textTransform: "capitalize" }}>
              <span className="conf-dot" style={{ width: 9, height: 9, background: CONFIDENCE_DOT[biggest.confidence] }} />
              {biggest.confidence}
            </div>
            <div className="stat__sub">on primary reason</div>
          </div>
        </div>
      </div>

      <div className="channels-row">
        <span className="t-label">Analysis scope</span>
        {CHANNELS_ANALYSED.map((c) => (
          <span key={c} className="channel-chip">✓ {c}</span>
        ))}
      </div>

      {/* --- Overview --- */}
      {tab === "overview" && (
        <div className="result-panel">
          <div className="overview-grid">
            <div className="rmap-panel">
              <div className="rmap-panel__head">
                <span className="t-h3">Track</span>
                <span className="t-label">coloured by time delta · click a corner to pin</span>
              </div>
              <DeltaTrackMap data={d} scale={scale} active={active} onHover={setHovered} onPin={onPin} />
              <div className="rmap-panel__legend"><Legend /></div>
            </div>
            <div className="panel-region" style={{ display: "flex", flexDirection: "column" }}>
              <div className="panel-region__head">
                <span className="t-h3">Top corners</span>
                <span className="t-label">by time lost</span>
              </div>
              <div className="panel-region__body" style={{ paddingTop: 4 }}>
                <CornerBreakdownList data={d} scale={scale} active={active} onHover={setHovered} onPin={onPin} limit={5} />
              </div>
            </div>
          </div>
          <div className="panel-region">
            <div className="panel-region__head">
              <span className="t-h3">Decomposition — how the gap is built</span>
              <span className="t-label">per-corner contribution telescopes to the total</span>
            </div>
            <div className="panel-region__body">
              <DecompositionBar data={d} scale={scale} active={active} onHover={setHovered} />
            </div>
          </div>
        </div>
      )}

      {/* --- Corner Analysis --- */}
      {tab === "corners" && (
        <div className="result-panel">
          <div className="panel-region">
            <div className="panel-region__head">
              <span className="t-h3">Corner-by-corner breakdown</span>
              <span className="t-label">sorted by time lost · engineer's notes · click to pin</span>
            </div>
            <div className="panel-region__body" style={{ paddingTop: 4 }}>
              <CornerBreakdownList data={d} scale={scale} active={active} onHover={setHovered} onPin={onPin} />
            </div>
          </div>
        </div>
      )}

      {/* --- Track View --- */}
      {tab === "track" && (
        <div className="result-panel">
          <div className="rmap-panel">
            <div className="rmap-panel__head">
              <span className="t-h3">Delta Track Map</span>
              <span className="t-label">racing line coloured by time delta · click a corner to pin</span>
            </div>
            <div style={{ height: 560 }}><DeltaTrackMap data={d} scale={scale} active={active} onHover={setHovered} onPin={onPin} /></div>
            <div className="rmap-panel__legend"><Legend /></div>
          </div>
        </div>
      )}

      {/* --- Telemetry --- */}
      {tab === "telemetry" && (
        <div className="result-panel">
          <div className="summary-row" style={{ marginTop: 0 }}>
            <div className="summary-cell"><Stat label="Top speed" value={`${Math.round(speedStats.top)} km/h`} /></div>
            <div className="summary-cell"><Stat label="Average speed" value={`${Math.round(speedStats.avg)} km/h`} /></div>
          </div>
          <div className="channel-stack">
            <div className="rtrace-panel">
              <div className="rtrace-panel__head">
                <span className="t-h3">Speed</span>
                <span className="t-label"><span className="legend-swatch" style={{ background: "var(--gain)" }} />analysed &nbsp; <span className="legend-swatch" style={{ background: "var(--text-3)" }} />benchmark</span>
              </div>
              <ChannelOverlay data={d} reference={t.reference_speed} target={t.target_speed} />
            </div>
            <div className="rtrace-panel">
              <div className="rtrace-panel__head"><span className="t-h3">Throttle</span><span className="t-label">0–100%</span></div>
              <ChannelOverlay data={d} reference={t.reference_throttle} target={t.target_throttle} domain={[0, 100]} />
            </div>
            <div className="rtrace-panel">
              <div className="rtrace-panel__head"><span className="t-h3">Brake</span><span className="t-label">on / off</span></div>
              <ChannelOverlay data={d} reference={t.reference_brake} target={t.target_brake} domain={[0, 1]} step />
            </div>
          </div>
          <div className="rtrace-panel">
            <div className="rtrace-panel__head">
              <span className="t-h3">Delta Trace</span>
              <span className="t-label">cumulative Δ vs distance</span>
            </div>
            <DeltaTrace data={d} active={active} />
          </div>
        </div>
      )}

      {/* --- Validation --- */}
      {tab === "validation" && (
        <div className="result-panel">
          <div className="panel-region">
            <div className="panel-region__head">
              <span className="t-h3">Analysis confidence</span>
              <span className="t-label">computed from the checks below</span>
            </div>
            <div className="panel-region__body">
              <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 16 }}>
                <div className="stat__value" style={{ fontSize: 34 }}>{confidence.score}<span style={{ fontSize: 16, color: "var(--text-3)" }}>/100</span></div>
                <Badge tone={confidence.score >= 75 ? "ok" : confidence.score >= 55 ? undefined : "loss"}>{confidence.label}</Badge>
                <InfoTip text="A transparent composite: reconciliation tightness (40 pts) + attribution confidence (40 pts) + vehicle cross-check agreement (20 pts). Not a black box — see the breakdown below." />
              </div>
              <div className="rail-kv" style={{ flexDirection: "column", gap: 8, maxWidth: 420 }}>
                {confidence.breakdown.map((b) => (
                  <div className="rail-kv__row" key={b.label}>
                    <span className="k">{b.label}</span>
                    <span className="v">{b.points}/{b.max} · {b.detail}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="panel-region">
            <button className="pipeline-toggle panel-region__collapsible-head" onClick={() => setReconOpen((o) => !o)}>
              <span>
                <span className="t-h3">Reconciliation</span>{" "}
                <Badge tone={d.reconciliation.within_tolerance ? "ok" : "loss"}>
                  {d.reconciliation.within_tolerance ? "✓ Internally consistent" : "⚠ Flagged"}
                </Badge>
              </span>
              <span>{reconOpen ? "▾" : "▸"} details</span>
            </button>
            {reconOpen && (
              <div className="panel-region__body">
                <p className="t-body" style={{ marginBottom: 18, maxWidth: 640 }}>
                  There's no external "what did the team actually do" to validate against here, so
                  credibility comes from internal mathematical consistency instead: the sum of
                  per-corner deltas should reconstruct the measured lap-time gap.
                </p>
                <div className="summary-row" style={{ marginTop: 0 }}>
                  <div className="summary-cell"><Stat label="Integrated (attributed)" value={f3(d.reconciliation.integrated_gap_s)} /></div>
                  <div className="summary-cell"><Stat label="Measured gap" value={f3(d.reconciliation.measured_gap_s)} /></div>
                  <div className="summary-cell"><Stat label="Difference" value={`±${Math.abs(d.reconciliation.reconciliation_error_s).toFixed(3)}s`} /></div>
                  <div className="summary-cell">
                    <Stat label="Within tolerance" value={d.reconciliation.within_tolerance ? "Yes" : "Flagged"}
                      tone={d.reconciliation.within_tolerance ? undefined : "loss"} />
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="panel-region">
            <div className="panel-region__head">
              <span className="t-h3">Vehicle-state cross-check</span>
              <span className="t-label">physical-realism validation</span>
            </div>
            <div className="panel-region__body">
              <p className="t-body" style={{ marginBottom: 18, maxWidth: 640 }}>
                A genuine lockup or wheelspin should coincide with local time loss. This is the
                fraction of flagged events that actually sit on a corner where time was lost —
                agreement between two independent signals, not a self-report.
              </p>
              <div className="summary-row" style={{ marginTop: 0 }}>
                <div className="summary-cell"><Stat label="Lockups flagged" value={d.vehicle_state.lockups_flagged} /></div>
                <div className="summary-cell"><Stat label="Lockup agreement" value={d.vehicle_state.lockup_delta_agreement != null ? `${Math.round(d.vehicle_state.lockup_delta_agreement * 100)}%` : "—"} /></div>
                <div className="summary-cell"><Stat label="Wheelspins flagged" value={d.vehicle_state.wheelspins_flagged} /></div>
                <div className="summary-cell"><Stat label="Wheelspin agreement" value={d.vehicle_state.wheelspin_delta_agreement != null ? `${Math.round(d.vehicle_state.wheelspin_delta_agreement * 100)}%` : "—"} /></div>
              </div>
            </div>
          </div>
        </div>
      )}

      <button className="pipeline-toggle" style={{ marginTop: 28 }} onClick={() => setPipelineOpen((o) => !o)}>
        {pipelineOpen ? "▾" : "▸"} How this was computed
      </button>
      {pipelineOpen && (
        <div className="pipeline" style={{ marginTop: 12 }}>
          {PIPELINE.map(([title, desc]) => (
            <div className="pipe-stage" key={title} style={{ animation: "none", opacity: 1 }}>
              <div className="pipe-stage__title">{title}</div>
              <div className="pipe-stage__desc">{desc}</div>
            </div>
          ))}
        </div>
      )}

      <button className="pipeline-toggle" style={{ marginTop: 10 }} onClick={() => setNotesOpen((o) => !o)}>
        {notesOpen ? "▾" : "▸"} Engineering notes
      </button>
      {notesOpen && (
        <div className="eng-notes">
          <div className="eng-notes__col">
            <div className="t-label" style={{ marginBottom: 8 }}>Limitations</div>
            <ul className="rail-list">
              {LIMITATIONS.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>
          <div className="eng-notes__col">
            <div className="t-label" style={{ marginBottom: 8 }}>Run details</div>
            <div className="rail-kv">
              <div className="rail-kv__row"><span className="k">Analysis confidence</span><span className="v">{confidence.score}/100 · {confidence.label}</span></div>
              <div className="rail-kv__row"><span className="k">Computation time</span><span className="v">{state.computeMs != null ? `${state.computeMs} ms` : "—"}</span></div>
              <div className="rail-kv__row"><span className="k">Backend</span><span className="v">FastAPI + FastF1</span></div>
            </div>
          </div>
        </div>
      )}
      </div>

      <PrintReport data={d} biggest={biggest} />
    </div>
  );
}

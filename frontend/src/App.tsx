import { useState } from "react";
import { Badge, Button, Stepper } from "./components/ui";
import { Configure, SESSION_LABEL } from "./pages/Configure";
import { ImportFlow } from "./pages/Import";
import { Results } from "./pages/Results";
import { Welcome } from "./pages/Welcome";
import { WizardProvider, useWizard, type ResultsTab } from "./wizard/WizardContext";

const CRUMB: Record<string, string> = {
  welcome: "Get started",
  configure: "Configure comparison",
  import: "Import telemetry",
  results: "Analysis",
};

const RESULT_TABS: { id: ResultsTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "corners", label: "Corner Analysis" },
  { id: "track", label: "Track View" },
  { id: "telemetry", label: "Telemetry" },
  { id: "validation", label: "Validation" },
];

function fmtLapTime(s: number): string {
  const m = Math.floor(s / 60);
  const rem = (s - m * 60).toFixed(3).padStart(6, "0");
  return `${m}:${rem}`;
}

function RailResults() {
  const { state, setResultsTab } = useWizard();
  const [assumptionsOpen, setAssumptionsOpen] = useState(false);
  const d = state.data!;
  const isSim = d.source === "sim";
  const fastestIsReference = d.reference_lap_time_s <= d.target_lap_time_s;

  return (
    <>
      <div className="rail-section">
        <div className="rail-section__label">Analysis</div>
        <nav className="rail-tabs">
          {RESULT_TABS.map((t) => (
            <button
              key={t.id}
              className={"rail-tab" + (state.resultsTab === t.id ? " rail-tab--active" : "")}
              onClick={() => setResultsTab(t.id)}
            >
              <span className="rail-tab__dot" />
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="rail-section" style={{ marginTop: 18 }}>
        <div className="rail-section__label">Data source</div>
        <div className="rail-kv">
          <div className="rail-kv__row"><span className="k">Series</span><span className="v">{isSim ? "Formula Student" : "Formula 1"}</span></div>
          {isSim ? (
            <>
              <div className="rail-kv__row"><span className="k">Session</span><span className="v" style={{ wordBreak: "break-word", textAlign: "right" }}>{d.session_id}</span></div>
              <div className="rail-kv__row"><span className="k">Driver</span><span className="v">{state.request.driver || "—"}</span></div>
              {state.simMeta?.car && <div className="rail-kv__row"><span className="k">Car</span><span className="v">{state.simMeta.car}</span></div>}
              {state.simMeta?.track && <div className="rail-kv__row"><span className="k">Track</span><span className="v">{state.simMeta.track}</span></div>}
            </>
          ) : (
            <>
              <div className="rail-kv__row"><span className="k">Event</span><span className="v" style={{ wordBreak: "break-word", textAlign: "right" }}>{state.request.year} {state.request.event}</span></div>
              <div className="rail-kv__row"><span className="k">Session</span><span className="v">{SESSION_LABEL[state.request.session] ?? state.request.session}</span></div>
              <div className="rail-kv__row"><span className="k">Driver</span><span className="v">{state.driverName ?? state.request.driver}</span></div>
            </>
          )}
          <div className="rail-kv__row"><span className="k">Benchmark lap</span><span className="v">L{d.reference_lap}{fastestIsReference ? " (fastest)" : ""} · {fmtLapTime(d.reference_lap_time_s)}</span></div>
          <div className="rail-kv__row"><span className="k">Analysed lap</span><span className="v">L{d.target_lap} · {fmtLapTime(d.target_lap_time_s)}</span></div>
          <div className="rail-kv__row"><span className="k">Telemetry source</span><span className="v">{isSim ? "Imported CSV" : "FastF1"}</span></div>
        </div>
      </div>

      <div className="rail-section" style={{ marginTop: 18 }}>
        <button className="pipeline-toggle" onClick={() => setAssumptionsOpen((o) => !o)}>
          {assumptionsOpen ? "▾" : "▸"} Assumptions
        </button>
        {assumptionsOpen && (
          <ul className="rail-list" style={{ marginTop: 10 }}>
            <li>Distance-domain comparison, not time-domain</li>
            <li>Same car and driver on both laps</li>
            {isSim
              ? <li>Vehicle-state thresholds calibrated from this session</li>
              : <li>Comparable tyre compound and fuel load assumed</li>}
            <li>{isSim ? "Imported datalogger telemetry only" : "Public FastF1 telemetry only"}</li>
          </ul>
        )}
      </div>
    </>
  );
}

function RailContext() {
  const { state } = useWizard();
  const { mode, request } = state;

  if (mode === "f1") {
    return (
      <div className="rail-kv">
        <div className="rail-kv__row"><span className="k">Event</span><span className="v">{request.event} {request.year}</span></div>
        <div className="rail-kv__row"><span className="k">Session</span><span className="v">{request.session}</span></div>
        <div className="rail-kv__row"><span className="k">Driver</span><span className="v">{request.driver}</span></div>
      </div>
    );
  }
  if (mode === "sim") {
    return <div className="rail-kv"><div className="rail-kv__row"><span className="k">Type</span><span className="v">Imported CSV</span></div></div>;
  }
  return <span className="rail-section__label">No data source selected</span>;
}

function Shell() {
  const { state, reset } = useWizard();
  const stepIndex = state.step === "welcome" ? 0 : state.step === "results" ? 2 : 1;
  const midLabel = state.mode === "sim" ? "Import lap" : "Configure";
  const modeBadge = state.mode === "f1" ? "Formula 1" : state.mode === "sim" ? "Formula Student" : null;
  const onResults = state.step === "results" && state.data;

  return (
    <div className="app-shell">
      <aside className="rail">
        <div className="rail__brand">
          <div className="rail__logo">▚ LPA</div>
          <div className="rail__title">Lap Performance Analyzer</div>
          <div className="rail__sub t-label">Telemetry decomposition</div>
        </div>

        {!onResults && <Stepper vertical steps={["Data source", midLabel, "Results"]} current={stepIndex} />}

        <div className="rail__context">
          {onResults ? <RailResults /> : <RailContext />}
        </div>

        {state.step !== "welcome" && (
          <div className="rail__foot">
            <Button variant="ghost" size="sm" onClick={reset}>New analysis</Button>
          </div>
        )}
      </aside>

      <main className="work">
        <div className="work__bar">
          <span className="work__crumb">{CRUMB[state.step]}</span>
          <span className="work__status">
            {state.loading && <span className="t-label">Running…</span>}
            {modeBadge && <Badge tone="accent">{modeBadge}</Badge>}
          </span>
        </div>
        <div className="work__body">
          {state.step === "welcome" && <Welcome />}
          {state.step === "configure" && <Configure />}
          {state.step === "import" && <ImportFlow />}
          {state.step === "results" && <Results />}
        </div>
      </main>
    </div>
  );
}

export function App() {
  return (
    <WizardProvider>
      <Shell />
    </WizardProvider>
  );
}

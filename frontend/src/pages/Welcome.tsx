import { Fragment, useState } from "react";
import { Button, Card } from "../components/ui";
import type { ComparisonRequest } from "../types";
import { useWizard } from "../wizard/WizardContext";
import "./welcome.css";

const PIPELINE = [
  ["Telemetry", "Two laps of speed, throttle, brake, gear and track position."],
  ["Distance alignment", "Both laps resampled onto one common distance grid."],
  ["Delta analysis", "Cumulative time gained or lost, metre by metre."],
  ["Corner attribution", "Each corner's loss explained — braking, apex or throttle."],
  ["Vehicle detection", "Lockups and wheelspin flagged from the car's own data."],
];

const PRESETS: { label: string; tag: string; request: ComparisonRequest }[] = [
  { label: "Monza 2023", tag: "Leclerc · Qualifying", request: { year: 2023, event: "Italian Grand Prix", session: "Q", driver: "LEC" } },
  { label: "Silverstone 2023", tag: "Hamilton · Qualifying", request: { year: 2023, event: "British Grand Prix", session: "Q", driver: "HAM" } },
];

const FlagIcon = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M5 21V4" />
    <path d="M5 4h13l-2.2 3.2L18 10.5H5" />
  </svg>
);
const TraceIcon = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M3 12h3l2.2-6 3 13 2.6-9L18 13h3" />
  </svg>
);

export function Welcome() {
  const { chooseMode, quickF1, quickSimDemo, state } = useWizard();
  const [busy, setBusy] = useState<string | null>(null);

  const run = async (id: string, fn: () => Promise<void>) => {
    setBusy(id);
    await fn();
    setBusy(null);
  };

  return (
    <div className="welcome">
      <div className="welcome__hero">
        <div className="welcome__eyebrow">Telemetry Decomposition Engine</div>
        <h1 className="t-hero">Lap Performance Analyzer</h1>
        <p className="welcome__why">
          Engineers don't just need to know a lap was slower — they need to know exactly{" "}
          <b>where the time disappeared</b>, and whether the cause was the <b>driver</b> or the{" "}
          <b>car</b>.
        </p>
        <div className="compat">
          <span className="compat__label">Compatible with</span>
          <span className="compat__items">
            <span>Formula 1</span>
            <span>Formula Student</span>
            <span>Simulator telemetry</span>
          </span>
        </div>
      </div>

      {state.error && (
        <div className="wz-error" style={{ maxWidth: 680 }}>Couldn't start: {state.error}</div>
      )}

      <div className="wsection">
        <div className="wsection__label t-label">How it works</div>
        <div className="pipeline">
          {PIPELINE.map(([title, desc], i) => (
            <Fragment key={title}>
              {i > 0 && <span className="pipe-arrow">→</span>}
              <div className="pipe-stage" style={{ animationDelay: `${i * 80}ms` }}>
                <div className="pipe-stage__n">0{i + 1}</div>
                <div className="pipe-stage__title">{title}</div>
                <div className="pipe-stage__desc">{desc}</div>
              </div>
            </Fragment>
          ))}
        </div>
      </div>

      <div className="wsection">
        <div className="wsection__label t-label">Start an analysis</div>
        <div className="entry-grid">
          <Card interactive className="entry-card" onClick={() => chooseMode("f1")}>
            <div className="entry-card__icon"><FlagIcon /></div>
            <div className="entry-card__title">Analyse Formula 1</div>
            <div className="entry-card__desc">
              Official FastF1 telemetry — pick any season, Grand Prix, session and driver.
            </div>
            <div className="entry-card__cta"><Button>Start analysis</Button></div>
          </Card>

          <Card interactive className="entry-card" onClick={() => chooseMode("sim")}>
            <div className="entry-card__icon"><TraceIcon /></div>
            <div className="entry-card__title">Analyse Formula Student</div>
            <div className="entry-card__desc">
              Upload your car's datalogger CSV and run the identical decomposition on your own lap.
            </div>
            <div className="entry-card__cta"><Button variant="secondary">Import CSV</Button></div>
          </Card>
        </div>
      </div>

      <div className="wsection">
        <div className="wsection__label t-label">Quick start — one click to results</div>
        <div className="presets">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              className="preset"
              disabled={state.loading}
              onClick={() => run(p.label, () => quickF1(p.request))}
            >
              <span className="preset__name">{busy === p.label ? "Loading…" : p.label}</span>
              <span className="preset__tag">{p.tag}</span>
              <span className="preset__go">→</span>
            </button>
          ))}
          <button className="preset" disabled={state.loading} onClick={() => run("fs", quickSimDemo)}>
            <span className="preset__name">{busy === "fs" ? "Loading…" : "Formula Student demo"}</span>
            <span className="preset__tag">sample autocross</span>
            <span className="preset__go">→</span>
          </button>
        </div>
      </div>
    </div>
  );
}

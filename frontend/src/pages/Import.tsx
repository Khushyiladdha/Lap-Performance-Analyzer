import { useMemo, useRef, useState } from "react";
import { inspectSim } from "../api";
import { Badge, Button, CheckRow, PanelRegion } from "../components/ui";
import { useWizard } from "../wizard/WizardContext";
import "./results.css";
import "./import.css";

const CHANNEL_LABELS: Record<string, string> = {
  speed: "Speed",
  throttle: "Throttle",
  brake: "Brake",
  rpm: "Engine RPM",
  gear: "Gear",
  position: "Position (X/Y)",
};

function fmtLapTime(s: number): string {
  const m = Math.floor(s / 60);
  const rem = (s - m * 60).toFixed(3).padStart(6, "0");
  return `${m}:${rem}`;
}

function TrackPreview({ x, y }: { x: number[]; y: number[] }) {
  const geom = useMemo(() => {
    if (x.length < 2) return null;
    const minX = Math.min(...x), maxX = Math.max(...x);
    const minY = Math.min(...y), maxY = Math.max(...y);
    const span = Math.max(maxX - minX, maxY - minY) || 1;
    const pad = 0.08 * span;
    const vb = `${minX - pad} ${-maxY - pad} ${maxX - minX + 2 * pad} ${maxY - minY + 2 * pad}`;
    const d = `M ${x[0]} ${-y[0]} ` + x.slice(1).map((xv, i) => `L ${xv} ${-y[i + 1]}`).join(" ");
    const strokeW = span * 0.012;
    return { vb, d, strokeW, startX: x[0], startY: -y[0], endX: x[x.length - 1], endY: -y[y.length - 1], r: span * 0.02 };
  }, [x, y]);

  if (!geom) {
    return <div className="track-preview"><span className="t-sm">No position data</span></div>;
  }
  return (
    <div className="track-preview">
      <svg viewBox={geom.vb} preserveAspectRatio="xMidYMid meet">
        <path d={geom.d} fill="none" stroke="#8891a0" strokeWidth={geom.strokeW} strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={geom.endX} cy={geom.endY} r={geom.r} fill="var(--loss)" />
        <circle cx={geom.startX} cy={geom.startY} r={geom.r * 0.7} fill="var(--gain)" />
      </svg>
    </div>
  );
}

export function ImportFlow() {
  const { state, setImport, setRequest, setSimMeta, runSim, back } = useWizard();
  const fileRef = useRef<HTMLInputElement>(null);

  const [dragOver, setDragOver] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const [inspectErr, setInspectErr] = useState<string | null>(null);
  const [driverField, setDriverField] = useState("SIM");
  const [labelField, setLabelField] = useState("IMPORTED SESSION");
  const [carField, setCarField] = useState("");
  const [trackField, setTrackField] = useState("");

  const runInspect = async (file: File) => {
    const label = file.name.replace(/\.csv$/i, "").toUpperCase().slice(0, 40) || "IMPORTED SESSION";
    setLabelField(label);
    setImport(file, null);
    setInspectErr(null);
    setInspecting(true);
    try {
      const result = await inspectSim(file, { driver: driverField, label });
      setImport(file, result);
    } catch (e) {
      setInspectErr(e instanceof Error ? e.message : "couldn't read that file");
    } finally {
      setInspecting(false);
    }
  };

  const pickFile = (f: File | null | undefined) => { if (f) runInspect(f); };

  const startOver = () => {
    setImport(null, null);
    setInspectErr(null);
  };

  const inspect = state.inspect;
  const canRun = Boolean(state.importFile && inspect && inspect.n_laps >= 2);

  return (
    <div className="page">
      <div className="t-h1">Import your lap</div>
      <p className="t-body" style={{ maxWidth: 640, marginTop: 10 }}>
        Upload a datalogger CSV — Formula Student, SAE-SUPRA, Assetto Corsa or iRacing — and run
        the identical corner-by-corner decomposition on your own telemetry.
      </p>

      {(inspectErr || state.error) && (
        <div className="wz-error">Couldn't import: {inspectErr ?? state.error}</div>
      )}

      <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 16 }}>
        <PanelRegion title="1 · Upload telemetry">
          {!state.importFile ? (
            <div
              className={"dropzone" + (dragOver ? " dropzone--over" : "")}
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                pickFile(e.dataTransfer.files?.[0]);
              }}
            >
              <svg className="dropzone__icon" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3v12" /><path d="M7 8l5-5 5 5" /><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
              </svg>
              <div className="dropzone__title">Drop a CSV here, or click to browse</div>
              <div className="dropzone__hint">speed, throttle, brake, gear, RPM, and position columns are auto-detected</div>
            </div>
          ) : (
            <>
              <div className="file-chip">
                <span className="file-chip__name">{state.importFile.name}</span>
                <span className="file-chip__meta">{(state.importFile.size / 1024).toFixed(0)} KB</span>
                <Button variant="ghost" size="sm" onClick={startOver}>Choose a different file</Button>
              </div>
              <div className="meta-fields">
                <div className="field">
                  <span className="t-label">Session label</span>
                  <input value={labelField} onChange={(e) => setLabelField(e.target.value)} maxLength={40} />
                </div>
                <div className="field">
                  <span className="t-label">Driver</span>
                  <input value={driverField} onChange={(e) => setDriverField(e.target.value)} maxLength={20} />
                </div>
                <div className="field">
                  <span className="t-label">Car <span className="t-sm" style={{ display: "inline" }}>(optional)</span></span>
                  <input value={carField} onChange={(e) => setCarField(e.target.value)} maxLength={30} placeholder="e.g. DSCE EV23" />
                </div>
                <div className="field">
                  <span className="t-label">Track <span className="t-sm" style={{ display: "inline" }}>(optional)</span></span>
                  <input value={trackField} onChange={(e) => setTrackField(e.target.value)} maxLength={30} placeholder="e.g. Autocross" />
                </div>
              </div>
            </>
          )}
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={(e) => { pickFile(e.target.files?.[0]); e.target.value = ""; }}
          />
        </PanelRegion>

        {inspecting && <div className="t-sm">Reading telemetry…</div>}

        {inspect && (
          <>
            <PanelRegion title="2 · Inspect" hint={`${inspect.n_laps} laps found`}>
              <div className="quality-summary quality-summary--ok" style={{ marginBottom: 18 }}>
                <div>✓ Imported dataset loaded — ready to inspect below.</div>
                <div className="rail-kv" style={{ marginTop: 10 }}>
                  <div className="rail-kv__row"><span className="k">Session</span><span className="v">{inspect.label}</span></div>
                  <div className="rail-kv__row"><span className="k">Driver</span><span className="v">{inspect.driver}</span></div>
                  {carField && <div className="rail-kv__row"><span className="k">Car</span><span className="v">{carField}</span></div>}
                  {trackField && <div className="rail-kv__row"><span className="k">Track</span><span className="v">{trackField}</span></div>}
                  <div className="rail-kv__row"><span className="k">Laps</span><span className="v">{inspect.n_laps}</span></div>
                  <div className="rail-kv__row"><span className="k">Channels detected</span><span className="v">{Object.values(inspect.channels).filter(Boolean).length}/{Object.keys(inspect.channels).length}</span></div>
                  <div className="rail-kv__row"><span className="k">Validated</span><span className="v">{inspect.all_ok ? "✓" : "⚠"}</span></div>
                </div>
              </div>
              <div className="inspect-grid">
                <div>
                  <div className="t-label" style={{ marginBottom: 10 }}>Laps</div>
                  <div className="lap-list">
                    {inspect.laps.map((l) => (
                      <div className="lap-row" key={l.lap_number}>
                        <span>Lap {l.lap_number}</span>
                        <span className="lap-row__time">{fmtLapTime(l.lap_time_s)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="t-label" style={{ marginTop: 16, marginBottom: 10 }}>Channels detected</div>
                  <div className="channels-grid">
                    {Object.entries(inspect.channels).map(([k, ok]) => (
                      <CheckRow key={k} ok={ok} name={CHANNEL_LABELS[k] ?? k} />
                    ))}
                  </div>
                </div>
                <div>
                  <div className="t-label" style={{ marginBottom: 10 }}>Track shape</div>
                  <TrackPreview x={inspect.track_preview.x} y={inspect.track_preview.y} />
                  <div className="t-sm" style={{ marginTop: 8 }}>
                    Start (blue) and finish (orange) should sit close together if the lap forms a closed loop.
                  </div>
                </div>
              </div>
            </PanelRegion>

            <PanelRegion title="3 · Validate data quality">
              <div className={"quality-summary " + (inspect.all_ok ? "quality-summary--ok" : "quality-summary--warn")}>
                {inspect.all_ok
                  ? "All checks passed — this telemetry is ready to analyse."
                  : "Some checks did not pass — review below before running."}
              </div>
              <div className="quality-list">
                {inspect.quality.map((c) => (
                  <CheckRow key={c.name} ok={c.ok} name={c.name} detail={c.detail} />
                ))}
              </div>
            </PanelRegion>
          </>
        )}
      </div>

      <div className="page-actions">
        <Button variant="ghost" onClick={back}>Back</Button>
        <Button
          onClick={() => {
            if (!state.importFile) return;
            // keep wizard state.request.driver in sync so the rail/Results
            // display the driver actually used for THIS run, not a stale
            // value left over from a previous Formula 1 configuration.
            setRequest({ driver: driverField.trim().toUpperCase() || "SIM" });
            setSimMeta({ car: carField, track: trackField });
            runSim(state.importFile, { driver: driverField, label: labelField });
          }}
          disabled={!canRun || state.loading}
        >
          {state.loading ? "Running…" : inspect?.all_ok === false ? "Run anyway" : "Confirm & run analysis"}
        </Button>
        {inspect && !inspect.all_ok && <Badge>quality issues found</Badge>}
      </div>
    </div>
  );
}

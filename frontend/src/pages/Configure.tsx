import { useEffect, useMemo, useState } from "react";
import { getDrivers, getEvents, getLaps } from "../api";
import { Button, InfoTip, PanelRegion, Select } from "../components/ui";
import type { DriverItem, EventItem, LapItem } from "../types";
import { useWizard } from "../wizard/WizardContext";
import "./configure.css";

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR - 2018 + 1 }, (_, i) => CURRENT_YEAR - i);
const SESSIONS = [
  { value: "Q", label: "Qualifying" },
  { value: "R", label: "Race" },
  { value: "FP1", label: "Practice 1" },
  { value: "FP2", label: "Practice 2" },
  { value: "FP3", label: "Practice 3" },
  { value: "Sprint", label: "Sprint" },
];
// Exported so Results/App can show "Qualifying" instead of the raw code "Q".
export const SESSION_LABEL: Record<string, string> = Object.fromEntries(
  SESSIONS.map((s) => [s.value, s.label]),
);

function fmtLapTime(s: number | null): string {
  if (s == null) return "no time";
  const m = Math.floor(s / 60);
  const rem = (s - m * 60).toFixed(3).padStart(6, "0");
  return `${m}:${rem}`;
}

export function Configure() {
  const { state, setRequest, setDriverName, runF1, back } = useWizard();
  const req = state.request;

  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsErr, setEventsErr] = useState<string | null>(null);

  const [drivers, setDrivers] = useState<DriverItem[] | null>(null);
  const [driversLoading, setDriversLoading] = useState(false);
  const [driversErr, setDriversErr] = useState<string | null>(null);

  const [laps, setLaps] = useState<LapItem[] | null>(null);
  const [lapsLoading, setLapsLoading] = useState(false);
  const [lapsErr, setLapsErr] = useState<string | null>(null);

  // --- cascading fetches ---
  useEffect(() => {
    let cancelled = false;
    setEvents(null);
    setEventsErr(null);
    setEventsLoading(true);
    getEvents(req.year)
      .then((evs) => !cancelled && setEvents(evs))
      .catch((e) => !cancelled && setEventsErr(e instanceof Error ? e.message : "failed to load events"))
      .finally(() => !cancelled && setEventsLoading(false));
    return () => { cancelled = true; };
  }, [req.year]);

  useEffect(() => {
    if (!req.event) { setDrivers(null); return; }
    let cancelled = false;
    setDrivers(null);
    setDriversErr(null);
    setDriversLoading(true);
    getDrivers(req.year, req.event, req.session)
      .then((d) => !cancelled && setDrivers(d))
      .catch((e) => !cancelled && setDriversErr(e instanceof Error ? e.message : "failed to load drivers"))
      .finally(() => !cancelled && setDriversLoading(false));
    return () => { cancelled = true; };
  }, [req.year, req.event, req.session]);

  useEffect(() => {
    if (!req.driver) { setLaps(null); return; }
    let cancelled = false;
    setLaps(null);
    setLapsErr(null);
    setLapsLoading(true);
    getLaps(req.year, req.event, req.session, req.driver)
      .then((l) => !cancelled && setLaps(l))
      .catch((e) => !cancelled && setLapsErr(e instanceof Error ? e.message : "failed to load laps"))
      .finally(() => !cancelled && setLapsLoading(false));
    return () => { cancelled = true; };
  }, [req.year, req.event, req.session, req.driver]);

  // auto-pick reference (fastest) + target (mid-pack) once laps arrive, unless already set.
  // A session's timed laps also include slow in-laps/out-laps and cool-down laps
  // that FastF1 still marks "accurate" (that flag only means "not deleted for a
  // track-limits infringement", not "is a genuine push lap"). Filter to laps
  // within 107% of the session's fastest time instead — the same "quicklap"
  // threshold the backend's own pick_quicklaps() uses — so the median pick lands
  // on a real flying lap, not a lap that happened to have a valid-but-slow time.
  useEffect(() => {
    if (!laps || laps.length < 2) return;
    if (req.reference_lap != null && req.target_lap != null) return;
    const byTime = (a: LapItem, b: LapItem) => (a.lap_time_s as number) - (b.lap_time_s as number);
    const withTime = laps.filter((l): l is LapItem & { lap_time_s: number } => l.lap_time_s != null).sort(byTime);
    if (withTime.length < 2) return;
    const fastest = withTime[0].lap_time_s;
    const quick = withTime.filter((l) => l.lap_time_s <= fastest * 1.07);
    const timed = quick.length >= 2 ? quick : withTime;
    setRequest({
      reference_lap: timed[0].lap_number,
      target_lap: timed[Math.floor(timed.length / 2)].lap_number,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [laps]);

  const eventOptions = useMemo(
    () => (events ?? []).map((e) => ({ value: e.name, label: e.name, sub: `Round ${e.round} · ${e.location}` })),
    [events],
  );
  const driverOptions = useMemo(
    () => (drivers ?? []).map((d) => ({ value: d.code, label: d.name, sub: d.team })),
    [drivers],
  );
  const lapOptions = useMemo(
    () => (laps ?? []).map((l) => ({
      value: String(l.lap_number),
      label: `Lap ${l.lap_number} — ${fmtLapTime(l.lap_time_s)}`,
      sub: l.is_fastest ? "fastest lap" : l.is_accurate ? "clean lap" : undefined,
    })),
    [laps],
  );

  const refLap = laps?.find((l) => l.lap_number === req.reference_lap) ?? null;
  const tgtLap = laps?.find((l) => l.lap_number === req.target_lap) ?? null;
  const canRun = Boolean(req.event && req.driver && req.reference_lap && req.target_lap);
  const err = state.error || eventsErr || driversErr || lapsErr;

  return (
    <div className="page">
      <div className="t-h1">Configure comparison</div>
      <p className="configure__intro t-body">
        Pick any season, Grand Prix, session and driver — the engine works identically for
        every event on the calendar, not just the default.
      </p>

      {err && <div className="wz-error">Couldn't load data: {err}</div>}

      <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 16 }}>
        <PanelRegion title="Session" hint="Step 1 of 2">
          <div className="cfg-grid">
            <div className="field">
              <span className="t-label">Season</span>
              <Select
                options={YEARS.map((y) => ({ value: String(y), label: String(y) }))}
                value={String(req.year)}
                onChange={(v) => { setRequest({ year: Number(v), event: "", driver: "", reference_lap: null, target_lap: null }); setDriverName(null); }}
                searchable={false}
              />
            </div>
            <div className="field">
              <span className="t-label">Grand Prix</span>
              <Select
                options={eventOptions}
                value={req.event || null}
                onChange={(v) => { setRequest({ event: v, driver: "", reference_lap: null, target_lap: null }); setDriverName(null); }}
                placeholder="Choose an event"
                loading={eventsLoading}
              />
            </div>
            <div className="field">
              <span className="t-label">Session</span>
              <Select
                options={SESSIONS}
                value={req.session}
                onChange={(v) => { setRequest({ session: v, driver: "", reference_lap: null, target_lap: null }); setDriverName(null); }}
                searchable={false}
              />
            </div>
          </div>
        </PanelRegion>

        <PanelRegion title="Driver & laps" hint="Step 2 of 2">
          <div className="field" style={{ maxWidth: 340, marginBottom: 18 }}>
            <span className="t-label">Driver</span>
            <Select
              options={driverOptions}
              value={req.driver || null}
              onChange={(v) => {
                setRequest({ driver: v, reference_lap: null, target_lap: null });
                setDriverName(drivers?.find((d) => d.code === v)?.name ?? null);
              }}
              placeholder={req.event ? "Choose a driver" : "Choose an event first"}
              disabled={!req.event}
              loading={driversLoading}
            />
          </div>

          {req.driver && (
            <>
              <div className="cfg-grid cfg-grid--2">
                <div className="field">
                  <div className="field__label">
                    <span className="t-label">Benchmark lap</span>
                    <InfoTip text="The benchmark lap — usually the fastest. Time lost or gained is measured against this lap." />
                  </div>
                  <Select
                    options={lapOptions}
                    value={req.reference_lap != null ? String(req.reference_lap) : null}
                    onChange={(v) => setRequest({ reference_lap: Number(v) })}
                    placeholder="Choose a lap"
                    loading={lapsLoading}
                  />
                </div>
                <div className="field">
                  <div className="field__label">
                    <span className="t-label">Analysed lap</span>
                    <InfoTip text="The lap being analysed — the engine explains where it gained or lost time against the benchmark lap." />
                  </div>
                  <Select
                    options={lapOptions}
                    value={req.target_lap != null ? String(req.target_lap) : null}
                    onChange={(v) => setRequest({ target_lap: Number(v) })}
                    placeholder="Choose a lap"
                    loading={lapsLoading}
                  />
                </div>
              </div>

              {refLap && tgtLap && (
                <div className="summary-line">
                  Analysing <b>Lap {tgtLap.lap_number} ({fmtLapTime(tgtLap.lap_time_s)})</b> against{" "}
                  <b>Lap {refLap.lap_number} ({fmtLapTime(refLap.lap_time_s)})</b> as the benchmark.
                </div>
              )}
            </>
          )}
        </PanelRegion>
      </div>

      <div className="page-actions">
        <Button variant="ghost" onClick={back}>Back</Button>
        <Button onClick={runF1} disabled={!canRun || state.loading}>
          {state.loading ? "Running…" : "Run analysis"}
        </Button>
      </div>
    </div>
  );
}

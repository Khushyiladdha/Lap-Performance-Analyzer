import type {
  ComparisonRequest,
  ComparisonResponse,
  DriverItem,
  EventItem,
  InspectResult,
  LapItem,
} from "./types";

// Same-origin in dev (Vite proxies /comparison to the backend); override with
// VITE_API_URL for a deployed frontend pointing at the Railway backend.
const BASE = import.meta.env.VITE_API_URL ?? "";

export async function analyze(
  req: ComparisonRequest,
): Promise<ComparisonResponse> {
  const res = await fetch(`${BASE}/comparison/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return handle(res);
}

// Stage 8: import a sim / student-logger CSV and run the identical analysis.
export async function analyzeSim(
  file: File,
  opts: { driver?: string; label?: string } = {},
): Promise<ComparisonResponse> {
  const form = new FormData();
  form.append("file", file);
  if (opts.driver) form.append("driver", opts.driver);
  form.append("label", opts.label ?? file.name.replace(/\.csv$/i, "").toUpperCase());
  const res = await fetch(`${BASE}/comparison/analyze-sim`, {
    method: "POST",
    body: form,
  });
  return handle(res);
}

// Stage 6: inspect an uploaded CSV (parse + track preview + quality checks).
// Does not run the analysis — that's a separate confirmed step.
export async function inspectSim(file: File, opts: { driver?: string; label?: string } = {}) {
  const form = new FormData();
  form.append("file", file);
  if (opts.driver) form.append("driver", opts.driver);
  if (opts.label) form.append("label", opts.label);
  const res = await fetch(`${BASE}/import/inspect`, { method: "POST", body: form });
  return handle<InspectResult>(res);
}

// ---- catalog (cascading dropdowns) ----
export async function getEvents(year: number): Promise<EventItem[]> {
  const res = await fetch(`${BASE}/catalog/events/${year}`);
  const body = await handle<{ year: number; events: EventItem[] }>(res);
  return body.events;
}

export async function getDrivers(year: number, event: string, session: string): Promise<DriverItem[]> {
  const path = `${BASE}/catalog/session/${year}/${encodeURIComponent(event)}/${session}/drivers`;
  const body = await handle<{ drivers: DriverItem[] }>(await fetch(path));
  return body.drivers;
}

export async function getLaps(
  year: number, event: string, session: string, driver: string,
): Promise<LapItem[]> {
  const path = `${BASE}/catalog/session/${year}/${encodeURIComponent(event)}/${session}/laps?driver=${encodeURIComponent(driver)}`;
  const body = await handle<{ laps: LapItem[] }>(await fetch(path));
  return body.laps;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}

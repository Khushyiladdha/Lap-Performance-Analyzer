import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import { analyze, analyzeSim } from "../api";
import type { ComparisonRequest, ComparisonResponse, InspectResult } from "../types";

export type Step = "welcome" | "configure" | "import" | "results";
export type Mode = "f1" | "sim";
export type ResultsTab = "overview" | "corners" | "track" | "telemetry" | "validation";

interface State {
  step: Step;
  mode: Mode | null;
  request: ComparisonRequest;
  driverName: string | null; // resolved full name for the F1 driver code, if known
  importFile: File | null;
  inspect: InspectResult | null;
  data: ComparisonResponse | null;
  loading: boolean;
  error: string | null;
  resultsTab: ResultsTab;
  computeMs: number | null; // real, measured wall-clock time for the last run
  simMeta: { car: string; track: string } | null; // user-provided, sim mode only
}

const DEFAULT_REQUEST: ComparisonRequest = {
  year: 2023,
  event: "Italian Grand Prix",
  session: "Q",
  driver: "LEC",
};

const initial: State = {
  step: "welcome",
  mode: null,
  request: DEFAULT_REQUEST,
  driverName: null,
  importFile: null,
  inspect: null,
  data: null,
  loading: false,
  error: null,
  resultsTab: "overview",
  computeMs: null,
  simMeta: null,
};

type Action =
  | { type: "CHOOSE_MODE"; mode: Mode }
  | { type: "PRESET"; mode: Mode; request: ComparisonRequest }
  | { type: "SET_REQUEST"; patch: Partial<ComparisonRequest> }
  | { type: "SET_DRIVER_NAME"; name: string | null }
  | { type: "SET_SIM_META"; meta: { car: string; track: string } | null }
  | { type: "SET_IMPORT"; file: File | null; inspect: InspectResult | null }
  | { type: "GO"; step: Step }
  | { type: "SET_TAB"; tab: ResultsTab }
  | { type: "RUN_START" }
  | { type: "RUN_OK"; data: ComparisonResponse; ms: number }
  | { type: "RUN_ERR"; error: string }
  | { type: "RESET" };

function reducer(s: State, a: Action): State {
  switch (a.type) {
    case "CHOOSE_MODE":
      return { ...s, mode: a.mode, step: a.mode === "f1" ? "configure" : "import", error: null };
    case "PRESET":
      // quick-start: set mode + request without navigating (RUN_OK moves to results).
      // Reset driverName/simMeta too — otherwise a resolved name or car/track left
      // over from a previous Configure/Import session would leak into this run's display.
      return { ...s, mode: a.mode, request: a.request, driverName: null, simMeta: null, error: null };
    case "SET_REQUEST":
      return { ...s, request: { ...s.request, ...a.patch } };
    case "SET_DRIVER_NAME":
      return { ...s, driverName: a.name };
    case "SET_SIM_META":
      return { ...s, simMeta: a.meta };
    case "SET_IMPORT":
      return { ...s, importFile: a.file, inspect: a.inspect };
    case "GO":
      return { ...s, step: a.step, error: null };
    case "SET_TAB":
      return { ...s, resultsTab: a.tab };
    case "RUN_START":
      return { ...s, loading: true, error: null };
    case "RUN_OK":
      return { ...s, loading: false, data: a.data, step: "results", resultsTab: "overview", computeMs: a.ms };
    case "RUN_ERR":
      return { ...s, loading: false, error: a.error };
    case "RESET":
      return initial;
    default:
      return s;
  }
}

interface WizardCtx {
  state: State;
  chooseMode: (m: Mode) => void;
  setRequest: (p: Partial<ComparisonRequest>) => void;
  setImport: (f: File | null, i: InspectResult | null) => void;
  goTo: (s: Step) => void;
  setResultsTab: (t: ResultsTab) => void;
  setDriverName: (n: string | null) => void;
  setSimMeta: (m: { car: string; track: string } | null) => void;
  back: () => void;
  reset: () => void;
  runF1: () => Promise<void>;
  runSim: (file: File, opts?: { driver?: string; label?: string }) => Promise<void>;
  quickF1: (request: ComparisonRequest) => Promise<void>;
  quickSimDemo: () => Promise<void>;
}

const Ctx = createContext<WizardCtx | null>(null);

export function WizardProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initial);

  const chooseMode = useCallback((m: Mode) => dispatch({ type: "CHOOSE_MODE", mode: m }), []);
  const setRequest = useCallback((p: Partial<ComparisonRequest>) => dispatch({ type: "SET_REQUEST", patch: p }), []);
  const setImport = useCallback((f: File | null, i: InspectResult | null) => dispatch({ type: "SET_IMPORT", file: f, inspect: i }), []);
  const goTo = useCallback((s: Step) => dispatch({ type: "GO", step: s }), []);
  const setResultsTab = useCallback((t: ResultsTab) => dispatch({ type: "SET_TAB", tab: t }), []);
  const setDriverName = useCallback((n: string | null) => dispatch({ type: "SET_DRIVER_NAME", name: n }), []);
  const setSimMeta = useCallback((m: { car: string; track: string } | null) => dispatch({ type: "SET_SIM_META", meta: m }), []);
  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  const back = useCallback(() => {
    const target: Step =
      state.step === "results" ? (state.mode === "sim" ? "import" : "configure") : "welcome";
    dispatch({ type: "GO", step: target });
  }, [state.step, state.mode]);

  const runF1 = useCallback(async () => {
    dispatch({ type: "RUN_START" });
    const t0 = performance.now();
    try {
      const data = await analyze(state.request);
      dispatch({ type: "RUN_OK", data, ms: Math.round(performance.now() - t0) });
    } catch (e) {
      dispatch({ type: "RUN_ERR", error: e instanceof Error ? e.message : "analysis failed" });
    }
  }, [state.request]);

  const runSim = useCallback(async (file: File, opts?: { driver?: string; label?: string }) => {
    dispatch({ type: "RUN_START" });
    const t0 = performance.now();
    try {
      const data = await analyzeSim(file, opts);
      dispatch({ type: "RUN_OK", data, ms: Math.round(performance.now() - t0) });
    } catch (e) {
      dispatch({ type: "RUN_ERR", error: e instanceof Error ? e.message : "import failed" });
    }
  }, []);

  const quickF1 = useCallback(async (request: ComparisonRequest) => {
    dispatch({ type: "PRESET", mode: "f1", request });
    dispatch({ type: "RUN_START" });
    const t0 = performance.now();
    try {
      const data = await analyze(request);
      dispatch({ type: "RUN_OK", data, ms: Math.round(performance.now() - t0) });
    } catch (e) {
      dispatch({ type: "RUN_ERR", error: e instanceof Error ? e.message : "analysis failed" });
    }
  }, []);

  const quickSimDemo = useCallback(async () => {
    dispatch({ type: "PRESET", mode: "sim", request: DEFAULT_REQUEST });
    dispatch({ type: "RUN_START" });
    const t0 = performance.now();
    try {
      const res = await fetch("/supra_autocross.csv");
      if (!res.ok) throw new Error("sample dataset not found");
      const file = new File([await res.blob()], "supra_autocross.csv", { type: "text/csv" });
      const data = await analyzeSim(file, { label: "SUPRA AUTOCROSS", driver: "STU" });
      dispatch({ type: "RUN_OK", data, ms: Math.round(performance.now() - t0) });
    } catch (e) {
      dispatch({ type: "RUN_ERR", error: e instanceof Error ? e.message : "demo failed" });
    }
  }, []);

  const value = useMemo<WizardCtx>(
    () => ({ state, chooseMode, setRequest, setImport, goTo, setResultsTab, setDriverName, setSimMeta, back, reset, runF1, runSim, quickF1, quickSimDemo }),
    [state, chooseMode, setRequest, setImport, goTo, setResultsTab, setDriverName, setSimMeta, back, reset, runF1, runSim, quickF1, quickSimDemo],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWizard(): WizardCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useWizard must be used within WizardProvider");
  return c;
}

// Mirrors the FastAPI response contract (backend/app/schemas/api.py).

export type Confidence = "high" | "medium" | "low";

export interface CornerOut {
  corner: number;
  distance: number;
  magnitude_s: number;
  cause: string;
  confidence: Confidence;
  brake_point_delta_m: number | null;
  apex_speed_delta_kmh: number | null;
  throttle_point_delta_m: number | null;
  signals: string[];
  lockup: boolean;
  wheelspin: boolean;
}

export interface ComparisonResponse {
  source: "fastf1" | "sim";
  session_id: string;
  reference_lap: number;
  target_lap: number;
  reference_lap_time_s: number;
  target_lap_time_s: number;
  delta_trace: {
    distance: number[];
    delta: number[];
    reference_speed: number[];
    target_speed: number[];
    reference_throttle: number[];
    target_throttle: number[];
    reference_brake: number[];
    target_brake: number[];
  };
  track_map: { x: number[]; y: number[]; delta: number[] };
  corners: CornerOut[];
  reconciliation: {
    integrated_gap_s: number;
    measured_gap_s: number;
    reconciliation_error_s: number;
    within_tolerance: boolean;
  };
  vehicle_state: {
    lockups_flagged: number;
    wheelspins_flagged: number;
    lockup_delta_agreement: number | null;
    wheelspin_delta_agreement: number | null;
  };
}

export interface ComparisonRequest {
  year: number;
  event: string;
  session: string;
  driver: string;
  reference_lap?: number | null;
  target_lap?: number | null;
}

// ---- catalog (dropdowns) ----
export interface EventItem {
  round: number;
  name: string;
  country: string;
  location: string;
  date: string;
}
export interface DriverItem {
  code: string;
  name: string;
  team: string;
  number: string;
}
export interface LapItem {
  lap_number: number;
  lap_time_s: number | null;
  is_accurate: boolean;
  is_fastest: boolean;
}

// ---- import inspect / validate ----
export interface InspectResult {
  label: string;
  driver: string;
  n_laps: number;
  laps: { lap_number: number; lap_time_s: number }[];
  channels: Record<string, boolean>;
  track_preview: { x: number[]; y: number[] };
  quality: { name: string; ok: boolean; detail: string }[];
  all_ok: boolean;
}

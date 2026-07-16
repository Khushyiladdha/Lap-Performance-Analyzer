// "Analysis Confidence" — a composite score (0-100) reflecting how much to
// trust THIS analysis, computed from figures the engine already produces.
// Deliberately not called "data quality": it doesn't measure the telemetry's
// quality, it measures how internally consistent and well-attributed this
// particular comparison turned out to be. Never a fabricated number — the
// formula is documented here and its breakdown is shown alongside the score.
import type { ComparisonResponse } from "./types";

export interface ConfidenceBreakdown {
  label: string;
  points: number;
  max: number;
  detail: string;
}

export interface ConfidenceResult {
  score: number;
  label: string;
  breakdown: ConfidenceBreakdown[];
}

const CONF_WEIGHT: Record<string, number> = { high: 1, medium: 0.6, low: 0.2 };

export function computeAnalysisConfidence(d: ComparisonResponse): ConfidenceResult {
  // 1. Reconciliation (40 pts): does the sum of per-corner deltas reconstruct
  //    the measured lap-time gap within the engine's own tolerance?
  const recon = d.reconciliation.within_tolerance ? 40 : 15;

  // 2. Attribution confidence (40 pts): weighted share of corners whose cause
  //    was identified with high confidence, vs. medium/low/ambiguous.
  const corners = d.corners;
  const confSum = corners.reduce((sum, c) => sum + (CONF_WEIGHT[c.confidence] ?? 0), 0);
  const confidence = corners.length ? Math.round((confSum / corners.length) * 40) : 0;

  // 3. Vehicle-state cross-check (20 pts): agreement between flagged lockups/
  //    wheelspins and local time loss. No flags at all -> nothing to
  //    contradict, so this doesn't penalise a clean lap.
  const agreements = [d.vehicle_state.lockup_delta_agreement, d.vehicle_state.wheelspin_delta_agreement]
    .filter((v): v is number => v != null);
  const crosscheck = agreements.length
    ? Math.round((agreements.reduce((a, b) => a + b, 0) / agreements.length) * 20)
    : 20;

  const score = recon + confidence + crosscheck;
  const label = score >= 90 ? "Excellent" : score >= 75 ? "Good" : score >= 55 ? "Fair" : "Needs review";

  return {
    score,
    label,
    breakdown: [
      { label: "Reconciliation", points: recon, max: 40, detail: d.reconciliation.within_tolerance ? "within tolerance" : "flagged" },
      { label: "Attribution confidence", points: confidence, max: 40, detail: `${corners.filter((c) => c.confidence === "high").length}/${corners.length} corners high-confidence` },
      { label: "Vehicle-state cross-check", points: crosscheck, max: 20, detail: agreements.length ? `${Math.round((agreements.reduce((a, b) => a + b, 0) / agreements.length) * 100)}% agreement` : "no events flagged" },
    ],
  };
}

import type { ReactNode } from "react";
import { InfoTip } from "./InfoTip";

export function Stat({
  label,
  value,
  sub,
  tone,
  info,
}: {
  label: ReactNode;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "loss" | "gain";
  info?: string;
}) {
  return (
    <div className="stat">
      <div className="stat__label t-label">
        {label}
        {info && <InfoTip text={info} />}
      </div>
      <div className={"stat__value" + (tone ? ` stat__value--${tone}` : "")}>{value}</div>
      {sub && <div className="stat__sub">{sub}</div>}
    </div>
  );
}

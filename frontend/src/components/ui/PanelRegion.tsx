import type { ReactNode } from "react";

export function PanelRegion({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="panel-region">
      <div className="panel-region__head">
        <span className="t-h3">{title}</span>
        {hint && <span className="t-label">{hint}</span>}
      </div>
      <div className="panel-region__body">{children}</div>
    </div>
  );
}

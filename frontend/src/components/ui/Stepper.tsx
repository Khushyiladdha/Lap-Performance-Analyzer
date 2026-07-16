import { Fragment } from "react";

export function Stepper({
  steps,
  current,
  vertical,
}: {
  steps: string[];
  current: number;
  vertical?: boolean;
}) {
  return (
    <div className={"stepper" + (vertical ? " stepper--vertical" : "")} aria-label="progress">
      {steps.map((s, i) => (
        <Fragment key={s}>
          <div className={"step " + (i < current ? "step--done" : i === current ? "step--active" : "")}>
            <span className="step__dot">{i < current ? "✓" : i + 1}</span>
            <span className="step__name">{s}</span>
          </div>
          {i < steps.length - 1 && <span className="step__bar" />}
        </Fragment>
      ))}
    </div>
  );
}

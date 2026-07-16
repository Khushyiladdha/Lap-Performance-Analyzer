import type { HTMLAttributes, ReactNode } from "react";

export function Card({
  interactive,
  className = "",
  children,
  ...rest
}: { interactive?: boolean; children: ReactNode } & HTMLAttributes<HTMLDivElement>) {
  const cls = ["card", interactive ? "card--interactive" : "", className]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

export function CardHead({ children }: { children: ReactNode }) {
  return <div className="card__head">{children}</div>;
}

export function CardBody({ children }: { children: ReactNode }) {
  return <div className="card__body">{children}</div>;
}

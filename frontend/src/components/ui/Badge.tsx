import type { ReactNode } from "react";

export function Badge({
  tone,
  children,
}: {
  tone?: "accent" | "loss" | "gain" | "ok";
  children: ReactNode;
}) {
  return <span className={"badge" + (tone ? ` badge--${tone}` : "")}>{children}</span>;
}

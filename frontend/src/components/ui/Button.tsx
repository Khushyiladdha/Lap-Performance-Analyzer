import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

export function Button({
  variant = "primary",
  size,
  className = "",
  children,
  ...rest
}: {
  variant?: Variant;
  size?: "sm" | "lg";
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const cls = ["btn", `btn--${variant}`, size ? `btn--${size}` : "", className]
    .filter(Boolean)
    .join(" ");
  return (
    <button className={cls} {...rest}>
      {children}
    </button>
  );
}

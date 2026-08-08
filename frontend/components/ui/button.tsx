import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "md" | "lg";
};

const variants = {
  primary: "border border-transparent bg-leaf text-[var(--rs-primary-foreground)] hover:bg-[var(--rs-primary-hover)]",
  secondary: "border border-border bg-surface-elevated text-ink hover:bg-[var(--rs-secondary-hover)]",
  danger: "bg-coral text-white hover:bg-[var(--rs-danger-hover)]",
  ghost: "bg-transparent text-ink hover:bg-cloud"
};

const sizes = {
  md: "min-h-11 px-4 py-2 text-sm",
  lg: "min-h-12 px-5 py-3 text-base"
};

export function Button({ className, variant = "primary", size = "md", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[3px] font-semibold transition duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf/25",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}

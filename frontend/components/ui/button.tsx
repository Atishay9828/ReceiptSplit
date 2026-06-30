import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
};

const variants = {
  primary: "bg-leaf text-white hover:bg-[#286c4d]",
  secondary: "bg-mint text-ink hover:bg-[#ccebdc]",
  danger: "bg-coral text-white hover:bg-[#cf5141]",
  ghost: "bg-transparent text-ink hover:bg-cloud"
};

export function Button({ className, variant = "primary", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-55",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

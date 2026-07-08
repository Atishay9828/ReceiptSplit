import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "md" | "lg";
};

const variants = {
  primary: "bg-leaf text-white hover:bg-[#286c4d]",
  secondary: "bg-mint text-ink hover:bg-[#ccebdc]",
  danger: "bg-coral text-white hover:bg-[#cf5141]",
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
        "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf/25",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}

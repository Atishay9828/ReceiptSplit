import type { InputHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: ReactNode;
};

export function Input({ className, label, hint, id, ...props }: InputProps) {
  const inputId = id ?? props.name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className="grid gap-1.5 text-sm font-medium text-ink" htmlFor={inputId}>
      <span>{label}</span>
      <input
        id={inputId}
        className={cn(
          "min-h-11 rounded-[3px] border border-border-strong bg-surface-elevated px-3 py-2 text-base font-normal text-ink outline-none ring-leaf/20 transition placeholder:text-soft focus:border-leaf focus:ring-4 disabled:cursor-not-allowed disabled:bg-cloud disabled:text-soft",
          className
        )}
        {...props}
      />
      {hint ? <span className="text-xs font-normal text-muted">{hint}</span> : null}
    </label>
  );
}

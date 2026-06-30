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
          "min-h-11 rounded-md border border-[#ccd8d1] bg-white px-3 py-2 text-base font-normal outline-none ring-leaf/20 transition focus:border-leaf focus:ring-4",
          className
        )}
        {...props}
      />
      {hint ? <span className="text-xs font-normal text-[#63706b]">{hint}</span> : null}
    </label>
  );
}

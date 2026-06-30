import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
};

export function Select({ className, label, id, children, ...props }: SelectProps) {
  const selectId = id ?? props.name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className="grid gap-1.5 text-sm font-medium text-ink" htmlFor={selectId}>
      <span>{label}</span>
      <select
        id={selectId}
        className={cn(
          "min-h-11 rounded-md border border-[#ccd8d1] bg-white px-3 py-2 text-base font-normal outline-none ring-leaf/20 transition focus:border-leaf focus:ring-4",
          className
        )}
        {...props}
      >
        {children}
      </select>
    </label>
  );
}

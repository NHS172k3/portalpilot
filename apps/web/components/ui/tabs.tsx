import * as React from "react";

import { cn } from "../../lib/utils";

export function TabsList({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("grid gap-2 rounded-lg bg-[#ECECE7] p-1 text-sm text-[#6B6B66]", className)}
      role="tablist"
      {...props}
    />
  );
}

export function TabsTrigger({
  active,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      aria-selected={active}
      className={cn(
        "inline-flex h-10 items-center justify-between rounded-md px-3 font-semibold transition-colors",
        active ? "bg-white text-[#0D0D0D] shadow-sm" : "text-[#6B6B66] hover:bg-white/70 hover:text-[#0D0D0D]",
        className,
      )}
      role="tab"
      type="button"
      {...props}
    />
  );
}

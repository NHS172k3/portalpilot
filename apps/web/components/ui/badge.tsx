import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "../../lib/utils";

const badgeVariants = cva(
  "inline-flex w-fit items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-[#0D0D0D] text-white",
        secondary: "border-transparent bg-[#ECECE7] text-[#4A4A46]",
        success: "border-transparent bg-[#E7F4EF] text-[#0E7A5F]",
        warning: "border-transparent bg-amber-100 text-amber-800",
        destructive: "border-transparent bg-rose-100 text-rose-800",
        outline: "border-[#D9D9D2] text-[#4A4A46]",
      },
    },
    defaultVariants: {
      variant: "secondary",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant, className }))} {...props} />;
}

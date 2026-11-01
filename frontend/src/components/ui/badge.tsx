import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium", {
  variants: {
    variant: {
      default: "bg-rose-50 text-rose-700 border border-rose-100",
      plum: "bg-plum text-white",
      outline: "border border-plum/15 text-plum/70",
      success: "bg-emerald-50 text-emerald-700 border border-emerald-100",
    },
  },
  defaultVariants: { variant: "default" },
});

export function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

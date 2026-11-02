import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Tooltip } from "antd";
import { badgeText, tagExplanation } from "../PhotoBadge";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium", {
  variants: {
    variant: {
      default: "bg-tint text-plum border border-line",
      plum: "bg-plum text-on-ink",
      outline: "border border-plum/15 text-plum/70",
      success: "bg-emerald-50 text-emerald-700 border border-emerald-100",
    },
  },
  defaultVariants: { variant: "default" },
});

export function Badge({
  className,
  variant,
  title,
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  const help=title ?? tagExplanation(badgeText(children));
  return <Tooltip title={help} trigger={["hover","focus"]}><span tabIndex={0} aria-label={help} className={cn(badgeVariants({ variant }), className)} {...props}>{children}</span></Tooltip>;
}

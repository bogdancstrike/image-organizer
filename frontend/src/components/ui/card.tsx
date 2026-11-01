import * as React from "react";
import { cn } from "@/lib/utils";

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-2xl border border-rose-100/90 bg-white/75 backdrop-blur-sm shadow-[0_1px_0_rgba(255,255,255,.9)_inset,0_10px_30px_-18px_rgba(120,40,80,.35)]",
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = "Card";

export const CardHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex items-center justify-between gap-2 px-3.5 pt-3", className)} {...props} />
);

export const CardTitle = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex min-w-0 items-center gap-1.5 text-[13px] font-medium text-plum", className)} {...props} />
);

export const CardContent = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("px-3.5 pb-3 pt-2", className)} {...props} />
);

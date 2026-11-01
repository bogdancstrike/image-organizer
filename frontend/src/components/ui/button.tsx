import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300 disabled:pointer-events-none disabled:opacity-50 cursor-pointer select-none active:scale-[.97]",
  {
    variants: {
      variant: {
        default: "bg-plum text-white shadow-[0_6px_20px_-6px_rgba(90,30,70,.6)] hover:bg-plum-700",
        soft: "bg-white/80 text-plum border border-rose-100 shadow-sm hover:bg-white",
        ghost: "text-plum/80 hover:bg-rose-50 hover:text-plum",
        outline: "border border-plum/20 bg-transparent text-plum hover:bg-white/60",
      },
      size: {
        default: "h-10 px-5",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-7 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

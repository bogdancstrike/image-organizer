import { useMemo } from "react";
import { cn, prefersReducedMotion } from "@/lib/utils";

const N = 8;
const BLADE = "M-18,0 L200,0 L200,-200 L-88,-200 Q-24,-90.0 -18,0 Z";
const OPEN = 62.0;
const CLOSED = 10.0;

/**
 * Animated camera iris (replaces the old flower): 8 blades slide along their normals, so the opening
 * breathes between wide open and almost closed. Colors come from the theme (--flower-* variables).
 * With prefers-reduced-motion it renders open and still.
 */
export function Flower({ caption, className }: { caption: string; className?: string }) {
  const still = useMemo(() => prefersReducedMotion(), []);
  return (
    <div className={cn("pointer-events-none flex flex-col items-center", className)}>
      <svg viewBox="-130 -130 260 260" className="bloom h-60 w-60 sm:h-72 sm:w-72" aria-hidden>
        <defs>
          <linearGradient id="iris-blade" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0" style={{ stopColor: "var(--flower-a)" }} />
            <stop offset="1" style={{ stopColor: "var(--flower-b)" }} />
          </linearGradient>
          <radialGradient id="iris-glass" cx=".42" cy=".38" r=".6">
            <stop offset="0" style={{ stopColor: "var(--flower-core)" }} />
            <stop offset="1" style={{ stopColor: "var(--page)" }} />
          </radialGradient>
          <radialGradient id="iris-glow" r=".5">
            <stop offset=".72" style={{ stopColor: "var(--flower-stroke)", stopOpacity: 0.18 }} />
            <stop offset="1" style={{ stopColor: "var(--flower-stroke)", stopOpacity: 0 }} />
          </radialGradient>
          <clipPath id="iris-lens">
            <circle r="100" />
          </clipPath>
        </defs>
        <circle r="128" fill="url(#iris-glow)" />
        <circle r="100" fill="url(#iris-glass)" />
        <circle cx="-16" cy="-18" r="10" style={{ fill: "var(--flower-eye)" }} opacity=".6" />
        <circle cx="12" cy="14" r="4" style={{ fill: "var(--flower-eye)" }} opacity=".25" />
        <g clipPath="url(#iris-lens)">
          {Array.from({ length: N }, (_, i) => (
            <g key={i} transform={`rotate(${(i * 360) / N})`}>
              <g transform={`translate(0 ${-OPEN})`}>
                {!still && (
                  <animateTransform
                    attributeName="transform"
                    type="translate"
                    values={`0,${-OPEN};0,${-CLOSED};0,${-CLOSED};0,${-OPEN};0,${-OPEN}`}
                    keyTimes="0;0.4;0.5;0.9;1"
                    dur="7s"
                    repeatCount="indefinite"
                    calcMode="spline"
                    keySplines=".6 0 .4 1;0 0 1 1;.6 0 .4 1;0 0 1 1"
                  />
                )}
                <path d={BLADE} fill="url(#iris-blade)" strokeWidth="1.4" strokeLinejoin="round" style={{ stroke: "var(--page)" }} />
              </g>
            </g>
          ))}
        </g>
        <circle r="100" fill="none" strokeWidth="2.5" style={{ stroke: "var(--flower-stroke)" }} />
        <circle r="107" fill="none" strokeWidth="1" style={{ stroke: "var(--line)" }} />
      </svg>
      <div className="mt-2 font-serif text-xl italic text-plum/55">{caption}</div>
    </div>
  );
}

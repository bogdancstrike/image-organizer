import { cn } from "@/lib/utils";

/** Aperture iris: six lens blades around a glass opening. Colors follow the theme (--logo-* variables). */
const BLADES = [
  "M0.0,-29.0 A29.0,29.0 0 0,1 25.11,-14.5 L10.89,1.53 L6.77,-8.67 Q6.41,-16.8 0.0,-29.0Z",
  "M25.11,-14.5 A29.0,29.0 0 0,1 25.11,14.5 L4.12,10.2 L10.89,1.53 Q17.75,-2.84 25.11,-14.5Z",
  "M25.11,14.5 A29.0,29.0 0 0,1 0.0,29.0 L-6.77,8.67 L4.12,10.2 Q11.34,13.95 25.11,14.5Z",
  "M0.0,29.0 A29.0,29.0 0 0,1 -25.11,14.5 L-10.89,-1.53 L-6.77,8.67 Q-6.41,16.8 0.0,29.0Z",
  "M-25.11,14.5 A29.0,29.0 0 0,1 -25.11,-14.5 L-4.12,-10.2 L-10.89,-1.53 Q-17.75,2.84 -25.11,14.5Z",
  "M-25.11,-14.5 A29.0,29.0 0 0,1 -0.0,-29.0 L6.77,-8.67 L-4.12,-10.2 Q-11.34,-13.95 -25.11,-14.5Z",
];
const SHADES = [0, 0.06, 0.12, 0.18, 0.1, 0.03];
const HEXAGON = "6.77,-8.67 10.89,1.53 4.12,10.2 -6.77,8.67 -10.89,-1.53 -4.12,-10.2";

export function LogoMark({ className, spinning = false }: { className?: string; spinning?: boolean }) {
  return (
    <svg viewBox="0 0 64 64" className={cn("shrink-0", spinning && "animate-[spin_2.4s_linear_infinite]", className)} aria-hidden>
      <defs>
        <linearGradient id="aio-blade" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" style={{ stopColor: "var(--logo-a)" }} />
          <stop offset="1" style={{ stopColor: "var(--logo-b)" }} />
        </linearGradient>
        <radialGradient id="aio-glass" cx="0.38" cy="0.35" r="0.75">
          <stop offset="0" style={{ stopColor: "var(--logo-core-a)" }} />
          <stop offset="1" style={{ stopColor: "var(--logo-core-b)" }} />
        </radialGradient>
      </defs>
      <g transform="translate(32 32)">
        <circle r="31" style={{ fill: "var(--logo-core-b)" }} />
        {BLADES.map((d, i) => (
          <g key={i}>
            <path d={d} fill="url(#aio-blade)" strokeWidth="1.3" strokeLinejoin="round" style={{ stroke: "var(--logo-core-b)" }} />
            {SHADES[i] > 0 && <path d={d} fill="#000" fillOpacity={SHADES[i]} />}
          </g>
        ))}
        <polygon points={HEXAGON} fill="url(#aio-glass)" strokeWidth="1.3" strokeLinejoin="round" style={{ stroke: "var(--logo-core-b)" }} />
        <circle cx="-3" cy="-3.4" r="2.6" fill="#fff" fillOpacity=".9" />
        <circle cx="2.6" cy="2.8" r="1" fill="#fff" fillOpacity=".45" />
        <circle r="31.4" fill="none" strokeWidth="0.8" style={{ stroke: "var(--logo-b)", strokeOpacity: 0.55 }} />
      </g>
    </svg>
  );
}

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark className="h-9 w-9 drop-shadow-[0_4px_10px_rgba(0,0,0,.35)]" />
      <div className="leading-tight">
        <div className="text-[13px] font-semibold tracking-tight text-plum">Auto Image Organizer</div>
        <div className="text-[11px] text-plum/50">photos & videos, sorted</div>
      </div>
    </div>
  );
}

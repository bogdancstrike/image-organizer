import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";

const LINES = "M5.0,-8.66 L0.0,-26.0 M10.0,0.0 L22.52,-13.0 M5.0,8.66 L22.52,13.0 M-5.0,8.66 L0.0,26.0 M-10.0,0.0 L-22.52,13.0 M-5.0,-8.66 L-22.52,-13.0";
const HEXAGON = "5.0,-8.66 10.0,0.0 5.0,8.66 -5.0,8.66 -10.0,0.0 -5.0,-8.66";

/** Fine-line aperture mark. Colors follow the theme (--logo-* variables). */
export function LogoMark({ className, spinning = false }: { className?: string; spinning?: boolean }) {
  return (
    <svg viewBox="0 0 64 64" className={cn("shrink-0", spinning && "animate-[spin_2.4s_linear_infinite]", className)} aria-hidden>
      <defs>
        <radialGradient id="aio-body" cx=".4" cy=".35" r=".8">
          <stop offset="0" style={{ stopColor: "var(--logo-core-a)" }} />
          <stop offset="1" style={{ stopColor: "var(--logo-core-b)" }} />
        </radialGradient>
      </defs>
      <g transform="translate(32 32)" fill="none" strokeLinecap="round" strokeLinejoin="round">
        <circle r="29" fill="url(#aio-body)" />
        <circle r="29" strokeWidth="1.6" style={{ stroke: "var(--logo-b)" }} />
        <path d={LINES} strokeWidth="1.6" style={{ stroke: "var(--logo-a)" }} />
        <polygon points={HEXAGON} strokeWidth="1.6" style={{ stroke: "var(--logo-a)", fill: "var(--logo-core-b)" }} />
        <circle cx="-2.6" cy="-3" r="2" fill="#fafafa" opacity=".85" />
      </g>
    </svg>
  );
}

export function Logo() {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark className="h-9 w-9" />
      <div className="leading-tight">
        <div className="text-[13px] font-semibold tracking-tight text-plum">Auto Image Organizer</div>
        <div className="text-[11px] text-plum/50">{t("tagline")}</div>
      </div>
    </div>
  );
}

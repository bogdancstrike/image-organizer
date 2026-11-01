import { cn } from "@/lib/utils";

/** Flower made of photo tiles: the Auto Image Organizer mark. */
export function LogoMark({ className, spinning = false }: { className?: string; spinning?: boolean }) {
  return (
    <svg viewBox="0 0 64 64" className={cn("shrink-0", spinning && "animate-[spin_3s_linear_infinite]", className)} aria-hidden>
      <defs>
        <linearGradient id="aio-petal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffc2da" />
          <stop offset="1" stopColor="#e5679b" />
        </linearGradient>
        <linearGradient id="aio-core" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#7a3260" />
          <stop offset="1" stopColor="#4a1d3b" />
        </linearGradient>
      </defs>
      <g transform="translate(32 32)">
        <g stroke="#fff" strokeWidth="2">
          {[0, 60, 120, 180, 240, 300].map((r) => (
            <rect key={r} x="-8" y="-30" width="16" height="21" rx="5" fill="url(#aio-petal)" transform={`rotate(${r})`} />
          ))}
        </g>
        <circle r="10" fill="url(#aio-core)" stroke="#fff" strokeWidth="2" />
        <circle cx="3" cy="-3" r="3.4" fill="#fff" />
      </g>
    </svg>
  );
}

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark className="h-9 w-9 drop-shadow-[0_4px_10px_rgba(229,103,155,.35)]" />
      <div className="leading-tight">
        <div className="text-[13px] font-semibold tracking-tight text-plum">Auto Image Organizer</div>
        <div className="text-[11px] text-plum/50">photos & videos, sorted ✿</div>
      </div>
    </div>
  );
}

import { cn } from "@/lib/utils";

/** The big pink flower from the demo, shown when the pile is empty. */
export function Flower({ caption, className }: { caption: string; className?: string }) {
  const petals = Array.from({ length: 9 }, (_, i) => i * 40);
  return (
    <div className={cn("pointer-events-none flex flex-col items-center", className)}>
      <svg viewBox="-100 -100 200 200" className="bloom h-56 w-56 sm:h-72 sm:w-72" aria-hidden>
        <defs>
          <radialGradient id="fl-petal" cx="0.5" cy="0.9" r="0.9">
            <stop offset="0" stopColor="#f6c4d8" />
            <stop offset="1" stopColor="#fbe4ee" />
          </radialGradient>
        </defs>
        <g>
          {petals.map((r) => (
            <ellipse
              key={r}
              cx="0"
              cy="-52"
              rx="27"
              ry="46"
              transform={`rotate(${r})`}
              fill="url(#fl-petal)"
              stroke="#e7a9c3"
              strokeWidth="1.2"
              opacity=".95"
            />
          ))}
        </g>
        <circle r="24" fill="#7b5466" />
        <circle r="24" fill="none" stroke="#5f3b4c" strokeWidth="3" opacity=".4" />
        <circle cx="3" cy="-3" r="10" fill="#f7e9ef" />
      </svg>
      <div className="mt-1 font-serif text-xl italic text-plum/55">{caption}</div>
    </div>
  );
}

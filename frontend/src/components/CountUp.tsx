import { useEffect, useRef, useState } from "react";
import { fmt, prefersReducedMotion } from "@/lib/utils";

/** Smoothly animates toward `value` (REQ-UI-2.4). */
export function CountUp({ value, className }: { value: number; className?: string }) {
  const [shown, setShown] = useState(value);
  const from = useRef(value);
  const shownRef = useRef(value);
  shownRef.current = shown;

  useEffect(() => {
    if (prefersReducedMotion()) {
      setShown(value);
      return;
    }
    from.current = shownRef.current;
    const start = performance.now();
    const dur = 420;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const e = 1 - Math.pow(1 - t, 3);
      setShown(Math.round(from.current + (value - from.current) * e));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return <span className={className}>{fmt(shown)}</span>;
}

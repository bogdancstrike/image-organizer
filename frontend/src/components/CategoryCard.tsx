import { InfoBadge } from "./PhotoBadge";
import { FolderClosed, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { CountUp } from "./CountUp";
import { cn } from "@/lib/utils";

interface Props {
  name: string;
  emoji?: string;
  count: number;
  total: number;
  slotRef: (el: HTMLDivElement | null) => void;
  onClick?: () => void;
  variant?: "default" | "trash" | "ghost";
  tall?: boolean;
  index?: number;
  cover?: string | null;
}

export function CategoryCard({ name, emoji, count, total, slotRef, onClick, variant = "default", tall, index = 0, cover }: Props) {
  const Icon = variant === "trash" ? Trash2 : FolderClosed;
  return (
    <Card
      onClick={onClick}
      style={{ animationDelay: `${Math.min(index, 16) * 45}ms` }}
      className={cn(
        "pop-in group relative overflow-hidden transition-shadow",
        onClick && "cursor-pointer hover:shadow-[var(--card-shadow-hover)]",
        variant === "ghost" && "opacity-55",
      )}
      title={total > count ? `${total} files` : undefined}
    >
      <CardHeader>
        <CardTitle>
          {cover ? (
            <img src={cover} alt="" className="h-6 w-6 shrink-0 rounded-full border border-line object-cover" />
          ) : (
            <Icon className="h-3.5 w-3.5 shrink-0 text-plum/60" strokeWidth={1.8} />
          )}
          <span className="truncate">{variant === "trash" ? `${name} → trash` : name}</span>
          {emoji && variant !== "trash" && <InfoBadge message={`${name} folder`} className="text-xs opacity-80">{emoji}</InfoBadge>}
        </CardTitle>
        <CountUp value={count} className="text-[15px] font-semibold tabular-nums text-plum/80" />
      </CardHeader>
      <CardContent>
        <div ref={slotRef} className={cn("w-full", tall ? "h-[68px]" : "h-[45px]")} />
      </CardContent>
    </Card>
  );
}

export function GhostCard({ name, index = 0 }: { name?: string; index?: number }) {
  return (
    <Card className="pop-in overflow-hidden opacity-70" style={{ animationDelay: `${index * 40}ms` }}>
      <CardHeader>
        <CardTitle>
          <FolderClosed className="h-3.5 w-3.5 text-plum/40" strokeWidth={1.8} />
          {name ? <span className="truncate text-plum/50">{name}</span> : <span className="shimmer h-3 w-24 rounded" />}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="shimmer h-[45px] w-full rounded-lg" />
      </CardContent>
    </Card>
  );
}

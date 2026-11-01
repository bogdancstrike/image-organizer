import { Drawer, Empty, Tag, Tooltip } from "antd";
import { Film } from "lucide-react";
import type { PlanItem } from "@/api";

const SOURCE_LABEL: Record<string, string> = {
  clip: "CLIP",
  ai: "AI",
  rule: "rule",
  cluster: "cluster",
  date: "date",
  duplicate: "duplicate",
};

export function FilesDrawer({ title, items, onClose }: { title: string | null; items: PlanItem[]; onClose: () => void }) {
  return (
    <Drawer open={!!title} onClose={onClose} title={title} size={520}>
      {items.length === 0 && <Empty description="Files appear here when the sort finishes" />}
      {items[0] && <div className="mb-3 truncate text-xs text-plum/55">→ {items[0].destination}/</div>}
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {items.map((p) => (
          <Tooltip
            key={p.file_id}
            title={
              <div className="text-xs">
                <div className="break-all">{p.rel_path}</div>
                <div className="opacity-70">
                  {SOURCE_LABEL[p.source] ?? p.source}
                  {p.source !== "date" && p.source !== "duplicate" ? ` · ${(p.confidence * 100).toFixed(0)}%` : ""}
                </div>
              </div>
            }
          >
            <div className="group relative aspect-square overflow-hidden rounded-xl border-2 border-white bg-rose-50 shadow-sm">
              <img src={p.thumb} alt={p.name} loading="lazy" className="h-full w-full object-cover" />
              {p.kind === "video" && (
                <Film size={14} className="absolute right-1.5 top-1.5 text-white drop-shadow" />
              )}
              {p.source === "ai" && (
                <Tag className="absolute bottom-1 left-1 m-0 px-1 text-[10px] leading-4" color="magenta">
                  AI
                </Tag>
              )}
            </div>
          </Tooltip>
        ))}
      </div>
    </Drawer>
  );
}

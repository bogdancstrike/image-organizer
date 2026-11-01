import { useState } from "react";
import { Button, Drawer, Empty, Input, Tooltip } from "antd";
import { useI18n } from "@/i18n";
import { Film, Paperclip } from "lucide-react";
import type { PlanItem } from "@/api";
import { FLAG, FileDetails, useMediaViewer } from "./MediaViewer";

export function Thumb({ p, onOpen, size = "md" }: { p: PlanItem; onOpen: () => void; size?: "sm" | "md" }) {
  return (
    <Tooltip title={<FileDetails p={p} />} mouseEnterDelay={0.4}>
      <button
        onClick={onOpen}
        className={
          (size === "sm" ? "h-12 w-12 " : "aspect-square w-full ") +
          "group relative shrink-0 cursor-zoom-in overflow-hidden rounded-xl border-2 border-white bg-tint shadow-sm transition-transform hover:scale-[1.04] focus-visible:outline-2 focus-visible:outline-petal"
        }
        aria-label={`Open ${p.name}`}
      >
        <img src={p.thumb} alt={p.name} loading="lazy" className="h-full w-full object-cover" />
        {p.kind === "video" && <Film size={size === "sm" ? 11 : 15} className="absolute right-1 top-1 text-white drop-shadow" />}
        {size === "md" && (
          <div className="absolute inset-x-1 bottom-1 flex flex-wrap gap-0.5">
            {p.source === "ai" && <span className="rounded bg-fuchsia-600/85 px-1 text-[10px] text-white">AI</span>}
            {p.quality?.flags.map((f) => (
              <span key={f} className="rounded bg-black/60 px-1 text-[10px] text-white" title={FLAG[f]?.label}>
                {FLAG[f]?.emoji ?? "!"}
              </span>
            ))}
            {p.quality?.smiling && <span className="rounded bg-black/40 px-1 text-[10px]">😄</span>}
            {p.sidecars?.length ? (
              <span className="inline-flex items-center rounded bg-black/50 px-1 text-[10px] text-white">
                <Paperclip size={9} />
                {p.sidecars.length}
              </span>
            ) : null}
          </div>
        )}
      </button>
    </Tooltip>
  );
}

/** Files of one folder card. Click a photo to open the full-size viewer (zoom, rotate, ← → to browse). */
export function FilesDrawer({
  title,
  items,
  onClose,
  onRename,
}: {
  title: string | null;
  items: PlanItem[];
  onClose: () => void;
  onRename?: (name: string) => Promise<void>;
}) {
  const viewer = useMediaViewer(items);
  const { t } = useI18n();
  const [name, setName] = useState("");
  return (
    <Drawer open={!!title} onClose={onClose} title={title} size={560}>
      {items.length === 0 && <Empty description="Files appear here when the sort finishes" />}
      {onRename && items[0] && (
        <div className="mb-3 flex gap-2">
          <Input placeholder={items[0].category} value={name} onChange={(e) => setName(e.target.value)} maxLength={60} />
          <Button disabled={!name.trim()} onClick={() => onRename(name.trim()).then(() => setName("")).catch(() => {})}>
            {t("rename")}
          </Button>
        </div>
      )}
      {items[0] && <div className="mb-3 truncate text-xs text-plum/55">→ {items[0].destination}/ · click a photo to view it large</div>}
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {items.map((p) => (
          <Thumb key={p.file_id} p={p} onOpen={() => viewer.open(p)} />
        ))}
      </div>
      {viewer.node}
    </Drawer>
  );
}

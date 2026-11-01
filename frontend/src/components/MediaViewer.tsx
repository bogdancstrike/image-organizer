import { useMemo, useState, type ReactNode } from "react";
import { Image, Modal } from "antd";
import { previewUrl, type PlanItem } from "@/api";

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${Math.round(v * 100)}%`);

const SOURCE_LABEL: Record<string, string> = {
  clip: "CLIP match",
  ai: "AI",
  rule: "rule",
  cluster: "auto group",
  date: "date",
  duplicate: "duplicate",
  quality: "quality check",
  manual: "set by you",
};

export const FLAG: Record<string, { label: string; emoji: string }> = {
  blurry: { label: "Blurry", emoji: "🌫️" },
  "eyes-closed": { label: "Eyes closed", emoji: "😑" },
  "too-dark": { label: "Too dark", emoji: "🌑" },
  "too-bright": { label: "Too bright", emoji: "☀️" },
  noisy: { label: "Noisy", emoji: "🌪️" },
  tilted: { label: "Tilted horizon", emoji: "📐" },
  "cropped-face": { label: "Face cut off", emoji: "✂️" },
};

export function FileDetails({ p }: { p: PlanItem }) {
  const q = p.quality;
  return (
    <div className="space-y-0.5 text-xs">
      <div className="break-all font-medium">{p.rel_path}</div>
      <div className="opacity-75">
        {p.category} · {SOURCE_LABEL[p.source] ?? p.source}
        {["clip", "ai", "cluster"].includes(p.source) ? ` ${pct(p.confidence)}` : ""}
      </div>
      {q && (
        <div className="opacity-75">
          sharpness {pct(q.sharpness)} · {q.faces} face{q.faces === 1 ? "" : "s"}
          {q.faces ? ` · eyes closed ${pct(q.blink)} · smile ${pct(q.smile)}` : ""}
          {q.flags.length ? ` · ${q.flags.map((f) => FLAG[f]?.label ?? f).join(", ")}` : ""}
        </div>
      )}
      {p.sidecars?.length ? <div className="opacity-75">+ {p.sidecars.map((s) => s.split("/").pop()).join(", ")}</div> : null}
    </div>
  );
}

/**
 * Full-size viewer for plan items: photos open in a zoomable lightbox (← → to browse, rotate, zoom),
 * videos in a player. Usage: const viewer = useMediaViewer(items); viewer.open(item); render {viewer.node}.
 */
export function useMediaViewer(items: PlanItem[]): { open: (p: PlanItem) => void; node: ReactNode } {
  const photos = useMemo(() => items.filter((p) => p.kind === "image"), [items]);
  const [current, setCurrent] = useState<number | null>(null);
  const [video, setVideo] = useState<PlanItem | null>(null);

  const open = (p: PlanItem) => {
    if (p.kind === "video") setVideo(p);
    else setCurrent(Math.max(0, photos.indexOf(p)));
  };

  const node = (
    <>
      <div className="hidden">
        <Image.PreviewGroup
          items={photos.map((p) => previewUrl(p.rel_path))}
          preview={{
            open: current !== null,
            current: current ?? 0,
            onOpenChange: (v: boolean) => !v && setCurrent(null),
            onChange: (c: number) => setCurrent(c),
            imageRender: (img: ReactNode, info: { current: number }) => (
              <div className="flex flex-col items-center gap-3">
                {img}
                {photos[info.current] && (
                  <div className="max-w-[80vw] rounded-lg bg-black/55 px-3 py-1.5 text-white">
                    <FileDetails p={photos[info.current]} />
                  </div>
                )}
              </div>
            ),
          }}
        />
      </div>
      <Modal open={!!video} onCancel={() => setVideo(null)} footer={null} width={900} title={video?.name} destroyOnHidden centered>
        {video && (
          <>
            <video src={previewUrl(video.rel_path)} controls autoPlay className="max-h-[70vh] w-full rounded-lg bg-black" />
            <div className="mt-2 text-plum/70">
              <FileDetails p={video} />
            </div>
          </>
        )}
      </Modal>
    </>
  );
  return { open, node };
}

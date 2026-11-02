import { useMemo, useState, type ReactNode } from "react";
import { Image, Modal } from "antd";
import { InfoBadge, SOURCE_HELP } from "./PhotoBadge";
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

export const FLAG: Record<string, { label: string; emoji: string; help: string }> = {
  blurry: { label: "Blurry", emoji: "🌫️", help: "Focus check: the subject may be blurry or out of focus." },
  "eyes-closed": { label: "Eyes closed", emoji: "😑", help: "Eye check: closed eyes were detected on a face included by your settings." },
  "too-dark": { label: "Too dark", emoji: "🌑", help: "Exposure check: too much shadow detail may be lost." },
  "too-bright": { label: "Too bright", emoji: "☀️", help: "Exposure check: highlights may be clipped." },
  noisy: { label: "Noisy", emoji: "🌪️", help: "Noise check: strong image grain was detected." },
  tilted: { label: "Tilted horizon", emoji: "📐", help: "Horizon check: consistent lines appear tilted. This is an experimental check." },
  "cropped-face": { label: "Face cut off", emoji: "✂️", help: "Framing check: a detected face touches the image edge." },
};

export function FileDetails({ p }: { p: PlanItem }) {
  const q = p.quality;
  return (
    <div className="space-y-0.5 text-xs">
      <div className="break-all font-medium">{p.rel_path}</div>
      <div className="opacity-75">
        {p.category} · <InfoBadge message={SOURCE_HELP[p.source] ?? p.source}>{SOURCE_LABEL[p.source] ?? p.source}</InfoBadge>
        {["clip", "ai", "cluster"].includes(p.source) ? ` ${pct(p.confidence)}` : ""}
      </div>
      {q && (
        <div className="opacity-75">
          sharpness {pct(q.sharpness)} · {q.faces} face{q.faces === 1 ? "" : "s"}
          {q.faces ? ` · eyes closed ${pct(q.blink)} · smile ${pct(q.smile)}` : ""}
          {q.faces_considered ? ` · ${q.eyes_open}/${q.faces_considered} faces with eyes open` : ""}
          {q.flags.length ? ` · ${q.flags.map((f) => FLAG[f]?.label ?? f).join(", ")}` : ""}
        </div>
      )}
      {p.pick && (
        <div className="space-y-0.5 opacity-90">
          <div>{p.pick.picked ? "★ Top pick" : "Recommendation"} · {(p.pick.rating ?? 1 + p.pick.score * 4).toFixed(2)}/5 · {p.pick.profile ?? "general"}</div>
          {p.pick.reasons.length > 0 && <div>{p.pick.reasons.join(" · ")}</div>}
          {p.pick.parts && <div className="flex flex-wrap gap-x-2 opacity-75">
            {Object.entries({ tech: "Technical", expr: "Expression", comp: "Composition", light: "Lighting", aes: "Presentation", detail: "Detail consistency", balance: "Visual balance", separation: "Subject separation", social: "Social readiness", crop: "Crop fit", clarity: "Thumbnail clarity", impact: "Visual story", contrast: "Contrast", color: "Color", novelty: "Unique view", relevance: "Subject relevance", tenengrad: "Gradient focus", directionality: "Directional edges", blocking: "Block artifacts", thumbnail: "Thumbnail detail" }).map(([key, label]) =>
              p.pick?.parts?.[key] !== undefined && <span key={key}>{label} {Math.round(p.pick.parts[key] * 100)}%</span>)}
          </div>}
        </div>
      )}
      {!!p.tags?.length && <div className="flex flex-wrap gap-1">{p.tags.map(tag => <InfoBadge key={tag.label}
        message={`${tag.label} · ${tag.source === "metadata" ? "file metadata" : `local AI tag, ${Math.round(tag.score*100)}% heuristic strength`}`}
        className="rounded bg-current/10 px-1">#{tag.label}</InfoBadge>)}</div>}
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
          items={photos.map((p) => previewUrl(p.preview_path ?? p.rel_path))}
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

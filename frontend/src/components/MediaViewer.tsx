import { cloneElement, isValidElement, useEffect, useMemo, useState, type ReactNode, type ReactElement, type ImgHTMLAttributes } from "react";
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
          <div>{p.pick.winner ? "🥇 Winner photo" : p.pick.picked ? "★ Top pick" : "Recommendation"} · {(p.pick.rating ?? 1 + p.pick.score * 4).toFixed(2)}/5 · {p.pick.profile ?? "general"}</div>
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

const SCORE_LABELS: Record<string, [string, string]> = {
  tech: ["Technical quality", "Subject focus, exposure and noise combined."],
  expr: ["Expression", "Readable eye, gaze and expression signals, adapted to the photography profile."],
  comp: ["Composition", "Framing, balance, subject separation and local semantic composition signals."],
  light: ["Lighting", "Local image/text assessment of lighting and highlight detail."],
  aes: ["Presentation", "Genre-specific visual presentation; an assisted review signal."],
  detail: ["Detail consistency", "Edge persistence across resolutions helps distinguish detail from noise."],
  balance: ["Visual balance", "A weak spatial balance signal from image gradients."],
  separation: ["Subject separation", "Edge contrast between subject regions and the surrounding image."],
  tenengrad: ["Gradient focus", "Sobel gradient energy supplements the focus assessment."],
  blocking: ["Block artifacts", "Higher indicates more block-boundary artifacts; this is a weak indicator."],
  directionality: ["Directional edges", "Edge orientation strength; deliberate motion and linear subjects can score highly."],
  thumbnail: ["Thumbnail detail", "Detail that remains visible at a small display size."],
  social: ["Social readiness", "Posting-readiness blend; does not predict engagement."],
  crop: ["Crop fit", "Estimated retained content and important faces for the proposed crop."],
  clarity: ["Thumbnail clarity", "Small-screen detail and recognizability."],
  impact: ["Visual story", "Semantic evidence of a clear subject or engaging moment."],
  contrast: ["Contrast", "Tonal separation in the analyzed preview."],
  color: ["Color", "A weak, restrained colorfulness cue; monochrome remains valid."],
  novelty: ["Unique view", "Visual difference from nearby alternatives in the scene."],
  relevance: ["Subject priority", "Local match to your culling priority prompt."],
  relative: ["Shoot comparison", "Relative rank within the shoot; this is not absolute quality."],
};

export function PhotoInfoPanel({ p }: { p: PlanItem }) {
  const rating=p.pick?.rating ?? p.quality?.rating ?? (p.pick ? 1+4*p.pick.score : p.quality ? 1+4*p.quality.score : null);
  const trashed=p.decision?.action === "recoverable-trash" || p.destination.split("/").includes(".aio-trash");
  const explanation=p.decision?.explanation ?? (p.duplicate_of ? "A duplicate matcher selected another file to keep." : SOURCE_HELP[p.source] ?? "Review the proposed category before applying.");
  return <aside aria-label="Photo recommendations" className="min-h-0 overflow-y-auto overscroll-contain rounded-2xl border border-line bg-surface p-5 text-left text-plum shadow-xl"
    onMouseDown={event=>event.stopPropagation()} onPointerDown={event=>event.stopPropagation()} onWheel={event=>event.stopPropagation()}>
    <div className="break-words text-base font-semibold">{p.name}</div>
    {p.rel_path !== p.name && <div className="mt-1 break-all text-[11px] text-plum/55">{p.rel_path}</div>}
    <div className="mt-4 rounded-xl bg-tint/60 p-3">
      <div className="flex items-center justify-between gap-2"><span className="text-xs font-medium">{trashed ? "Recoverable trash" : p.pick?.winner ? "🥇 Winner photo" : p.pick?.picked ? "★ Top pick" : "Recommendation"}</span>
        {rating !== null && <strong className="text-xl tabular-nums">{rating.toFixed(2)}<span className="text-xs font-normal text-plum/50"> / 5</span></strong>}</div>
      <div className="mt-1 text-sm">{p.category}</div>
      {p.pick?.profile && <div className="mt-1 text-xs text-plum/55">Profile · {p.pick.profile}</div>}
    </div>
    <section className="mt-5"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-plum/55">Why this happened</h3>
      <p className="text-[13px] leading-relaxed">{explanation}</p>
      {!!p.decision?.evidence.length && <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-plum/70">{p.decision.evidence.map((reason,i)=><li key={i}>{reason}</li>)}</ul>}
      {p.decision?.kept_path && <p className="mt-2 break-all text-xs">Kept original · {p.decision.kept_path}</p>}
      {p.decision?.previous && <p className="mt-2 text-xs text-plum/60">Previous suggestion · {p.decision.previous.category}: {p.decision.previous.explanation}</p>}
      <div className="mt-2 text-xs text-plum/60"><InfoBadge message={SOURCE_HELP[p.source]??p.source}>{SOURCE_LABEL[p.source]??p.source}</InfoBadge></div>
    </section>
    {!!p.pick?.reasons.length && <section className="mt-5"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-plum/55">Selection notes</h3>
      <ul className="list-disc space-y-1 pl-4 text-[13px]">{p.pick.reasons.map((reason,i)=><li key={i}>{reason}</li>)}</ul>
    </section>}
    {!!p.pick?.parts && <section className="mt-5 space-y-3"><h3 className="text-xs font-semibold uppercase tracking-wide text-plum/55">Algorithm scores</h3>
      {Object.entries(p.pick.parts).filter(([key,value])=>key!=="pareto"&&Number.isFinite(value)).map(([key,value])=>{
        const [label,help]=SCORE_LABELS[key]??[key,"A component of the recommendation score."];const percent=Math.round(Math.max(0,Math.min(1,value))*100);
        return <div key={key}><div className="mb-1 flex justify-between gap-2 text-xs"><InfoBadge message={help}>{label}</InfoBadge><span className="tabular-nums">{percent}%</span></div>
          <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="h-1.5 overflow-hidden rounded-full bg-tint">
            <div className={key==="blocking"?"h-full rounded-full bg-amber-500":"h-full rounded-full bg-plum/65"} style={{width:`${percent}%`}} />
          </div></div>;
      })}
    </section>}
    {p.quality && <section className="mt-5"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-plum/55">Quality checks</h3>
      <p className="text-xs">{p.quality.faces} detected face{p.quality.faces===1?"":"s"}{p.quality.faces_considered ? ` · eyes open on ${p.quality.eyes_open}/${p.quality.faces_considered}`:""}</p>
      {p.quality.flags.length ? <div className="mt-2 space-y-2">{p.quality.flags.map(flag=><InfoBadge key={flag} message={FLAG[flag]?.help??flag} className="block text-xs">{FLAG[flag]?.emoji??"!"} {FLAG[flag]?.label??flag}</InfoBadge>)}</div>
        : <p className="mt-1 text-xs text-plum/55">No enabled quality checks flagged an issue.</p>}
    </section>}
    {!!p.tags?.length && <section className="mt-5"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-plum/55">Search tags</h3>
      <div className="flex flex-wrap gap-1">{p.tags.map(tag=><InfoBadge key={tag.label} message={`${tag.label} · ${tag.source==="metadata"?"file metadata":"local AI suggestion"}`} className="rounded bg-tint px-2 py-1 text-xs">#{tag.label}</InfoBadge>)}</div>
    </section>}
    {!!p.sidecars?.length && <p className="mt-5 break-all text-xs text-plum/55">Attached · {p.sidecars.map(path=>path.split("/").pop()).join(", ")}</p>}
    <p className="mt-5 break-all text-[11px] text-plum/50">Destination · {p.destination}/</p>
  </aside>;
}

/**
 * Full-size viewer for plan items: photos open in a zoomable lightbox (← → to browse, rotate, zoom),
 * videos in a player. Usage: const viewer = useMediaViewer(items); viewer.open(item); render {viewer.node}.
 */
export function useMediaViewer(items: PlanItem[]): { open: (p: PlanItem) => void; node: ReactNode } {
  const photos = useMemo(() => items.filter((p) => p.kind === "image"), [items]);
  const [current, setCurrent] = useState<number | null>(null);
  const [video, setVideo] = useState<PlanItem | null>(null);
  useEffect(() => {
    if (current === null) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setCurrent(null); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [current]);

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
            onChange: (c: number) => setCurrent(previous => previous === null ? null : c),
            imageRender: (img: ReactNode, info: { current: number }) => (
              <div className="grid h-[84vh] max-h-[1100px] w-[96vw] max-w-[1900px] grid-rows-[minmax(0,1fr)_minmax(0,0.8fr)] gap-3 md:grid-cols-[minmax(0,1fr)_340px] md:grid-rows-1">
                <div className="flex min-h-0 min-w-0 items-center justify-center overflow-hidden rounded-xl" aria-label="Photo preview">
                  {isValidElement(img) ? cloneElement(img as ReactElement<ImgHTMLAttributes<HTMLImageElement>>, {style:{...(img.props as ImgHTMLAttributes<HTMLImageElement>).style,maxWidth:"100%",maxHeight:"100%",objectFit:"contain"}}) : img}
                </div>
                {photos[info.current] && <PhotoInfoPanel p={photos[info.current]} />}
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

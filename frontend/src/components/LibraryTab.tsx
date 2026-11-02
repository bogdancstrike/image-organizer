import { ExplainedTag as Tag } from "./PhotoBadge";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { App, Button, Empty, Input, Modal, Segmented, Select, Spin } from "antd";
import { ChevronLeft, ChevronRight, Images, Map as MapIcon, Plane, Search, Sparkles, X } from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  api,
  previewUrl,
  thumbUrl,
  type JobRequest,
  type ImageTag,
  type TagFacets,
  type LibResults,
  type MapPoint,
  type PlacesResult,
  type Strategy,
  type TripsResult,
} from "@/api";
import { Card } from "./ui/card";
import { InfoBadge } from "./PhotoBadge";
import { fmt } from "@/lib/utils";

type View = "search" | "trips" | "map";

interface Props {
  active: boolean;
  folder: string; // library-relative scope (the folder chosen on /sort, incl. subfolders)
  folderLabel: string;
  model: "clip" | "siglip2";
  onSortBy: (strategy: Strategy, extra?: Record<string, unknown>) => void;
}

const EXAMPLES = ["red dress at the beach", "dog in the snow", "sunset over the sea", "wedding rings", "mountain hike", "receipt or document"];
const dateOf = (ts: number) => (ts ? new Date(ts * 1000).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "");

/** A grid of photos (library paths); click opens the viewer. */
function Grid({ items, onOpen }: { items: { path: string; thumb?: string }[]; onOpen: (i: number) => void }) {
  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-8">
      {items.map((it, i) => (
        <button
          key={it.path}
          onClick={() => onOpen(i)}
          className="group relative aspect-square cursor-pointer overflow-hidden rounded-lg bg-tint"
          title={it.path}
        >
          <img
            src={it.thumb ?? thumbUrl(it.path)}
            onError={(e) => {
              const img = e.currentTarget;
              if (!img.dataset.fallback) {
                img.dataset.fallback = "1";
                img.src = thumbUrl(it.path);
              }
            }}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition group-hover:scale-[1.03]"
          />
        </button>
      ))}
    </div>
  );
}

/** Large viewer with keyboard navigation and "Find similar". */
function Viewer({ paths, index, onIndex, onClose, onSimilar, tags }: {
  paths: string[];
  tags?: Record<string, ImageTag[]>;
  index: number | null;
  onIndex: (i: number) => void;
  onClose: () => void;
  onSimilar: (path: string) => void;
}) {
  const open = index !== null && index >= 0 && index < paths.length;
  useEffect(() => {
    if (!open || index === null) return;
    const key = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" && index < paths.length - 1) onIndex(index + 1);
      if (e.key === "ArrowLeft" && index > 0) onIndex(index - 1);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [open, index, paths.length, onIndex]);
  if (!open || index === null) return null;
  const path = paths[index];
  return (
    <Modal open onCancel={onClose} footer={null} width="min(1100px, 96vw)" closeIcon={<X size={18} />} centered>
      <div className="relative flex items-center justify-center" style={{ minHeight: "60vh" }}>
        <img src={previewUrl(path)} alt="" className="max-h-[75vh] max-w-full object-contain" />
        {index > 0 && (
          <button aria-label="Previous" onClick={() => onIndex(index - 1)} className="absolute left-2 rounded-full bg-black/40 p-2 text-white hover:bg-black/60">
            <ChevronLeft size={20} />
          </button>
        )}
        {index < paths.length - 1 && (
          <button aria-label="Next" onClick={() => onIndex(index + 1)} className="absolute right-2 rounded-full bg-black/40 p-2 text-white hover:bg-black/60">
            <ChevronRight size={20} />
          </button>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="min-w-0 truncate text-xs text-plum/60">{path} · {index + 1} / {paths.length}</span>
        <div className="flex flex-wrap gap-1">{tags?.[path]?.map(tag=><InfoBadge key={tag.label} message={`${tag.label} · ${tag.source === "metadata" ? "file metadata" : "local AI tag"}`} className="rounded bg-tint px-1">#{tag.label}</InfoBadge>)}</div>
        <Button icon={<Sparkles size={14} />} onClick={() => onSimilar(path)}>
          Find similar
        </Button>
      </div>
    </Modal>
  );
}

/** Leaflet map: one marker per ~1 km cell, sized by photo count. */
function PhotoMap({ points, onPick }: { points: MapPoint[]; onPick: (p: MapPoint) => void }) {
  const el = useRef<HTMLDivElement>(null);
  const pickRef = useRef(onPick);
  useEffect(() => {
    pickRef.current = onPick;
  }, [onPick]);
  const bounds = useMemo(() => L.latLngBounds(points.map((p) => [p.lat, p.lon] as [number, number])), [points]);

  useEffect(() => {
    const node = el.current;
    if (!node) return;
    const map = L.map(node, { worldCopyJump: true });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap contributors" }).addTo(map);
    const accent = getComputedStyle(document.documentElement).getPropertyValue("--petal").trim() || "#b8467d";
    for (const p of points) {
      L.circleMarker([p.lat, p.lon], {
        radius: Math.min(26, 5 + Math.sqrt(p.count) * 2),
        color: accent,
        weight: 1.5,
        fillColor: accent,
        fillOpacity: 0.45,
      })
        .bindTooltip(`${[p.city, p.country].filter(Boolean).join(", ")} · ${p.count}`)
        .on("click", () => pickRef.current(p))
        .addTo(map);
    }
    map.fitBounds(bounds.pad(0.2), { maxZoom: 12 });
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(node);
    return () => {
      ro.disconnect();
      map.remove();
    };
  }, [points, bounds]);

  return <div ref={el} className="h-[55vh] min-h-[320px] w-full overflow-hidden rounded-xl border border-line" />;
}

/** Library: natural-language search, find similar, trips and a map, scoped to the chosen folder. */
export function LibraryTab({ active, folder, folderLabel, model, onSortBy }: Props) {
  const { message } = App.useApp();
  const [view, setView] = useState<View>("search");
  const [facets, setFacets] = useState<TagFacets | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [indexed, setIndexed] = useState<number | null>(null);
  const [indexing, setIndexing] = useState(false);
  const [q, setQ] = useState("");
  const [res, setRes] = useState<LibResults | null>(null);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [viewer, setViewer] = useState<{ paths: string[]; index: number } | null>(null);
  const [places, setPlaces] = useState<PlacesResult | null>(null);
  const [trips, setTrips] = useState<TripsResult | null>(null);
  const [geoBusy, setGeoBusy] = useState(false);
  const [picked, setPicked] = useState<{ title: string; paths: string[] } | null>(null);
  const reqId = useRef(0);
  const scope = `${folder}|${model}`;
  const [loadedScope, setLoadedScope] = useState(scope);
  const scopeRef = useRef(scope);scopeRef.current=scope;

  // scope changed: results belong to the old folder
  if (loadedScope !== scope) {
    reqId.current++;
    setLoadedScope(scope);
    setSelectedTags([]);
    setFacets(null);
    setRes(null);
    setPlaces(null);
    setTrips(null);
    setPicked(null);
    setTitle("");
  }

  const refreshStatus = useCallback(() => {
    const requested=`${folder}|${model}`;
    api.libStatus(folder, model).then((s) => {if(scopeRef.current===requested)setIndexed(s.indexed);}).catch(() => {if(scopeRef.current===requested)setIndexed(0);});
    api.libTags(folder, model).then(tags=>{if(scopeRef.current===requested)setFacets(tags);}).catch(() => {if(scopeRef.current===requested)setFacets(null);});
  }, [folder, model]);
  useEffect(() => {
    if (active) refreshStatus();
  }, [active, refreshStatus]);

  // trips & map load lazily, once per folder
  useEffect(() => {
    if (!active || view === "search") return;
    if ((view === "trips" && trips) || (view === "map" && places)) return;
    let alive = true;
    setGeoBusy(true);
    const p = view === "trips" ? api.libTrips(folder).then((d) => alive && setTrips(d)) : api.libPlaces(folder).then((d) => alive && setPlaces(d));
    p.catch((e) => alive && message.error((e as Error).message)).finally(() => alive && setGeoBusy(false));
    return () => {
      alive = false;
    };
  }, [active, view, folder, trips, places, message]);

  const run = async (fn: () => Promise<LibResults>, label: string) => {
    const id = ++reqId.current;
    setBusy(true);
    try {
      const r = await fn();
      if (id !== reqId.current) return; // a newer search replaced this one
      setRes(r);
      setTitle(label);
    } catch (e) {
      if (id === reqId.current) message.error((e as Error).message);
    } finally {
      if (id === reqId.current) setBusy(false);
    }
  };
  const search = (text: string, tags = selectedTags) => {
    const t = text.trim() || tags.join(" ");
    if (!t) return;
    setQ(t);
    setView("search");
    run(() => tags.length ? api.libSearch(t, folder, model, tags) : api.libSearch(t, folder, model), `“${t}”`);
  };
  const similar = (path: string) => {
    setViewer(null);
    setView("search");
    run(() => api.libSimilar(path, folder, model), `Similar to ${path.split("/").pop()}`);
  };

  const indexNow = async () => {
    setIndexing(true);
    try {
      const options = { model, near_duplicates: false, auto_tags: true } as unknown as JobRequest["options"];
      const { id } = await api.startJob({ source: folder, strategy: "date", set_id: null, options });
      for (;;) {
        await new Promise((r) => setTimeout(r, 1200));
        const s = await api.job(id);
        if (s.status !== "running") {
          if (s.status !== "done" && s.status !== "applied") throw Error(s.error || "Indexing did not finish. Retry this folder.");
          break;
        }
      }
      refreshStatus();
      message.success("Folder indexed. Search away.");
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setIndexing(false);
    }
  };

  const hits = res?.results ?? [];
  const open = (paths: string[]) => (i: number) => setViewer({ paths, index: i });
  const spinner = (
    <div className="flex flex-col items-center gap-2 py-16 text-xs text-plum/55">
      <Spin /> Reading locations…
    </div>
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Segmented
          value={view}
          onChange={(v) => setView(v as View)}
          options={[
            { value: "search", label: <span className="inline-flex items-center gap-1.5 px-1"><Search size={14} /> Search</span> },
            { value: "trips", label: <span className="inline-flex items-center gap-1.5 px-1"><Plane size={14} /> Trips</span> },
            { value: "map", label: <span className="inline-flex items-center gap-1.5 px-1"><MapIcon size={14} /> Map</span> },
          ]}
        />
        <span className="text-xs text-plum/55">
          In <b>{folderLabel}</b> and its subfolders{indexed !== null && view === "search" ? ` · ${fmt(indexed)} photos searchable` : ""}
        </span>
      </div>

      {view === "search" && (
        <>
          <Input.Search
            size="large"
            allowClear
            placeholder="Describe what you're looking for, e.g. red dress at the beach"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onSearch={text => search(text)}
            enterButton={<span className="inline-flex items-center gap-1.5"><Search size={15} /> Search</span>}
            loading={busy}
            disabled={indexed === 0}
          />
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((e) => (
              <Tag key={e} className="m-0 cursor-pointer" onClick={() => indexed && search(e)}>
                {e}
              </Tag>
            ))}
          </div>
          {!!facets?.tags.length && <div className="rounded-xl border border-line bg-surface/60 p-3">
            <div className="mb-2 flex items-center justify-between gap-2 text-xs text-plum/60">
              <span>Filter by tags · {facets.tagged} tagged photos · selected tags must all match</span>
              {selectedTags.length > 0 && <Button size="small" type="text" onClick={() => { setSelectedTags([]); search(q, []); }}>Clear tags</Button>}
            </div>
            <Select aria-label="Filter image tags" mode="multiple" showSearch allowClear maxCount={12} className="w-full"
              placeholder="Choose subjects, scenes, clothing or lighting…" value={selectedTags}
              options={facets.tags.map(tag=>({value:tag.label,label:`${tag.label} (${tag.count})`}))}
              onChange={tags=>{setSelectedTags(tags);search(q,tags);}} />
          </div>}
          {!!indexed && <div className="flex items-center justify-between gap-3 text-xs text-plum/55">
            <span>{facets ? `${facets.tagged} of ${indexed} photos have automatic tags` : "Local tags complement semantic search."}</span>
            <Button size="small" loading={indexing} onClick={indexNow}>Update search tags</Button>
          </div>}
          {indexed === 0 ? (
            <Card className="p-6 text-center">
              <p className="mb-3 text-sm text-plum/70">
                Nothing here is searchable yet. Search uses what a sort already analyzed: index this folder once (nothing is moved).
              </p>
              <Button type="primary" loading={indexing} onClick={indexNow} icon={<Images size={15} />}>
                Index this folder
              </Button>
            </Card>
          ) : busy && !res ? (
            <div className="flex justify-center py-16"><Spin /></div>
          ) : res ? (
            <div>
              <div className="mb-3 flex items-baseline justify-between gap-2">
                <h3 className="text-[15px] font-semibold text-plum">{title}</h3>
                <span className="text-xs text-plum/50">
                  {res.missing ? "This photo isn't analyzed yet: run a sort on its folder first." : `${hits.length} results${res.took_ms !== undefined ? ` · ${res.took_ms} ms` : ""}`}
                </span>
              </div>
              {hits.length ? <>
                <Grid items={hits} onOpen={open(hits.map((h) => h.path))} />
                <div className="mt-3 space-y-2">{hits.slice(0, 12).filter(hit=>hit.tags?.length).map(hit=><div key={hit.path} className="flex flex-wrap items-center gap-1 text-xs">
                  <span className="mr-1 max-w-52 truncate text-plum/60">{hit.path.split("/").pop()}</span>
                  {hit.tags!.map(tag=><InfoBadge key={tag.label} message={`${tag.label} · ${tag.source === "metadata" ? "file metadata" : "automatic local AI tag; review if needed"}`} className="rounded bg-tint px-1.5 py-0.5">#{tag.label}</InfoBadge>)}
                </div>)}</div>
              </> : <Empty description="No matching photos" />}
            </div>
          ) : (
            <p className="py-10 text-center text-sm text-plum/50">Search by what's in the photo, not by file name. Text inside photos (OCR) counts too.</p>
          )}
        </>
      )}

      {view === "trips" &&
        (geoBusy && !trips ? (
          spinner
        ) : trips && trips.trips.length ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-plum/55">
              <span>
                {trips.trips.length} trips · {fmt(trips.located)} of {fmt(trips.photos)} files have a location
                {trips.home?.city ? ` · home: ${trips.home.city}, ${trips.home.country}` : ""}
              </span>
              <Button size="small" icon={<Plane size={13} />} onClick={() => onSortBy("trips")}>
                Sort into trip folders
              </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {trips.trips.map((t) => (
                <button key={`${t.name}-${t.start}`} className="text-left" onClick={() => setPicked({ title: t.name, paths: t.paths })}>
                  <Card className="p-4 transition hover:bg-tint/40">
                    <div className="flex items-baseline justify-between gap-2">
                      <h3 className="truncate text-[15px] font-semibold text-plum">✈️ {t.name}</h3>
                      <span className="shrink-0 text-xs tabular-nums text-plum/55">{fmt(t.count)}</span>
                    </div>
                    <div className="mb-3 text-[11px] text-plum/50">{dateOf(t.start)} – {dateOf(t.end)}</div>
                    <div className="grid grid-cols-4 gap-1">
                      {t.samples.slice(0, 4).map((p) => (
                        <img key={p} src={thumbUrl(p)} alt="" loading="lazy" className="aspect-square w-full rounded-md bg-tint object-cover" />
                      ))}
                    </div>
                  </Card>
                </button>
              ))}
            </div>
          </>
        ) : (
          <Empty
            className="py-16"
            description={trips ? `No trips found: ${fmt(trips.located)} of ${fmt(trips.photos)} files have GPS. Phones usually save it; many cameras don't.` : "Loading…"}
          />
        ))}

      {view === "map" &&
        (geoBusy && !places ? (
          spinner
        ) : places && places.points.length ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-1.5">
                {places.countries.map((c) => (
                  <Tag key={c.name} className="m-0">{c.name} · {fmt(c.count)}</Tag>
                ))}
              </div>
              <div className="flex gap-2">
                <Button size="small" onClick={() => onSortBy("places", { place_granularity: "country" })}>Sort by country</Button>
                <Button size="small" onClick={() => onSortBy("places", { place_granularity: "city" })}>Sort by city</Button>
              </div>
            </div>
            <PhotoMap points={places.points} onPick={(p) => setPicked({ title: [p.city, p.country].filter(Boolean).join(", "), paths: p.paths })} />
            <p className="text-[11px] text-plum/45">
              {fmt(places.located)} of {fmt(places.photos)} photos have GPS. Place names are looked up offline; map tiles © OpenStreetMap.
            </p>
          </>
        ) : (
          <Empty className="py-16" description={places ? `No photos with GPS in this folder (${fmt(places.photos)} photos checked).` : "Loading…"} />
        ))}

      {picked && view !== "search" && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-[15px] font-semibold text-plum">{picked.title} · {fmt(picked.paths.length)}</h3>
            <Button size="small" type="text" icon={<X size={14} />} onClick={() => setPicked(null)} aria-label="Close" />
          </div>
          <Grid items={picked.paths.map((p) => ({ path: p }))} onOpen={open(picked.paths)} />
        </div>
      )}

      <Viewer
        paths={viewer?.paths ?? []}
        index={viewer?.index ?? null}
        onIndex={(i) => setViewer((v) => (v ? { ...v, index: i } : v))}
        onClose={() => setViewer(null)}
        onSimilar={similar}
        tags={Object.fromEntries(hits.map(hit=>[hit.path,hit.tags??[]]))}
      />
    </div>
  );
}

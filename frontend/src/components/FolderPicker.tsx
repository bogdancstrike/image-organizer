import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { App, Button, Empty, Input, Modal, Spin } from "antd";
import {
  ArrowUp,
  ChevronRight,
  Clock,
  Download,
  FileText,
  Film,
  FolderClosed,
  FolderOpen,
  HardDrive,
  Home,
  Image as ImageIcon,
  Images,
  Monitor,
  Search,
  Smartphone,
} from "lucide-react";
import { api, thumbUrl, type FolderListing, type Health, type Place } from "@/api";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";

interface Props {
  open: boolean;
  value: string;
  health: Health | null;
  onClose: () => void;
  onChoose: (path: string) => void;
}

const RECENT_KEY = "aio.recentFolders";
const PLACE_ICON = { pictures: ImageIcon, downloads: Download, desktop: Monitor, documents: FileText, videos: Film, dcim: Smartphone };

/** Shows a library-relative path the way the user knows it (host path when known). */
export function displayPath(health: Health | null, rel: string) {
  const base = (health?.library_host_path || "/library").replace(/\/+$/, "");
  return rel ? `${base}/${rel}` : base;
}

/** Typed / pasted path → library-relative path (accepts host paths like /home/me/Pictures/x, or relative ones). */
function toRelative(health: Health | null, typed: string): string {
  let p = typed.trim().replace(/\\/g, "/");
  const bases = [health?.library_host_path, "/library", "~"].filter(Boolean).map((b) => (b as string).replace(/\/+$/, ""));
  for (const b of bases) {
    if (p === b) return "";
    if (p.startsWith(b + "/")) {
      p = p.slice(b.length + 1);
      break;
    }
  }
  return p.replace(/^\/+|\/+$/g, "");
}

function loadRecent(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string").slice(0, 6) : [];
  } catch {
    return [];
  }
}

function saveRecent(path: string) {
  try {
    const next = [path, ...loadRecent().filter((p) => p !== path)].slice(0, 6);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable */
  }
}

/** Browse the mounted library and pick the working folder: places, recent, typed paths, filter, keyboard. */
export function FolderPicker({ open, value, health, onClose, onChoose }: Props) {
  const { message } = App.useApp();
  const { t } = useI18n();
  const [path, setPath] = useState(value);
  const [data, setData] = useState<FolderListing | null>(null);
  const [loading, setLoading] = useState(false);
  const [places, setPlaces] = useState<Place[]>([]);
  const [recent, setRecent] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const [typed, setTyped] = useState<string | null>(null); // null = not editing the path bar
  const [cursor, setCursor] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    setPath(value);
    setRecent(loadRecent());
    api.places().then(setPlaces).catch(() => setPlaces([]));
  }, [open, value]);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
    setFilter("");
    setCursor(0);
    api
      .folders(path)
      .then((d) => alive && setData(d))
      .catch((e) => {
        if (!alive) return;
        message.error(e.message);
        if (path) setPath("");
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [open, path, message]);

  const shown = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return (data?.folders ?? []).filter((f) => !q || f.name.toLowerCase().includes(q));
  }, [data, filter]);

  const choose = useCallback(
    (p: string) => {
      saveRecent(p);
      onChoose(p);
    },
    [onChoose],
  );
  const up = () => path && setPath(path.split("/").slice(0, -1).join("/"));

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-i="${cursor}"]`)?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  const onKey = (e: KeyboardEvent) => {
    if ((e.target as HTMLElement).tagName === "INPUT" && e.key !== "ArrowDown" && e.key !== "ArrowUp" && e.key !== "Enter") return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, shown.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter" && shown[cursor]) {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) choose(shown[cursor].path);
      else setPath(shown[cursor].path);
    } else if (e.key === "Backspace" && !filter) {
      e.preventDefault();
      up();
    }
  };

  const parts = path ? path.split("/") : [];
  const rootLabel = health?.library_host_path || health?.library_name || "Library";

  const Side = ({ icon: Icon, label, to, title }: { icon: typeof Home; label: string; to: string; title?: string }) => (
    <button
      onClick={() => setPath(to)}
      title={title ?? label}
      className={cn(
        "flex w-full shrink-0 cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[13px] text-plum/80 hover:bg-tint sm:w-full",
        path === to && "bg-tint font-medium text-plum",
      )}
    >
      <Icon size={14} className="shrink-0 text-plum/55" />
      <span className="truncate">{label}</span>
    </button>
  );

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        <span className="inline-flex items-center gap-2">
          <FolderOpen size={18} /> {t("fp.title")}
        </span>
      }
      width={860}
      styles={{ body: { paddingTop: 4 } }}
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="min-w-0 truncate text-left text-xs text-plum/60">
            <Images size={12} className="mr-1 inline" />
            {data ? `${data.media_count} photos & videos directly in “${data.name}”` : ""}
          </span>
          <div className="flex gap-2">
            <Button onClick={onClose}>{t("ed.cancel")}</Button>
            <Button type="primary" onClick={() => choose(path)}>
              {t("fp.use")}
            </Button>
          </div>
        </div>
      }
    >
      <div className="flex flex-col gap-3 sm:flex-row" onKeyDown={onKey}>
        {/* places + recent */}
        <nav className="flex gap-1 overflow-x-auto pb-1 sm:w-48 sm:shrink-0 sm:flex-col sm:overflow-visible sm:pb-0">
          <div className="hidden px-2.5 pb-1 label-caps sm:block">Places</div>
          <Side icon={Home} label="Home" to="" title={rootLabel} />
          {places.map((p) => (
            <Side key={p.path} icon={PLACE_ICON[p.kind] ?? FolderClosed} label={p.name} to={p.path} />
          ))}
          {recent.length > 0 && <div className="hidden px-2.5 pb-1 pt-3 label-caps sm:block">Recent</div>}
          {recent.map((r) => (
            <Side key={`r-${r}`} icon={Clock} label={r.split("/").pop() || "Home"} to={r} title={displayPath(health, r)} />
          ))}
        </nav>

        <div className="min-w-0 flex-1">
          {/* path bar */}
          <div className="mb-2 flex items-center gap-1.5">
            <Button size="small" icon={<ArrowUp size={14} />} disabled={!path} onClick={up} aria-label="Up one folder" />
            {typed === null ? (
              <div
                role="button"
                tabIndex={0}
                title="Click to type or paste a path"
                onClick={() => setTyped(displayPath(health, path))}
                onKeyDown={(e) => e.key === "Enter" && setTyped(displayPath(health, path))}
                className="flex min-w-0 flex-1 cursor-text items-center gap-0.5 overflow-hidden rounded-md border border-line bg-surface/60 px-2 py-1 text-[12px]"
              >
                <button onClick={(e) => (e.stopPropagation(), setPath(""))} className="inline-flex shrink-0 items-center gap-1 text-plum/70 hover:text-plum">
                  <HardDrive size={12} /> {parts.length ? "" : rootLabel}
                </button>
                {parts.map((p, i) => (
                  <span key={i} className="inline-flex min-w-0 items-center">
                    <ChevronRight size={12} className="shrink-0 text-plum/35" />
                    <button
                      onClick={(e) => (e.stopPropagation(), setPath(parts.slice(0, i + 1).join("/")))}
                      className={cn("truncate hover:text-plum", i === parts.length - 1 ? "font-medium text-plum" : "text-plum/70")}
                    >
                      {p}
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <Input
                size="small"
                autoFocus
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                onBlur={() => setTyped(null)}
                onKeyDown={(e) => {
                  if (e.key === "Escape") setTyped(null);
                  if (e.key === "Enter") {
                    setPath(toRelative(health, typed));
                    setTyped(null);
                  }
                  e.stopPropagation();
                }}
                placeholder={`${rootLabel}/Pictures/2025`}
              />
            )}
          </div>
          <Input
            size="small"
            allowClear
            prefix={<Search size={13} className="text-plum/40" />}
            placeholder="Filter folders"
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setCursor(0);
            }}
            className="mb-2"
          />

          <div ref={listRef} tabIndex={0} className="h-[46vh] min-h-[220px] overflow-y-auto rounded-xl border border-line bg-surface/60 p-1.5 outline-none">
            {loading && !data ? (
              <div className="flex h-full items-center justify-center">
                <Spin />
              </div>
            ) : shown.length === 0 ? (
              <Empty className="py-8" description={filter ? "No folder matches" : "No subfolders here: you can use this folder"} />
            ) : (
              shown.map((f, i) => (
                <button
                  key={f.path}
                  data-i={i}
                  onClick={() => setPath(f.path)}
                  onDoubleClick={() => choose(f.path)}
                  onMouseEnter={() => setCursor(i)}
                  className={cn(
                    "flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] text-plum",
                    i === cursor ? "bg-tint" : "hover:bg-tint",
                    loading && "opacity-60",
                  )}
                >
                  <FolderClosed size={16} className="shrink-0 text-plum/60" />
                  <span className="min-w-0 flex-1 truncate">{f.name}</span>
                  {f.media_count > 0 && <span className="rounded-full bg-tint px-2 py-0.5 text-[11px] tabular-nums text-plum/70">{f.media_count}</span>}
                  {f.has_children && <ChevronRight size={14} className="text-plum/40" />}
                </button>
              ))
            )}
          </div>

          {/* what is in here */}
          {data?.samples && data.samples.length > 0 && (
            <div className="mt-2 flex gap-1.5 overflow-hidden">
              {data.samples.slice(0, 8).map((s) => (
                <img key={s} src={thumbUrl(s)} alt="" loading="lazy" className="h-14 w-14 shrink-0 rounded-md bg-tint object-cover" />
              ))}
            </div>
          )}
          <p className="mt-2 text-[11px] text-plum/50">
            Click a folder to open it, double-click (or Ctrl+Enter) to choose it. ↑ ↓ to move, Enter to open, Backspace to go up. Click the path to paste one.
          </p>
        </div>
      </div>
    </Modal>
  );
}

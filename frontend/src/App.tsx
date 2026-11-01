import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, App as AntApp, Button as AntButton, Tooltip } from "antd";
import { History, SlidersHorizontal, Square, Sparkles, Undo2, RefreshCw, ChevronDown, FolderOpen } from "lucide-react";
import { GithubOutlined } from "@ant-design/icons";
import { api, subscribe, type CategorySet, type Health, type JobCategory, type JobEvent, type PlanItem, type Usage } from "./api";
import { SortEngine } from "./anim/engine";
import { Logo, LogoMark } from "./components/Logo";
import { Stats } from "./components/Stats";
import { CategoryCard, GhostCard } from "./components/CategoryCard";
import { Flower } from "./components/Flower";
import { SettingsDrawer, SettingsPanel } from "./components/SettingsDrawer";
import { ReviewTab } from "./components/ReviewTab";
import { CategoriesTab } from "./components/CategoriesTab";
import { CategoryEditor } from "./components/CategoryEditor";
import { HistoryDrawer, HistoryList } from "./components/HistoryDrawer";
import { Segmented } from "antd";
import { LayoutGrid, TableProperties, Tags, Settings2 } from "lucide-react";
import { FilesDrawer } from "./components/FilesDrawer";
import { FolderPicker, displayPath } from "./components/FolderPicker";
import { Button } from "./components/ui/button";
import { Badge } from "./components/ui/badge";
import { Card } from "./components/ui/card";
import { loadSettings, saveSettings, type UiSettings } from "./settings";
import { ThemeSwitcher, useTheme } from "./theme";
import { fmt, prefersReducedMotion } from "./lib/utils";

type Status = "idle" | "running" | "done" | "error" | "cancelled" | "applied" | "undone";

interface JobState {
  id: string | null;
  status: Status;
  phase: string;
  total: number;
  analyzed: number;
  categories: JobCategory[];
  sourceName: string | null;
  warnings: string[];
  usage: Usage | null;
  error: string | null;
  runId: string | null;
  errors: number;
  context: { theme: string; source?: string } | null;
}

const INITIAL: JobState = {
  id: null,
  status: "idle",
  phase: "",
  total: 0,
  analyzed: 0,
  categories: [],
  sourceName: null,
  warnings: [],
  usage: null,
  error: null,
  runId: null,
  errors: 0,
  context: null,
};

const DUP = "_duplicates";
const TABS = ["sort", "review", "categories", "history", "settings"] as const;
type Tab = (typeof TABS)[number];
const tabFromPath = (): Tab => {
  const seg = window.location.pathname.replace(/^\/+|\/+$/g, "").split("/")[0];
  return (TABS as readonly string[]).includes(seg) ? (seg as Tab) : "sort";
};
const cardKey = (catId: string, kind: string) => (catId === DUP ? "dup" : `${kind}:${catId}`);

export default function App() {
  const { message, notification } = AntApp.useApp();
  const [settings, setSettingsState] = useState<UiSettings>(loadSettings);
  const [health, setHealth] = useState<Health | null>(null);
  const [presets, setPresets] = useState<CategorySet[]>([]);
  const [customSets, setCustomSets] = useState<CategorySet[]>([]);
  const [job, setJob] = useState<JobState>(INITIAL);
  const [landed, setLanded] = useState<Record<string, number>>({});
  const [landedKinds, setLandedKinds] = useState({ image: 0, video: 0 });
  const [plan, setPlan] = useState<PlanItem[]>([]);
  const [drawer, setDrawer] = useState<null | "settings" | "history" | "editor" | "folder">(null);
  const [filesFor, setFilesFor] = useState<{ title: string; catId: string; kind: string | null } | null>(null);
  const [applying, setApplying] = useState(false);
  const [editorTarget, setEditorTarget] = useState<{ set: CategorySet | null; mode: "edit" | "copy" | "new" } | null>(null);
  const [tab, setTabState] = useState<Tab>(tabFromPath);
  const setTab = useCallback((t: Tab) => {
    setTabState(t);
    if (window.location.pathname !== `/${t}`) window.history.pushState({ tab: t }, "", `/${t}`);
  }, []);
  useEffect(() => {
    const onPop = () => setTabState(tabFromPath());
    window.addEventListener("popstate", onPop);
    if (window.location.pathname === "/") window.history.replaceState({ tab: "sort" }, "", "/sort");
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const stageRef = useRef<HTMLDivElement>(null);
  const pileRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<SortEngine | null>(null);
  const slotEls = useRef(new Map<string, HTMLElement>());
  const kinds = useRef(new Map<string, string>());
  const landedBuf = useRef<{ keys: Record<string, number>; image: number; video: number }>({ keys: {}, image: 0, video: 0 });
  const flushRaf = useRef(0);
  const lastSeq = useRef(-1);
  const unsub = useRef<null | (() => void)>(null);

  const { theme } = useTheme();
  useEffect(() => {
    // parent effects (data-theme) run after ours: wait a frame before re-reading CSS variables
    const id = requestAnimationFrame(() => engineRef.current?.refreshTheme());
    return () => cancelAnimationFrame(id);
  }, [theme]);

  const setSettings = (s: UiSettings) => {
    setSettingsState(s);
    saveSettings(s);
  };

  // ---- boot
  useEffect(() => {
    api.health().then(setHealth).catch(() => message.error("Backend is not reachable"));
    api.presets().then(setPresets).catch(() => {});
    api.sets().then(setCustomSets).catch(() => {});
  }, [message]);

  // ---- animation engine
  useEffect(() => {
    if (!canvasRef.current) return;
    const engine = new SortEngine(canvasRef.current, {
      stage: () => stageRef.current,
      pile: () => pileRef.current,
      slotArea: (key) => slotEls.current.get(key) ?? null,
      onLand: (key, id) => {
        const buf = landedBuf.current;
        buf.keys[key] = (buf.keys[key] ?? 0) + 1;
        if (kinds.current.get(id) === "video") buf.video++;
        else buf.image++;
        if (!flushRaf.current) {
          flushRaf.current = requestAnimationFrame(() => {
            flushRaf.current = 0;
            setLanded({ ...landedBuf.current.keys });
            setLandedKinds({ image: landedBuf.current.image, video: landedBuf.current.video });
          });
        }
      },
    });
    engine.reduced = prefersReducedMotion();
    engineRef.current = engine;
    return () => engine.destroy();
  }, []);

  const slotRef = useCallback(
    (key: string) => (el: HTMLDivElement | null) => {
      if (el) slotEls.current.set(key, el);
      else slotEls.current.delete(key);
    },
    [],
  );

  // ---- events
  const handleEvents = useCallback(
    (evs: JobEvent[]) => {
      const engine = engineRef.current!;
      const patch: Partial<JobState> = {};
      let warnings: string[] | null = null;
      for (const e of evs) {
        if (e.seq <= lastSeq.current) continue;
        lastSeq.current = e.seq;
        switch (e.type) {
          case "phase":
            patch.phase = e.phase;
            engine.setWobble(e.phase === "analyzing" || e.phase === "deduplicating" || e.phase === "categorizing");
            break;
          case "scanned":
            engine.setExpected(e.total);
            patch.total = e.total;
            patch.sourceName = e.source_name;
            break;
          case "file":
            kinds.current.set(e.id, e.kind);
            engine.addFile(e.id, e.thumb);
            break;
          case "file_error":
            patch.errors = (patch.errors ?? 0) + 1;
            break;
          case "progress":
            patch.analyzed = e.analyzed;
            break;
          case "categories": {
            const cats = e.categories as JobCategory[];
            patch.categories = cats;
            engine.expectAssigns(cats.reduce((n, c) => n + c.photos + c.videos, 0));
            break;
          }
          case "assign":
            engine.assign(e.id, cardKey(e.category_id, e.kind));
            break;
          case "context":
            patch.context = { theme: e.theme, source: e.source };
            break;
          case "warning":
            warnings = [...(warnings ?? []), e.message];
            break;
          case "done":
            patch.status = "done";
            patch.phase = "done";
            patch.usage = e.usage;
            patch.warnings = e.warnings ?? [];
            break;
          case "cancelled":
            patch.status = "cancelled";
            break;
          case "error":
            patch.status = "error";
            patch.error = e.message;
            break;
        }
      }
      setJob((j) => ({
        ...j,
        ...patch,
        errors: j.errors + (patch.errors ?? 0),
        warnings: patch.warnings ?? (warnings ? [...j.warnings, ...warnings] : j.warnings),
      }));
    },
    [],
  );

  // restore the last finished sort after a page reload (state lives on the server)
  useEffect(() => {
    let id: string | null = null;
    try {
      id = localStorage.getItem("aio.lastJob");
    } catch {
      /* storage unavailable */
    }
    if (!id) return;
    api
      .job(id)
      .then((s) => {
        if (!s.plan || !["done", "applied"].includes(s.status)) return;
        const engine = engineRef.current;
        if (!engine) return;
        const src = String((s as unknown as { request?: { source?: string } }).request?.source ?? "");
        engine.reset();
        engine.reduced = true; // snap straight into the cards, no replay of the animation
        landedBuf.current = { keys: {}, image: 0, video: 0 };
        lastSeq.current = Number.MAX_SAFE_INTEGER;
        setJob({
          ...INITIAL,
          id: s.id,
          status: s.status === "applied" ? "applied" : "done",
          phase: "done",
          total: s.stats.total ?? s.plan.length,
          analyzed: s.stats.analyzed ?? 0,
          categories: s.categories,
          sourceName: src ? src.split("/").pop()! : null,
          warnings: s.warnings,
          usage: s.usage,
          runId: s.run_id,
          errors: s.errors.length,
          context: s.context ?? null,
        });
        setPlan(s.plan);
        engine.setExpected(s.plan.length);
        for (const p of s.plan) {
          kinds.current.set(p.file_id, p.kind);
          engine.addFile(p.file_id, p.thumb);
        }
        engine.expectAssigns(s.plan.length);
        for (const p of s.plan) engine.assign(p.file_id, cardKey(p.category_id, p.kind));
      })
      .catch(() => {
        /* job is gone (server restarted): start fresh */
      });
  }, []);

  // fetch the full plan once a job is done
  useEffect(() => {
    if (job.status === "done" && job.id) api.job(job.id).then((s) => setPlan(s.plan ?? [])).catch(() => {});
    if (job.status === "error" && job.error) message.error(job.error);
  }, [job.status, job.id, job.error, message]);

  const startSort = async () => {
    unsub.current?.();
    engineRef.current?.reset();
    if (engineRef.current) engineRef.current.reduced = prefersReducedMotion();
    slotEls.current.clear();
    kinds.current.clear();
    landedBuf.current = { keys: {}, image: 0, video: 0 };
    setLanded({});
    setLandedKinds({ image: 0, video: 0 });
    setPlan([]);
    lastSeq.current = -1;
    setJob({ ...INITIAL, status: "running", phase: "starting" });
    const s = settings;
    if (s.strategy === "custom" && !s.customSetId) {
      setJob(INITIAL);
      message.info("Create your own category set first");
      setDrawer("editor");
      return;
    }
    try {
      const { id } = await api.startJob({
        source: s.source,
        strategy: s.strategy,
        set_id: s.strategy === "preset" ? s.presetId : s.strategy === "custom" ? s.customSetId : null,
        options: {
          min_confidence: s.minConfidence,
          near_duplicates: s.nearDuplicates,
          split_media: s.splitMedia,
          ai_assist: s.aiAssist && !!health?.ai_available,
          date_granularity: s.dateGranularity,
          max_clusters: s.maxClusters,
          output_dir: s.outputMode === "direct" ? "" : s.outputDir.trim() || "Organized",
          recursive: s.recursive,
          pair_sidecars: s.pairSidecars,
          quality: s.quality,
          focus: s.focus,
          granularity: s.granularity,
          ai: s.ai,
        },
      });
      setJob((j) => ({ ...j, id }));
      try {
        localStorage.setItem("aio.lastJob", id);
      } catch {
        /* storage unavailable */
      }
      unsub.current = subscribe(id, handleEvents, () => {});
    } catch (e) {
      setJob({ ...INITIAL, status: "error", error: (e as Error).message });
    }
  };

  const stop = async () => {
    if (job.id) await api.cancel(job.id).catch(() => {});
  };

  const applyPlan = async () => {
    if (!job.id) return;
    setApplying(true);
    try {
      const r = await api.apply(job.id, settings.applyMode);
      setJob((j) => ({ ...j, status: "applied", runId: r.run_id }));
      const key = `apply-${r.run_id}`;
      notification.success({
        key,
        title: `${settings.applyMode === "copy" ? "Copied" : "Moved"} ${fmt(r.moved)} files`,
        description: r.failed.length
          ? `${r.failed.length} files could not be moved. See History.`
          : `Everything is sorted in ${settings.outputMode === "direct" ? "the folder" : `${settings.outputDir || "Organized"}/`}. Changed your mind?`,
        duration: 12,
        btn: (
          <AntButton
            size="small"
            icon={<Undo2 size={13} />}
            onClick={async () => {
              notification.destroy(key);
              await undoRun(r.run_id);
            }}
          >
            Undo
          </AntButton>
        ),
      } as Parameters<typeof notification.success>[0]);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setApplying(false);
    }
  };

  const undoRun = async (runId: string) => {
    try {
      const r = await api.undo(runId);
      message.success(`Restored ${r.undo?.restored ?? 0} files`);
      setJob((j) => (j.runId === runId ? { ...j, status: "undone" } : j));
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  // ---- derived
  const running = job.status === "running";
  const planned = job.categories.reduce((n, c) => n + c.photos + c.videos, 0);
  const landedTotal = landedKinds.image + landedKinds.video;
  const settled = job.status !== "running" && job.status !== "idle" && landedTotal >= planned;
  const photoCats = job.categories.filter((c) => c.id !== DUP && c.photos > 0);
  const videoCats = job.categories.filter((c) => c.id !== DUP && c.videos > 0);
  const dupCat = job.categories.find((c) => c.id === DUP);
  const noVideos = job.categories.length > 0 && videoCats.length === 0;
  const folderName =
    job.sourceName ??
    (settings.source
      ? settings.source.split("/").pop()
      : health?.library_host_path?.split("/").filter(Boolean).pop() ?? health?.library_name) ??
    "Library";
  const activeSet =
    settings.strategy === "preset"
      ? presets.find((p) => p.id === settings.presetId)
      : settings.strategy === "custom"
        ? customSets.find((p) => p.id === settings.customSetId)
        : undefined;

  const stats = {
    total: job.total,
    photos: landedKinds.image - 0,
    videos: landedKinds.video,
    folders: Object.entries(landed).filter(([k, v]) => k !== "dup" && v > 0).length,
    duplicates: landed["dup"] ?? 0,
  };

  const statusText = useMemo(() => {
    switch (job.status) {
      case "idle":
        return "Ready when you are";
      case "running":
        if (job.phase === "scanning" || job.phase === "starting") return "Looking for photos & videos…";
        if (job.phase === "analyzing") return `Looking at ${fmt(job.analyzed)} / ${fmt(job.total)}…`;
        if (job.phase === "deduplicating") return "Finding duplicates…";
        if (job.phase === "checking") return "Checking sharpness, eyes & smiles…";
        return "Sorting into folders…";
      case "done":
        return settled ? "Sorted, nothing moved yet. Review & apply" : "Sorting into folders…";
      case "applied":
        return "Applied ✓";
      case "undone":
        return "Undone, all files are back";
      case "cancelled":
        return "Stopped";
      case "error":
        return "Something went wrong";
    }
  }, [job.status, job.phase, job.analyzed, job.total, settled]);

  const strategyLabel =
    settings.strategy === "preset"
      ? `Preset · ${activeSet?.name ?? settings.presetId}`
      : settings.strategy === "custom"
        ? `My categories · ${activeSet?.name ?? "none"}`
        : settings.strategy === "auto"
          ? "Auto-discover"
          : settings.strategy === "cull"
            ? "Culling · keepers & rejects"
            : `By date · ${settings.dateGranularity}`;

  const filesItems = useMemo(
    () =>
      filesFor
        ? plan.filter((p) => p.category_id === filesFor.catId && (filesFor.kind === null || p.kind === filesFor.kind))
        : [],
    [plan, filesFor],
  );

  const showGhosts = running && job.categories.length === 0;
  const showFlower = !running && (job.status === "idle" || settled || job.status === "cancelled" || job.status === "error");
  const caption =
    job.status === "applied"
      ? "…not anymore ✿"
      : job.status === "idle" || job.status === "undone"
        ? "a total mess"
        : job.status === "done"
          ? job.total === 0
            ? "nothing to sort here"
            : "a total mess, sorted"
          : job.status === "error"
            ? "oops"
            : "paused";

  return (
    <div className="mx-auto max-w-[1400px] px-4 pb-16 pt-5 sm:px-8">
      {/* header */}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <Logo />
        <div className="flex items-center gap-1.5">
          <span className="mr-2 hidden text-xs text-plum/55 md:inline">{statusText}</span>
          <div className="mr-1">
            <ThemeSwitcher />
          </div>
          <Tooltip title="History & undo">
            <Button variant="ghost" size="icon" onClick={() => setDrawer("history")} aria-label="History">
              <History size={18} />
            </Button>
          </Tooltip>
          <Tooltip title="Settings">
            <Button variant="ghost" size="icon" onClick={() => setDrawer("settings")} aria-label="Settings">
              <SlidersHorizontal size={18} />
            </Button>
          </Tooltip>
          {running ? (
            <Button variant="soft" onClick={stop}>
              <Square size={14} /> Stop
            </Button>
          ) : (
            <Button onClick={startSort} disabled={!health?.library_ok}>
              <LogoMark className="h-5 w-5" /> Sort
            </Button>
          )}
        </div>
      </header>

      <nav className="mt-6 overflow-x-auto">
        <Segmented
          value={tab}
          onChange={(v) => setTab(v as typeof tab)}
          options={[
            { value: "sort", label: <span className="inline-flex items-center gap-1.5 px-1"><LayoutGrid size={14} />Sort</span> },
            {
              value: "review",
              label: (
                <span className="inline-flex items-center gap-1.5 px-1">
                  <TableProperties size={14} />Review{plan.length ? <span className="text-plum/45">{fmt(plan.length)}</span> : null}
                </span>
              ),
            },
            { value: "categories", label: <span className="inline-flex items-center gap-1.5 px-1"><Tags size={14} />Categories</span> },
            { value: "history", label: <span className="inline-flex items-center gap-1.5 px-1"><History size={14} />History</span> },
            { value: "settings", label: <span className="inline-flex items-center gap-1.5 px-1"><Settings2 size={14} />Settings</span> },
          ]}
        />
      </nav>

      <div className={tab === "sort" ? "" : "hidden"}>
      {/* headline */}
      <section className="mt-10">
        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          <Badge variant="outline">{strategyLabel}</Badge>
          <Badge variant="outline">{settings.recursive ? "incl. subfolders" : "this folder only"}</Badge>
          {job.context?.theme && (
            <Badge>
              <Sparkles size={11} /> Looks like: {job.context.theme}
            </Badge>
          )}
          {settings.aiAssist && health?.ai_available && settings.strategy !== "auto" && settings.strategy !== "date" && (
            <Badge>
              <Sparkles size={11} /> AI assist
            </Badge>
          )}
          {settings.quality.enabled && settings.strategy !== "cull" && (
            <Badge>Quality checks · {settings.quality.action === "reject" ? "rejects set aside" : "tag only"}</Badge>
          )}
          {settings.strategy === "auto" && health?.ai_available && (
            <Badge>
              <Sparkles size={11} /> AI names
            </Badge>
          )}
          {running && (
            <span className="ml-1 inline-flex items-center gap-1.5 text-xs text-plum/55 md:hidden">
              <LogoMark spinning className="h-3.5 w-3.5" /> {statusText}
            </span>
          )}
        </div>
        <h1 className="text-[38px] font-semibold leading-[1.05] tracking-tight sm:text-[56px]">
          Sorting my{" "}
          <button
            onClick={() => !running && setDrawer("folder")}
            disabled={running}
            title="Choose another folder"
            className="group inline-flex cursor-pointer items-baseline gap-1 rounded-xl px-1 font-serif text-[1.12em] font-normal italic decoration-petal decoration-2 underline-offset-[10px] hover:underline disabled:cursor-default disabled:no-underline"
          >
            {folderName}
            <ChevronDown className="h-6 w-6 self-center text-plum/40 transition-transform group-hover:translate-y-0.5 sm:h-8 sm:w-8" />
          </button>{" "}
          folder
        </h1>
      </section>

      <button
        onClick={() => !running && setDrawer("folder")}
        className="mt-3 inline-flex max-w-full cursor-pointer items-center gap-1.5 truncate text-xs text-plum/55 hover:text-plum"
      >
        <FolderOpen size={13} className="shrink-0" />
        <span className="truncate">
          {displayPath(health, settings.source)} → {settings.outputMode === "direct" ? "sorted folders directly inside" : `${settings.outputDir || "Organized"}/`}
        </span>
      </button>

      <div className="mt-7">
        <Stats values={stats} />
      </div>

      </div>
      {(tab === "sort" || tab === "review") && (
      <>
      {/* review / apply bar */}
      {(settled && job.status === "done" && job.total > 0) || job.status === "applied" || job.status === "undone" ? (
        <Card className="pop-in mt-7 flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="text-[13px] text-plum/75">
            {job.status === "applied" ? (
              <>Done. Your files are in <b>{displayPath(health, settings.source)}{settings.outputMode === "direct" ? "" : `/${settings.outputDir || "Organized"}`}/</b>.</>
            ) : job.status === "undone" ? (
              <>Undone. Every file is back where it was.</>
            ) : (
              <>
                {fmt(planned)} files planned into <b>{stats.folders}</b> folders
                {stats.duplicates ? <>, <b>{stats.duplicates}</b> duplicates set aside</> : null}
                {job.errors ? <>, {job.errors} unreadable skipped</> : null}. Nothing has been touched yet.
              </>
            )}
            {job.usage && (
              <span className="ml-2 text-plum/45">
                · AI: {job.usage.calls} call{job.usage.calls === 1 ? "" : "s"},{" "}
                {fmt(job.usage.input_tokens + job.usage.output_tokens)} tokens
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="soft" onClick={startSort}>
              <RefreshCw size={14} /> Re-run
            </Button>
            {job.status === "done" && (
              <Button onClick={applyPlan} disabled={applying}>
                {applying ? "Applying…" : settings.applyMode === "copy" ? "Apply · copy files" : "Apply · move files"}
              </Button>
            )}
            {job.status === "applied" && job.runId && (
              <Button variant="soft" onClick={() => undoRun(job.runId!)}>
                <Undo2 size={14} /> Undo
              </Button>
            )}
          </div>
        </Card>
      ) : null}
      {job.warnings.length > 0 && (
        <Alert className="mt-3" type="warning" showIcon title={job.warnings.join(" · ")} closable />
      )}

      </>
      )}

      {tab === "review" && (
        <div className="mt-6">
          <ReviewTab
            jobId={job.id}
            editable={job.status === "done"}
            plan={plan}
            categories={job.categories}
            onChanged={(changed, cats) => {
              const byId = new Map(changed.map((c) => [c.file_id, c]));
              setPlan((old) => old.map((p) => byId.get(p.file_id) ?? p));
              setJob((j) => ({ ...j, categories: cats }));
            }}
          />
        </div>
      )}
      {tab === "categories" && (
        <div className="mt-8">
          <CategoriesTab
            presets={presets}
            customSets={customSets}
            activeId={settings.strategy === "preset" ? settings.presetId : settings.strategy === "custom" ? settings.customSetId : null}
            onUse={(set, custom) => {
              setSettings(custom ? { ...settings, strategy: "custom", customSetId: set.id } : { ...settings, strategy: "preset", presetId: set.id });
              message.success(`Using “${set.name}”. Press Sort when ready`);
              setTab("sort");
            }}
            onEdit={(set, mode) => {
              setEditorTarget({ set, mode });
              setDrawer("editor");
            }}
          />
        </div>
      )}
      {tab === "history" && (
        <Card className="mt-8 max-w-3xl p-4">
          <HistoryList active={tab === "history"} onUndone={(id) => setJob((j) => (j.runId === id ? { ...j, status: "undone" } : j))} />
        </Card>
      )}
      {tab === "settings" && (
        <div className="mt-8">
          <SettingsPanel
            layout="page"
            settings={settings}
            onChange={setSettings}
            presets={presets}
            customSets={customSets}
            health={health}
            onEditCategories={() => setDrawer("editor")}
            onPickFolder={() => setDrawer("folder")}
          />
        </div>
      )}

      <div className={tab === "sort" ? "" : "hidden"}>
      {/* stage */}
      <div
        ref={stageRef}
        className={
          "relative mt-8 grid gap-6 " +
          (noVideos
            ? "lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)_minmax(0,0.55fr)]"
            : "lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,1fr)]")
        }
      >
        <section className="order-2 lg:order-1">
          <h2 className="mb-3 flex items-center gap-2 font-serif text-[22px] italic text-plum/80">
            <span className="h-1.5 w-1.5 rounded-full bg-petal" /> Photos
          </h2>
          <div className={"grid gap-3 " + (noVideos ? "grid-cols-2 xl:grid-cols-3" : "grid-cols-2")}>
            {showGhosts &&
              (activeSet ? activeSet.categories : Array.from({ length: 6 }, () => null)).map((c, i) => (
                <GhostCard key={c?.id ?? i} name={c?.name} index={i} />
              ))}
            {photoCats.map((c, i) => (
              <CategoryCard
                key={c.id}
                index={i}
                name={c.name}
                emoji={c.emoji}
                count={landed[cardKey(c.id, "image")] ?? 0}
                total={c.photos}
                slotRef={slotRef(cardKey(c.id, "image"))}
                onClick={() => setFilesFor({ title: `${c.name} · photos`, catId: c.id, kind: "image" })}
              />
            ))}
          </div>
        </section>

        <section
          ref={pileRef}
          className="relative order-1 flex min-h-[360px] items-center justify-center lg:order-2 lg:min-h-[600px]"
        >
          {showFlower && <Flower caption={caption} />}
          {running && job.phase !== "analyzing" && job.total === 0 && (
            <LogoMark spinning className="h-10 w-10 opacity-60" />
          )}
        </section>

        <section className="order-3">
          <h2 className="mb-3 flex items-center gap-2 font-serif text-[22px] italic text-plum/80">
            <span className="h-1.5 w-1.5 rounded-full bg-plum" /> Videos
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {showGhosts && [0, 1].map((i) => <GhostCard key={i} index={i} />)}
            {videoCats.map((c, i) => (
              <CategoryCard
                key={c.id}
                index={i}
                tall
                name={c.name}
                emoji={c.emoji}
                count={landed[cardKey(c.id, "video")] ?? 0}
                total={c.videos}
                slotRef={slotRef(cardKey(c.id, "video"))}
                onClick={() => setFilesFor({ title: `${c.name} · videos`, catId: c.id, kind: "video" })}
              />
            ))}
            {!showGhosts && job.categories.length > 0 && videoCats.length === 0 && (
              <p className="col-span-2 text-xs text-plum/45">No videos in this folder.</p>
            )}
            {dupCat && (
              <div className="col-span-2">
                <CategoryCard
                  variant="trash"
                  name="Duplicates"
                  count={landed["dup"] ?? 0}
                  total={dupCat.photos + dupCat.videos}
                  slotRef={slotRef("dup")}
                  onClick={() => setFilesFor({ title: "Duplicates", catId: DUP, kind: null })}
                />
              </div>
            )}
          </div>
        </section>

        <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 z-10" aria-hidden />
      </div>

      </div>

      <footer className="mt-16 flex flex-wrap items-center justify-between gap-2 text-[11px] text-plum/45">
        <span>
          Auto Image Organizer v{health?.version ?? "…"} · runs locally · nothing is moved until you press Apply
        </span>
        <a
          className="inline-flex items-center gap-1 hover:text-plum"
          href="https://github.com/bogdancstrike/image-organizer"
          target="_blank"
          rel="noreferrer"
        >
          <GithubOutlined /> GitHub
        </a>
      </footer>

      <SettingsDrawer
        open={drawer === "settings"}
        onClose={() => setDrawer(null)}
        settings={settings}
        onChange={setSettings}
        presets={presets}
        customSets={customSets}
        health={health}
        onEditCategories={() => setDrawer("editor")}
        onPickFolder={() => setDrawer("folder")}
      />
      <FolderPicker
        open={drawer === "folder"}
        value={settings.source}
        health={health}
        onClose={() => setDrawer(null)}
        onChoose={(path) => {
          setSettings({ ...settings, source: path });
          setDrawer(null);
          if (!running) {
            engineRef.current?.reset();
            setJob(INITIAL);
            setLanded({});
            setLandedKinds({ image: 0, video: 0 });
          }
        }}
      />
      <CategoryEditor
        open={drawer === "editor"}
        onClose={() => {
          setDrawer(null);
          setEditorTarget(null);
        }}
        presets={presets}
        customSets={customSets}
        initial={editorTarget}
        onSaved={(saved) => {
          api.sets().then(setCustomSets).catch(() => {});
          api.presets().then(setPresets).catch(() => {});
          if (saved)
            setSettings(
              saved.custom === false
                ? { ...settings, strategy: "preset", presetId: saved.id }
                : { ...settings, strategy: "custom", customSetId: saved.id },
            );
        }}
      />
      <HistoryDrawer open={drawer === "history"} onClose={() => setDrawer(null)} onUndone={(id) => {
        setJob((j) => (j.runId === id ? { ...j, status: "undone" } : j));
      }} />
      <FilesDrawer title={filesFor?.title ?? null} items={filesItems} onClose={() => setFilesFor(null)} />
    </div>
  );
}

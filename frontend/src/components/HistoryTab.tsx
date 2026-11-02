import { useCallback, useEffect, useMemo, useState } from "react";
import { App, Button, Drawer, Empty, Pagination, Popconfirm, Segmented, Spin } from "antd";
import { ChevronRight, FolderOpen, RotateCcw, Trash2 } from "lucide-react";
import { api, type HistoryItem, type HistoryPage } from "@/api";
import { cn, fmt } from "@/lib/utils";

const OUTCOME: Record<string, { label: string; dot: string; hint: string }> = {
  applied: { label: "Applied", dot: "bg-emerald-500", hint: "Files were moved or copied." },
  undone: { label: "Undone", dot: "bg-sky-500", hint: "Applied, then every file was put back." },
  not_applied: { label: "Plan only", dot: "bg-plum/30", hint: "Sorted and reviewed, nothing was moved." },
  cancelled: { label: "Cancelled", dot: "bg-plum/20", hint: "Stopped before it finished." },
  failed: { label: "Failed", dot: "bg-red-500", hint: "An error stopped it." },
};
const STRATEGY: Record<string, string> = {
  rules: "AI prompt rules", preset: "preset", custom: "my categories", auto: "auto-discover", date: "by date", cull: "culling",
  people: "by person", trips: "by trip", places: "by place",
};
const PAGE = 40;
const dur = (s?: number | null) => (!s ? "–" : s >= 60 ? `${(s / 60).toFixed(1)} min` : `${s.toFixed(1)} s`);
const folderName = (src?: string | null) => (src || "").split("/").filter(Boolean).pop() || "Library";

function dayLabel(ts: number) {
  const d = new Date(ts * 1000);
  const today = new Date();
  const y = new Date();
  y.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === y.toDateString()) return "Yesterday";
  return d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: d.getFullYear() === today.getFullYear() ? undefined : "numeric" });
}

/** Consecutive, identical plan-only sorts (same folder + strategy) collapse into one line "×N". */
type Entry = { item: HistoryItem; repeats: number };
function collapse(items: HistoryItem[]): Entry[] {
  const out: Entry[] = [];
  for (const it of items) {
    const prev = out[out.length - 1];
    if (
      prev &&
      it.outcome === "not_applied" &&
      prev.item.outcome === "not_applied" &&
      prev.item.source === it.source &&
      prev.item.strategy === it.strategy &&
      dayLabel(prev.item.finished_at ?? 0) === dayLabel(it.finished_at ?? 0)
    ) {
      prev.repeats += 1;
      continue;
    }
    out.push({ item: it, repeats: 1 });
  }
  return out;
}

function Details({ it, onUndo, onTrash, onReopen, busy }: {
  it: HistoryItem;
  onUndo: (runId: string) => void;
  onTrash: (runId: string) => void;
  onReopen: (jobId: string) => void;
  busy: boolean;
}) {
  const o = OUTCOME[it.outcome];
  const run = it.run;
  const phases = Object.entries(it.phases ?? {}).filter(([k, v]) => k !== "done" && v > 0.05);
  const maxPhase = Math.max(0.001, ...phases.map(([, v]) => v));
  const facts: [string, string][] = [
    ["When", it.finished_at ? new Date(it.finished_at * 1000).toLocaleString() : "–"],
    ["Folder", it.source || "/"],
    ["How", it.strategy ? STRATEGY[it.strategy] ?? it.strategy : "–"],
    ["Model", it.model ?? "–"],
    ["Files", `${fmt(it.photos ?? 0)} photos · ${fmt(it.videos ?? 0)} videos`],
    ["Duplicates", fmt(it.duplicates ?? 0)],
    ["Took", dur(it.wall)],
  ];
  if (run) facts.push([run.mode === "copy" ? "Copied" : "Moved", `${fmt(run.moved)} files${run.failed ? ` · ${run.failed} failed` : ""}`]);
  if (run?.undo) facts.push(["Put back", `${fmt(run.undo.restored)} files`]);
  if (it.usage) facts.push(["AI tokens", fmt((it.usage.input_tokens ?? 0) + (it.usage.output_tokens ?? 0))]);

  return (
    <div className="space-y-7">
      <div className="flex items-center gap-2 text-[13px] text-plum/70">
        <span className={cn("h-2 w-2 rounded-full", o?.dot)} /> {o?.label} · {o?.hint}
      </div>

      {(it.reopen || run?.status === "applied") && (
        <div className="flex flex-wrap gap-2">
          {it.reopen && it.job_id && (
            <Button type="primary" icon={<FolderOpen size={14} />} onClick={() => onReopen(it.job_id!)}>
              Open this plan
            </Button>
          )}
          {run?.status === "applied" && (
            <Popconfirm title="Put every file back where it was?" onConfirm={() => onUndo(run.run_id)}>
              <Button icon={<RotateCcw size={14} />} loading={busy}>Undo</Button>
            </Popconfirm>
          )}
          {run?.status === "applied" && run.in_trash > 0 && (
            <Popconfirm title={`Delete ${run.in_trash} trashed duplicates for good? This can't be undone.`} onConfirm={() => onTrash(run.run_id)}>
              <Button danger icon={<Trash2 size={14} />}>Empty trash ({run.in_trash})</Button>
            </Popconfirm>
          )}
        </div>
      )}

      <section>
        <h4 className="label-caps mb-3">Folders</h4>
        {it.categories.length ? (
          <div className="space-y-2">
            {it.categories.map((c) => (
              <div key={c.name} className="flex items-center gap-3 text-[13px]">
                <span className="w-40 truncate text-plum/85">{c.name}</span>
                <div className="h-1.5 flex-1 rounded-full bg-tint">
                  <div className="h-1.5 rounded-full bg-plum/50" style={{ width: `${(c.count / Math.max(1, it.categories[0].count)) * 100}%` }} />
                </div>
                <span className="w-10 text-right tabular-nums text-plum/60">{fmt(c.count)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[12px] text-plum/45">Only the latest 20 sorts keep their folder list.</p>
        )}
      </section>

      <section>
        <h4 className="label-caps mb-3">Details</h4>
        <dl className="divide-y divide-line/60 text-[13px]">
          {facts.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 py-1.5">
              <dt className="text-plum/55">{k}</dt>
              <dd className="min-w-0 truncate text-right text-plum/85" title={v}>{v}</dd>
            </div>
          ))}
        </dl>
      </section>

      {phases.length > 0 && (
        <section>
          <h4 className="label-caps mb-3">Time per step</h4>
          <div className="space-y-2">
            {phases.map(([k, v]) => (
              <div key={k} className="flex items-center gap-3 text-[12px]">
                <span className="w-28 capitalize text-plum/70">{k}</span>
                <div className="h-1.5 flex-1 rounded-full bg-tint">
                  <div className="h-1.5 rounded-full bg-plum/40" style={{ width: `${(v / maxPhase) * 100}%` }} />
                </div>
                <span className="w-14 text-right tabular-nums text-plum/60">{dur(v)}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/** History: a calm, day-grouped list of every sort; details and actions open in a side panel. */
export function HistoryTab({ active, onUndone, onReopen }: { active: boolean; onUndone: (runId: string) => void; onReopen: (jobId: string) => void }) {
  const { message } = App.useApp();
  const [outcome, setOutcome] = useState("all");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<HistoryPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [selected, setSelected] = useState<HistoryItem | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    api
      .history(outcome, PAGE, (page - 1) * PAGE)
      .then(setData)
      .catch((e) => message.error((e as Error).message))
      .finally(() => setLoading(false));
  }, [outcome, page, message]);
  useEffect(() => {
    if (active) load();
  }, [active, load]);

  const undo = async (runId: string) => {
    setBusy(runId);
    try {
      const r = await api.undo(runId);
      const problems = r.undo?.problems.length ?? 0;
      if (problems) message.warning(`Restored ${r.undo?.restored} files, ${problems} could not be restored`);
      else message.success(`Restored ${r.undo?.restored} files`);
      onUndone(runId);
      setSelected(null);
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  const trash = async (runId: string) => {
    try {
      await api.emptyTrash(runId);
      message.success("Trash emptied");
      setSelected(null);
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const groups = useMemo(() => {
    const out: { day: string; entries: Entry[] }[] = [];
    for (const e of collapse(data?.items ?? [])) {
      const day = dayLabel(e.item.finished_at ?? 0);
      if (out.length && out[out.length - 1].day === day) out[out.length - 1].entries.push(e);
      else out.push({ day, entries: [e] });
    }
    return out;
  }, [data]);

  const c = data?.counts;
  return (
    <div>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-[26px] font-semibold tracking-tight text-plum">History</h2>
          {c && (
            <p className="mt-1 text-[13px] text-plum/55">
              {fmt(c.all)} sorts · {fmt(c.applied)} applied · {fmt(c.not_applied)} plans not applied
              {c.undone ? ` · ${fmt(c.undone)} undone` : ""}
            </p>
          )}
        </div>
        <Segmented
          size="small"
          value={outcome}
          onChange={(v) => {
            setOutcome(String(v));
            setPage(1);
          }}
          options={[
            { value: "all", label: "All" },
            { value: "applied", label: "Applied" },
            { value: "not_applied", label: "Plans" },
            { value: "undone", label: "Undone" },
            { value: "failed", label: "Failed" },
          ]}
        />
      </div>

      {loading && !data ? (
        <div className="flex justify-center py-20"><Spin /></div>
      ) : !groups.length ? (
        <Empty className="py-20" description={outcome === "all" ? "Your sorts will show up here." : "Nothing here."} />
      ) : (
        <div className={cn("space-y-8", loading && "opacity-60")}>
          {groups.map((g) => (
            <section key={g.day}>
              <h3 className="mb-2 px-3 text-[12px] font-medium text-plum/45">{g.day}</h3>
              <ul>
                {g.entries.map(({ item: it, repeats }, i) => {
                  const o = OUTCOME[it.outcome];
                  return (
                    <li key={`${it.job_id ?? it.run?.run_id}-${i}`}>
                      <button
                        onClick={() => setSelected(it)}
                        className="group flex w-full cursor-pointer items-center gap-4 rounded-xl px-3 py-3 text-left transition hover:bg-tint/60"
                      >
                        <span className={cn("h-2 w-2 shrink-0 rounded-full", o?.dot)} title={o?.label} />
                        <span className="min-w-0 flex-1 truncate text-[14px] text-plum">
                          <span className="font-medium">{folderName(it.source)}</span>
                          <span className="text-plum/45"> · {it.strategy ? STRATEGY[it.strategy] ?? it.strategy : "applied"}</span>
                          {repeats > 1 && <span className="ml-2 rounded-full bg-tint px-1.5 py-0.5 text-[11px] text-plum/55">×{repeats}</span>}
                        </span>
                        <span className="hidden w-44 shrink-0 text-right text-[12px] tabular-nums text-plum/50 sm:block">
                          {it.files == null ? "" : it.folders != null ? `${fmt(it.files)} files → ${it.folders} folders` : `${fmt(it.files)} files`}
                        </span>
                        {it.outcome !== "not_applied" && (
                          <span className="hidden w-20 shrink-0 text-right text-[12px] text-plum/60 md:block">{o?.label}</span>
                        )}
                        {it.outcome === "not_applied" && <span className="hidden w-20 shrink-0 md:block" />}
                        <span className="w-20 shrink-0 whitespace-nowrap text-right text-[12px] tabular-nums text-plum/40">
                          {it.finished_at ? new Date(it.finished_at * 1000).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : ""}
                        </span>
                        <ChevronRight size={15} className="shrink-0 text-plum/25 transition group-hover:text-plum/60" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
          {data && data.total > PAGE && (
            <div className="flex justify-center pt-2">
              <Pagination size="small" current={page} pageSize={PAGE} total={data.total} onChange={setPage} showSizeChanger={false} />
            </div>
          )}
        </div>
      )}

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        size={520}
        title={selected ? <span className="font-semibold">{folderName(selected.source)}</span> : null}
      >
        {selected && <Details it={selected} onUndo={undo} onTrash={trash} onReopen={onReopen} busy={busy === selected.run?.run_id} />}
      </Drawer>
    </div>
  );
}

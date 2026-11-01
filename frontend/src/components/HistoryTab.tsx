import { useCallback, useEffect, useState } from "react";
import { App, Button, Empty, Pagination, Popconfirm, Segmented, Spin, Tag } from "antd";
import { ChevronDown, Clock, FolderOpen, RotateCcw, Trash2 } from "lucide-react";
import { api, type HistoryItem, type HistoryPage } from "@/api";
import { Card } from "./ui/card";
import { cn, fmt } from "@/lib/utils";

const OUTCOME: Record<string, { label: string; color?: string; hint: string }> = {
  applied: { label: "Applied", color: "green", hint: "files were moved or copied" },
  undone: { label: "Undone", color: "blue", hint: "applied, then put back" },
  not_applied: { label: "Not applied", color: "gold", hint: "planned only, nothing moved" },
  cancelled: { label: "Cancelled", hint: "stopped before it finished" },
  failed: { label: "Failed", color: "red", hint: "an error stopped it" },
};
const STRATEGY: Record<string, string> = {
  preset: "Preset", custom: "My categories", auto: "Auto-discover", date: "By date", cull: "Culling",
  people: "By person", trips: "By trip", places: "By place",
};
const PAGE = 15;
const dur = (s?: number | null) => (!s ? "–" : s >= 60 ? `${(s / 60).toFixed(1)} min` : `${s.toFixed(1)} s`);

function Row({ it, onUndo, onTrash, onReopen, busy }: {
  it: HistoryItem;
  onUndo: (runId: string) => void;
  onTrash: (runId: string) => void;
  onReopen: (jobId: string) => void;
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  const o = OUTCOME[it.outcome] ?? { label: it.outcome, hint: "" };
  const run = it.run;
  const phases = Object.entries(it.phases ?? {}).filter(([k]) => k !== "done");
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <button onClick={() => setOpen((v) => !v)} className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 text-left" aria-expanded={open}>
          <ChevronDown size={16} className={cn("shrink-0 text-plum/40 transition", open && "rotate-180")} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-[14px] font-medium text-plum">
              <span className="truncate">{(it.source || "/").split("/").pop() || "Library"}</span>
              <Tag color={o.color} className="m-0" title={o.hint}>{o.label}</Tag>
              {it.strategy && <Tag className="m-0">{STRATEGY[it.strategy] ?? it.strategy}</Tag>}
            </div>
            <div className="mt-0.5 flex flex-wrap gap-x-3 text-[11px] text-plum/55">
              <span><Clock size={11} className="mr-1 inline" />{it.finished_at ? new Date(it.finished_at * 1000).toLocaleString() : "–"}</span>
              {it.files != null && <span>{fmt(it.files)} files → {it.folders ?? "?"} folders</span>}
              {it.wall != null && <span>{dur(it.wall)}</span>}
              {run && <span>{run.mode === "copy" ? "copied" : "moved"} {fmt(run.moved)}{run.failed ? ` · ${run.failed} failed` : ""}</span>}
            </div>
          </div>
        </button>
        <div className="flex flex-wrap gap-2">
          {it.reopen && it.job_id && (
            <Button size="small" icon={<FolderOpen size={13} />} onClick={() => onReopen(it.job_id!)}>
              Open plan
            </Button>
          )}
          {run && run.status === "applied" && (
            <Popconfirm title="Put every file back where it was?" onConfirm={() => onUndo(run.run_id)}>
              <Button size="small" icon={<RotateCcw size={13} />} loading={busy}>Undo</Button>
            </Popconfirm>
          )}
          {run && run.status === "applied" && run.in_trash > 0 && (
            <Popconfirm title={`Delete ${run.in_trash} trashed duplicates for good? This can't be undone.`} onConfirm={() => onTrash(run.run_id)}>
              <Button size="small" danger icon={<Trash2 size={13} />}>Empty trash ({run.in_trash})</Button>
            </Popconfirm>
          )}
        </div>
      </div>
      {open && (
        <div className="mt-4 grid gap-4 border-t border-line pt-4 md:grid-cols-3">
          <div>
            <div className="label-caps mb-2">Folders</div>
            {it.categories.length ? (
              <ul className="space-y-1 text-[12px] text-plum/75">
                {it.categories.map((c) => (
                  <li key={c.name} className="flex justify-between gap-2"><span className="truncate">{c.name}</span><span className="tabular-nums">{fmt(c.count)}</span></li>
                ))}
              </ul>
            ) : <p className="text-[12px] text-plum/45">Not kept (only the last 20 sorts keep their full plan).</p>}
          </div>
          <div>
            <div className="label-caps mb-2">Details</div>
            <dl className="grid grid-cols-2 gap-y-1 text-[12px] text-plum/75">
              <dt>Folder</dt><dd className="truncate text-right" title={it.source ?? ""}>{it.source || "/"}</dd>
              <dt>Photos / videos</dt><dd className="text-right tabular-nums">{fmt(it.photos ?? 0)} / {fmt(it.videos ?? 0)}</dd>
              <dt>Analyzed fresh</dt><dd className="text-right tabular-nums">{fmt(it.embedded ?? 0)}</dd>
              <dt>Duplicates</dt><dd className="text-right tabular-nums">{fmt(it.duplicates ?? 0)}</dd>
              <dt>Model</dt><dd className="text-right">{it.model ?? "–"}</dd>
              {it.usage && <><dt>AI tokens</dt><dd className="text-right tabular-nums">{fmt((it.usage.input_tokens ?? 0) + (it.usage.output_tokens ?? 0))}</dd></>}
              {run?.undo && <><dt>Restored</dt><dd className="text-right tabular-nums">{fmt(run.undo.restored)}</dd></>}
            </dl>
          </div>
          <div>
            <div className="label-caps mb-2">Time per step</div>
            {phases.length ? (
              <ul className="space-y-1 text-[12px] text-plum/75">
                {phases.map(([k, v]) => (
                  <li key={k} className="flex justify-between"><span className="capitalize">{k}</span><span className="tabular-nums">{dur(v)}</span></li>
                ))}
              </ul>
            ) : <p className="text-[12px] text-plum/45">–</p>}
          </div>
        </div>
      )}
    </Card>
  );
}

/** History: every sort (applied or not) with outcome, details, undo, empty trash and "open plan". */
export function HistoryTab({ active, onUndone, onReopen }: { active: boolean; onUndone: (runId: string) => void; onReopen: (jobId: string) => void }) {
  const { message } = App.useApp();
  const [outcome, setOutcome] = useState("all");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<HistoryPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

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
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const c = data?.counts;
  return (
    <div className="space-y-4">
      <Segmented
        value={outcome}
        onChange={(v) => {
          setOutcome(String(v));
          setPage(1);
        }}
        options={[
          { value: "all", label: `All${c ? ` · ${c.all}` : ""}` },
          { value: "applied", label: `Applied${c ? ` · ${c.applied}` : ""}` },
          { value: "not_applied", label: `Not applied${c ? ` · ${c.not_applied}` : ""}` },
          { value: "undone", label: `Undone${c ? ` · ${c.undone}` : ""}` },
          { value: "failed", label: `Failed${c ? ` · ${c.failed}` : ""}` },
          { value: "cancelled", label: `Cancelled${c ? ` · ${c.cancelled}` : ""}` },
        ]}
      />
      {loading && !data ? (
        <div className="flex justify-center py-16"><Spin /></div>
      ) : !data || data.items.length === 0 ? (
        <Empty className="py-16" description="No sorts here yet" />
      ) : (
        <>
          <div className={cn("space-y-2", loading && "opacity-60")}>
            {data.items.map((it, i) => (
              <Row key={`${it.job_id ?? it.run?.run_id}-${i}`} it={it} onUndo={undo} onTrash={trash} onReopen={onReopen} busy={busy === it.run?.run_id} />
            ))}
          </div>
          {data.total > PAGE && (
            <div className="flex justify-center">
              <Pagination current={page} pageSize={PAGE} total={data.total} onChange={setPage} showSizeChanger={false} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

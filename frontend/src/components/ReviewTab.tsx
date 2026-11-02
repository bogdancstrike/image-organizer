import { useMemo, useState } from "react";
import { App, Button, Empty, Input, Progress, Rate, Segmented, Select, Table, Tag, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Search, MoveRight } from "lucide-react";
import { api, type JobCategory, type PlanItem } from "@/api";
import { InfoBadge, SOURCE_HELP } from "./PhotoBadge";
import { ComparePhotos } from "./ComparePhotos";
import { Thumb } from "./FilesDrawer";
import { FLAG, useMediaViewer } from "./MediaViewer";
import { fmt } from "@/lib/utils";
import { useI18n } from "@/i18n";

interface Props {
  jobId: string | null;
  editable: boolean;
  plan: PlanItem[];
  categories: JobCategory[];
  onChanged: (changed: PlanItem[], categories: JobCategory[]) => void;
}

type Filter = "all" | "rejects" | "smiling" | "unsure" | "ai" | "manual" | "bursts" | "picks" | "close" | "unique" | "pareto" | "winner";

/** The whole plan as a table: filter, inspect, and reassign files before Apply. */
export function ReviewTab({ jobId, editable, plan, categories, onChanged }: Props) {
  const { message } = App.useApp();
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<"all" | "image" | "video">("all");
  const [cats, setCats] = useState<string[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<string[]>([]);
  const [target, setTarget] = useState<string | undefined>();
  const [compare, setCompare] = useState(false);
  const [busy, setBusy] = useState(false);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return plan.filter((p) => {
      if (kind !== "all" && p.kind !== kind) return false;
      if (cats.length && !cats.includes(p.category_id)) return false;
      if (needle && !p.rel_path.toLowerCase().includes(needle) && !(p.text ?? "").toLowerCase().includes(needle) && !p.tags?.some(tag=>tag.label.toLowerCase().includes(needle))) return false;
      if (filter === "rejects" && !(p.quality?.flags.length || p.category_id.startsWith("_reject"))) return false;
      if (filter === "smiling" && !p.quality?.smiling) return false;
      if (filter === "unsure" && !(p.category_id === "_unsorted" || (p.source === "clip" && p.confidence < 0.45))) return false;
      if (filter === "ai" && p.source !== "ai") return false;
      if (filter === "manual" && p.source !== "manual") return false;
      if (filter === "winner" && !p.pick?.winner) return false;
      if (filter === "picks" && !p.pick?.picked) return false;
      if (filter === "close" && !(p.burst?.margin !== undefined && p.burst.margin < .025)) return false;
      if (filter === "unique" && (p.pick?.parts?.novelty ?? 0) < .8) return false;
      if (filter === "pareto" && p.pick?.parts?.pareto !== 1) return false;
      if (filter === "bursts" && !p.burst) return false;
      return true;
    });
  }, [plan, q, kind, cats, filter]);

  const viewer = useMediaViewer(rows);
  const catOptions = categories.map((c) => ({ value: c.id, label: `${c.emoji ?? ""} ${c.name}`.trim() }));

  const move = async (ids: string[], categoryId: string) => {
    if (!jobId) return;
    setBusy(true);
    try {
      const r = await api.reassign(jobId, ids, categoryId);
      onChanged(r.changed, r.categories);
      message.success(`${ids.length} file${ids.length === 1 ? "" : "s"} → ${r.changed[0]?.category ?? ""}`);
      if (!compare) setSelected([]);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const columns: ColumnsType<PlanItem> = [
    { title: "", key: "thumb", width: 64, render: (_, p) => <Thumb p={p} size="sm" onOpen={() => viewer.open(p)} /> },
    {
      title: "File",
      key: "name",
      sorter: (a, b) => a.rel_path.localeCompare(b.rel_path),
      render: (_, p) => (
        <div className="min-w-0">
          <div className="truncate font-medium text-plum">{p.name}</div>
          <div className="truncate text-[11px] text-plum/50">{p.rel_path.split("/").slice(0, -1).join("/") || "/"}</div>
        </div>
      ),
    },
    {
      title: "Category",
      key: "category",
      width: 230,
      render: (_, p) =>
        editable ? (
          <Select
            size="small"
            className="w-full"
            value={p.category_id}
            options={catOptions}
            onChange={(v) => move([p.file_id], v)}
            disabled={busy}
            popupMatchSelectWidth={false}
          />
        ) : (
          <span>{p.category}</span>
        ),
    },
    {
      title: "Match",
      key: "confidence",
      width: 120,
      sorter: (a, b) => a.confidence - b.confidence,
      render: (_, p) =>
        ["clip", "ai", "cluster"].includes(p.source) ? (
          <Tooltip title={SOURCE_HELP[p.source] ?? p.source}>
            <Progress percent={Math.round(p.confidence * 100)} size="small" showInfo={false} />
          </Tooltip>
        ) : (
          <InfoBadge message={SOURCE_HELP[p.source] ?? p.source}><Tag className="m-0">{p.source}</Tag></InfoBadge>
        ),
    },
    {
      title: "Quality",
      key: "quality",
      width: 150,
      sorter: (a, b) => (a.quality?.sharpness ?? 0) - (b.quality?.sharpness ?? 0),
      render: (_, p) =>
        p.quality ? (
          <span className="inline-flex items-center gap-1.5 text-xs">
            <Tooltip title="sharpness">
              <span className="tabular-nums text-plum/60">{Math.round(p.quality.sharpness * 100)}%</span>
            </Tooltip>
            {p.quality.flags.map((f) => (
              <Tooltip key={f} title={FLAG[f]?.help ?? f}>
                <span>{FLAG[f]?.emoji}</span>
              </Tooltip>
            ))}
            {p.quality.smiling && <InfoBadge message="Smile detected on a face included by your quality settings.">😄</InfoBadge>}
            {p.quality.faces > 0 && <InfoBadge message={`${p.quality.faces} detected face${p.quality.faces === 1 ? "" : "s"}. Quality checks use your main-face or group setting.`} className="text-plum/45">· {p.quality.faces}👤</InfoBadge>}
          </span>
        ) : (
          <span className="text-plum/30">–</span>
        ),
    },
    {
      title: "Recommendation", key: "recommendation", width: 140,
      defaultSortOrder: plan.some((p) => p.pick) ? "descend" : undefined,
      sorter: (a, b) => (a.pick?.score ?? -1) - (b.pick?.score ?? -1),
      render: (_, p) => p.pick ? <Tooltip title={`${p.pick.profile ?? "general"}: ${p.pick.reasons.join(" · ")}`}>
        <span className="text-xs tabular-nums">{p.pick.picked ? "★ " : ""}{(p.pick.rating ?? 1 + p.pick.score * 4).toFixed(2)}/5</span>
      </Tooltip> : <span className="text-plum/30">–</span>,
    },
    {
      title: "Rating",
      key: "stars",
      width: 120,
      sorter: (a, b) => (a.quality?.score ?? 0) - (b.quality?.score ?? 0),
      render: (_, p) =>
        p.quality ? (
          <Tooltip title={`keeper score ${Math.round(p.quality.score * 100)}/100${p.burst ? ` · burst of ${p.burst.size}${p.burst.best ? " · best" : ""}` : ""}`}>
            <span className="inline-flex items-center gap-1">
              <Rate disabled value={p.quality.stars} className="!text-[11px]" />
              {p.burst && <InfoBadge message={p.burst.best ? `Best frame in a group of ${p.burst.size} similar shots.` : `Alternative frame in a group of ${p.burst.size} similar shots.`} className="text-[11px]">{p.burst.best ? "🏆" : "🎞️"}</InfoBadge>}
            </span>
          </Tooltip>
        ) : (
          <span className="text-plum/30">–</span>
        ),
    },
    {
      title: "Goes to",
      key: "destination",
      ellipsis: true,
      render: (_, p) => <span className="text-xs text-plum/60">{p.destination}/</span>,
    },
  ];

  if (!plan.length) {
    return <Empty className="py-20" description={t("rv.empty")} />;
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          allowClear
          prefix={<Search size={14} className="text-plum/40" />}
          placeholder={t("review.search")}
          className="w-64"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Segmented
          value={kind}
          onChange={(v) => setKind(v as typeof kind)}
          options={[
            { value: "all", label: "All" },
            { value: "image", label: "Photos" },
            { value: "video", label: "Videos" },
          ]}
        />
        <Select
          mode="multiple"
          allowClear
          placeholder="Categories"
          className="min-w-52"
          maxTagCount="responsive"
          value={cats}
          onChange={setCats}
          options={catOptions}
        />
        <Segmented
          value={filter}
          onChange={(v) => setFilter(v as Filter)}
          options={[
            { value: "all", label: t("rv.everything") },
            { value: "winner", label: "Winner photo" },
            { value: "picks", label: "Top picks" },
            { value: "unsure", label: t("rv.unsure") },
            { value: "rejects", label: t("rv.rejects") },
            { value: "smiling", label: t("rv.smiling") },
            { value: "ai", label: "AI" },
            { value: "bursts", label: t("rv.bursts") },
            { value: "manual", label: t("rv.edited") },
          ]}
        />
        <Select aria-label="More recommendation filters" placeholder="More review filters" allowClear className="min-w-44"
          value={["close","unique","pareto"].includes(filter)?filter:undefined} onChange={v=>setFilter(v??"all")}
          options={[{value:"close",label:"Close burst decisions"},{value:"unique",label:"Unique views"},{value:"pareto",label:"Alternative strengths"}]} />
        <Button disabled={selected.length<2 || selected.length>4 || plan.filter(p=>selected.includes(p.file_id)).some(p=>p.kind!=="image")}
          onClick={()=>setCompare(true)}>Compare selected</Button>
        <span className="ml-auto text-xs text-plum/55">
          {t("rv.count", { n: fmt(rows.length), total: fmt(plan.length) })}
        </span>
      </div>

      {editable && selected.length > 0 && (
        <div className="pop-in mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-line bg-surface/80 px-3 py-2 text-[13px]">
          <b>{selected.length}</b> selected
          <MoveRight size={14} className="text-plum/50" />
          <Select size="small" className="w-60" placeholder={t("rv.moveto")} value={target} onChange={setTarget} options={catOptions} />
          <Button size="small" type="primary" disabled={!target} loading={busy} onClick={() => target && move(selected, target)}>
            Move
          </Button>
          <Button size="small" type="text" onClick={() => setSelected([])}>
            Clear
          </Button>
        </div>
      )}

      <Table<PlanItem>
        rowKey="file_id"
        size="small"
        columns={columns}
        dataSource={rows}
        rowSelection={{ selectedRowKeys: selected, onChange: (k) => setSelected(k as string[]) }}
        pagination={{ defaultPageSize: 50, showSizeChanger: true, pageSizeOptions: [25, 50, 100, 250] }}
        scroll={{ x: 900 }}
      />
      {!editable && <p className="mt-2 text-xs text-plum/50">This plan was already applied. Re-run a sort to edit again.</p>}
      {compare && <ComparePhotos items={plan.filter(p=>selected.includes(p.file_id))} onClose={()=>setCompare(false)} categories={categories}
        onAssign={editable ? (id,category)=>move([id],category) : undefined} />}
      {viewer.node}
    </div>
  );
}

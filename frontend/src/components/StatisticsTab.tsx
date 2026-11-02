import { ExplainedTag as Tag } from "./PhotoBadge";
import { useEffect, useState } from "react";
import { Empty, Spin, Table } from "antd";
import { Activity, Clock, FolderCheck, Gauge, Images, Sparkles } from "lucide-react";
import { api, type Stats, type StatsRow } from "@/api";
import { Card } from "./ui/card";
import { fmt } from "@/lib/utils";

const PHASE_LABEL: Record<string, string> = {
  rules: "AI rules", scanning: "Scanning", analyzing: "Analyzing", checking: "Quality checks", reading: "OCR", faces: "Faces",
  deduplicating: "Duplicates", categorizing: "Categorizing", ai: "AI", naming: "AI naming", planning: "Planning",
};
const PHASE_COLOR = ["#71717a", "#a1a1aa", "#3f3f46", "#d4d4d8", "#52525b", "#b8467d", "#27272a", "#e4e4e7", "#8b5cf6"];
const color = (i: number) => PHASE_COLOR[i % PHASE_COLOR.length];
const dur = (s: number) => (s >= 3600 ? `${(s / 3600).toFixed(1)} h` : s >= 60 ? `${(s / 60).toFixed(1)} min` : `${s.toFixed(1)} s`);

function Kpi({ icon: Icon, label, value, hint }: { icon: typeof Clock; label: string; value: string; hint?: string }) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 label-caps">
        <Icon size={13} /> {label}
      </div>
      <div className="mt-1 text-[26px] font-semibold tabular-nums tracking-tight text-plum">{value}</div>
      {hint && <div className="truncate text-[11px] text-plum/50">{hint}</div>}
    </Card>
  );
}

/** Statistics: how much was processed, how fast, and where the time goes (data from /api/stats). */
export function StatisticsTab({ active }: { active: boolean }) {
  const [st, setSt] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!active) return;
    let alive = true;
    api
      .stats()
      .then((d) => alive && (setSt(d), setError(null)))
      .catch((e) => alive && setError(String(e.message ?? e)));
    return () => {
      alive = false;
    };
  }, [active]);

  if (error) return <Empty className="py-20" description={`Could not load statistics: ${error}`} />;
  if (!st) return <div className="flex justify-center py-20"><Spin /></div>;
  if (!st.sorts) return <Empty className="py-20" description="No sorts yet. Statistics appear after your first sort." />;

  const phases = Object.entries(st.phase_seconds).filter(([k]) => k !== "done");
  const phaseKeys = phases.map(([k]) => k);
  const maxPhase = Math.max(...phases.map(([, v]) => v), 0.001);
  const recent: StatsRow[] = st.recent.filter((r) => r.status === "done").slice(0, 24).reverse();
  const maxWall = Math.max(...recent.map((r) => r.wall ?? 0), 0.001);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        <Kpi icon={Activity} label="Sorts" value={fmt(st.sorts)} hint={st.failed_sorts ? `${st.failed_sorts} failed` : "all succeeded"} />
        <Kpi icon={Images} label="Files processed" value={fmt(st.files_processed)} hint={`${fmt(st.files_analyzed)} analyzed fresh`} />
        <Kpi icon={FolderCheck} label="Photos organized" value={fmt(st.photos_organized)} hint={`${st.applies} applies`} />
        <Kpi icon={Clock} label="Processing time" value={dur(st.processing_seconds)} hint={`${dur(st.avg_seconds_per_sort)} per sort`} />
        <Kpi icon={Gauge} label="Throughput" value={`${fmt(st.avg_files_per_second)}/s`} hint="files per second" />
        <Kpi icon={Sparkles} label="AI tokens" value={fmt(st.ai_tokens)} hint="input + output" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h3 className="mb-4 text-[15px] font-semibold text-plum">Where the time goes</h3>
          <div className="space-y-2.5">
            {phases.map(([k, v], i) => (
              <div key={k}>
                <div className="mb-1 flex justify-between text-[12px] text-plum/70">
                  <span>{PHASE_LABEL[k] ?? k}</span>
                  <span className="tabular-nums">{dur(v)}</span>
                </div>
                <div className="h-2.5 rounded-full bg-tint">
                  <div className="h-2.5 rounded-full" style={{ width: `${Math.max(1, (v / maxPhase) * 100)}%`, background: color(i) }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-5">
          <h3 className="mb-4 text-[15px] font-semibold text-plum">Time per sort (latest {recent.length})</h3>
          <div className="flex h-44 items-end justify-center gap-1.5 border-b border-line">
            {recent.map((r) => (
              <div
                key={r.job_id}
                className="flex h-full min-w-0 max-w-14 flex-1 flex-col-reverse"
                title={`${fmt(r.files)} files · ${dur(r.wall ?? 0)} · ${r.strategy}`}
              >
                {phaseKeys.map((k, i) => {
                  const v = r.phases?.[k] ?? 0;
                  return v > 0 ? <div key={k} style={{ height: `${(v / maxWall) * 100}%`, background: color(i) }} className="w-full" /> : null;
                })}
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-plum/60">
            {phaseKeys.map((k, i) => (
              <span key={k} className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-sm" style={{ background: color(i) }} /> {PHASE_LABEL[k] ?? k}
              </span>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-5">
        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          <h3 className="mr-2 text-[15px] font-semibold text-plum">Sorts</h3>
          {Object.entries(st.by_strategy).map(([k, v]) => (
            <Tag key={k} className="m-0">{k} · {v}</Tag>
          ))}
          {Object.entries(st.by_model).map(([k, v]) => (
            <Tag key={`m-${k}`} color="purple" className="m-0">{k} · {v}</Tag>
          ))}
        </div>
        <Table<StatsRow>
          size="small"
          rowKey="job_id"
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          scroll={{ x: 820 }}
          dataSource={st.recent}
          columns={[
            { title: "When", dataIndex: "finished_at", render: (v: number) => (v ? new Date(v * 1000).toLocaleString() : "–") },
            { title: "Folder", dataIndex: "source", ellipsis: true, render: (v: string) => <span title={v || "/"}>{(v || "/").split("/").filter(Boolean).pop() ?? "/"}</span> },
            { title: "Strategy", dataIndex: "strategy" },
            { title: "Model", dataIndex: "model" },
            { title: "Files", dataIndex: "files", align: "right", render: (v: number) => fmt(v ?? 0) },
            { title: "Analyzed", dataIndex: "embedded", align: "right", render: (v: number) => fmt(v ?? 0) },
            { title: "Folders", dataIndex: "folders", align: "right" },
            { title: "Time", dataIndex: "wall", align: "right", render: (v: number) => dur(v ?? 0) },
            { title: "Files/s", key: "fps", align: "right", render: (_: unknown, r) => (r.wall ? Math.round(r.files / r.wall) : "–") },
            {
              title: "",
              dataIndex: "status",
              render: (v: string) => <Tag color={v === "done" ? "green" : v === "error" ? "red" : undefined} className="m-0">{v}</Tag>,
            },
          ]}
        />
      </Card>
    </div>
  );
}

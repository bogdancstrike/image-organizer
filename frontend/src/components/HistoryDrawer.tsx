import { useEffect, useState } from "react";
import { App, Button, Drawer, Empty, Popconfirm, Tag } from "antd";
import { RotateCcw } from "lucide-react";
import { api, type Run } from "@/api";
import { useI18n } from "@/i18n";

export function HistoryDrawer({ open, onClose, onUndone }: { open: boolean; onClose: () => void; onUndone: (runId: string) => void }) {
  return (
    <Drawer open={open} onClose={onClose} title="History" size={420}>
      <HistoryList active={open} onUndone={onUndone} />
    </Drawer>
  );
}

export function HistoryList({ active, onUndone }: { active: boolean; onUndone: (runId: string) => void }) {
  const { message } = App.useApp();
  const { t } = useI18n();
  const [runs, setRuns] = useState<Run[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = () => api.runs().then(setRuns).catch((e) => message.error(e.message));
  useEffect(() => {
    if (active) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const undo = async (id: string) => {
    setBusy(id);
    try {
      const r = await api.undo(id);
      const problems = r.undo?.problems.length ?? 0;
      if (problems) message.warning(`Restored ${r.undo?.restored} files, ${problems} could not be restored`);
      else message.success(`Restored ${r.undo?.restored} files`);
      onUndone(id);
      refresh();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      {runs.length === 0 && <Empty description={t("hi.empty")} />}
      <div className="space-y-2">
        {runs.map((r) => (
          <div key={r.run_id} className="rounded-xl border border-line bg-surface/80 p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-plum">
                  {t(r.mode === "copy" ? "hi.copied" : "hi.moved", { n: r.moved })}
                  {r.source ? <span className="text-plum/50"> · {r.source}</span> : null}
                </div>
                <div className="text-[11px] text-plum/50">{new Date(r.created_at).toLocaleString()}</div>
              </div>
              {r.status === "undone" ? (
                <Tag>undone</Tag>
              ) : (
                <Popconfirm title="Put every file back where it was?" onConfirm={() => undo(r.run_id)}>
                  <Button size="small" icon={<RotateCcw size={13} />} loading={busy === r.run_id}>
                    Undo
                  </Button>
                </Popconfirm>
              )}
            </div>
            {r.failed > 0 && <div className="mt-1 text-[11px] text-red-500">{r.failed} failed</div>}
            {!!r.in_trash && r.status !== "undone" && (
              <div className="mt-2 flex items-center justify-between gap-2 rounded-lg bg-tint px-2.5 py-1.5 text-[12px] text-plum/75">
                <span>🗑️ {r.in_trash} duplicate{r.in_trash === 1 ? "" : "s"} in trash (still recoverable with Undo)</span>
                <Popconfirm
                  title="Delete these files permanently?"
                  description="This cannot be undone."
                  okText="Delete forever"
                  okButtonProps={{ danger: true }}
                  onConfirm={async () => {
                    const res = await api.emptyTrash(r.run_id);
                    message.success(`Deleted ${res.deleted} files · freed ${(res.freed_bytes / 1e6).toFixed(1)} MB`);
                    refresh();
                  }}
                >
                  <Button size="small" danger>
                    Empty trash
                  </Button>
                </Popconfirm>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

import { useEffect, useState } from "react";
import { App, Button, Drawer, Empty, Popconfirm, Tag } from "antd";
import { RotateCcw } from "lucide-react";
import { api, type Run } from "@/api";

export function HistoryDrawer({ open, onClose, onUndone }: { open: boolean; onClose: () => void; onUndone: (runId: string) => void }) {
  const { message } = App.useApp();
  const [runs, setRuns] = useState<Run[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = () => api.runs().then(setRuns).catch((e) => message.error(e.message));
  useEffect(() => {
    if (open) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

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
    <Drawer open={open} onClose={onClose} title="History" size={420}>
      {runs.length === 0 && <Empty description="Nothing applied yet" />}
      <div className="space-y-2">
        {runs.map((r) => (
          <div key={r.run_id} className="rounded-xl border border-line bg-surface/80 p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-plum">
                  {r.mode === "copy" ? "Copied" : "Moved"} {r.moved} files
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
          </div>
        ))}
      </div>
    </Drawer>
  );
}

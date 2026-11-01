import { useEffect, useState } from "react";
import { App, Breadcrumb, Button, Empty, Modal, Spin } from "antd";
import { ChevronRight, FolderClosed, FolderOpen, HardDrive, Images } from "lucide-react";
import { api, type Folder, type Health } from "@/api";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";

interface Props {
  open: boolean;
  value: string;
  health: Health | null;
  onClose: () => void;
  onChoose: (path: string) => void;
}

/** Shows a library-relative path the way the user knows it (host path when known). */
export function displayPath(health: Health | null, rel: string) {
  const base = (health?.library_host_path || "/library").replace(/\/+$/, "");
  return rel ? `${base}/${rel}` : base;
}

/** Browse the mounted library and pick the working folder (REQ-SCAN-5, REQ-UI-3). */
export function FolderPicker({ open, value, health, onClose, onChoose }: Props) {
  const { message } = App.useApp();
  const { t } = useI18n();
  const [path, setPath] = useState(value);
  const [data, setData] = useState<{ path: string; name: string; media_count: number; folders: Folder[] } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) setPath(value);
  }, [open, value]);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
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

  const parts = path ? path.split("/") : [];
  const rootLabel = health?.library_host_path || health?.library_name || "Library";

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        <span className="inline-flex items-center gap-2">
          <FolderOpen size={18} /> {t("fp.title")}
        </span>
      }
      width={640}
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="truncate text-xs text-plum/60">
            {data ? (
              <>
                <Images size={12} className="mr-1 inline" />
                {data.media_count} photos & videos directly here · sorted folders will be created inside it
              </>
            ) : null}
          </span>
          <div className="flex gap-2">
            <Button onClick={onClose}>Cancel</Button>
            <Button type="primary" onClick={() => onChoose(path)}>
              {t("fp.use")}
            </Button>
          </div>
        </div>
      }
    >
      <Breadcrumb
        className="mb-3"
        items={[
          {
            title: (
              <a onClick={() => setPath("")} className="inline-flex items-center gap-1">
                <HardDrive size={13} /> {rootLabel}
              </a>
            ),
          },
          ...parts.map((p, i) => ({
            title: <a onClick={() => setPath(parts.slice(0, i + 1).join("/"))}>{p}</a>,
          })),
        ]}
      />
      <div className="max-h-[52vh] min-h-[220px] overflow-y-auto rounded-xl border border-line bg-surface/60 p-1.5">
        {loading && !data ? (
          <div className="flex h-48 items-center justify-center">
            <Spin />
          </div>
        ) : data && data.folders.length === 0 ? (
          <Empty className="py-8" description="No subfolders, so you can use this folder" />
        ) : (
          data?.folders.map((f) => (
            <button
              key={f.path}
              onClick={() => setPath(f.path)}
              onDoubleClick={() => onChoose(f.path)}
              className={cn(
                "flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] text-plum hover:bg-tint",
                loading && "opacity-60",
              )}
            >
              <FolderClosed size={16} className="shrink-0 text-plum/60" />
              <span className="min-w-0 flex-1 truncate">{f.name}</span>
              {f.media_count > 0 && (
                <span className="rounded-full bg-tint px-2 py-0.5 text-[11px] text-plum/70">{f.media_count}</span>
              )}
              {f.has_children && <ChevronRight size={14} className="text-plum/40" />}
            </button>
          ))
        )}
      </div>
      <p className="mt-2 text-[11px] text-plum/50">
        Showing folders under <code>{rootLabel}</code>, the folder mounted into the container (set <code>LIBRARY_PATH</code>{" "}
        to change it). Click to open, double-click to choose.
      </p>
    </Modal>
  );
}

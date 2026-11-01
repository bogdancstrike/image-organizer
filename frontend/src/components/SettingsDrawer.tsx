import { useCallback, useEffect, useState } from "react";
import { Drawer, Segmented, Select, Slider, Switch, Tooltip, TreeSelect, InputNumber, Radio, Button, Divider } from "antd";
import { Sparkles, Shapes, CalendarDays, Wand2, PencilLine } from "lucide-react";
import { api, type CategorySet, type Health } from "@/api";
import type { UiSettings } from "@/settings";

interface TreeNode {
  id: string;
  pId?: string;
  value: string;
  title: string;
  isLeaf: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
  settings: UiSettings;
  onChange: (s: UiSettings) => void;
  presets: CategorySet[];
  customSets: CategorySet[];
  health: Health | null;
  onEditCategories: () => void;
}

const Row = ({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) => (
  <div className="mb-5">
    <div className="mb-1.5 flex items-baseline justify-between">
      <span className="text-[13px] font-medium text-plum">{label}</span>
      {hint && <span className="text-[11px] text-plum/50">{hint}</span>}
    </div>
    {children}
  </div>
);

export function SettingsDrawer({ open, onClose, settings, onChange, presets, customSets, health, onEditCategories }: Props) {
  const set = <K extends keyof UiSettings>(k: K, v: UiSettings[K]) => onChange({ ...settings, [k]: v });
  const [tree, setTree] = useState<TreeNode[]>([]);

  const loadChildren = useCallback(async (path: string) => {
    const res = await api.folders(path);
    const nodes = res.folders.map((f) => ({
      id: f.path,
      pId: path || "__root",
      value: f.path,
      title: `${f.name}${f.media_count ? `  ·  ${f.media_count}` : ""}`,
      isLeaf: !f.has_children,
    }));
    setTree((prev) => {
      const ids = new Set(prev.map((n) => n.id));
      return [...prev, ...nodes.filter((n) => !ids.has(n.id))];
    });
  }, []);

  useEffect(() => {
    if (!open || tree.length) return;
    setTree([{ id: "__root", value: "", title: `${health?.library_name || "Library"} (root)`, isLeaf: false }]);
    loadChildren("").catch(() => {});
  }, [open, tree.length, health, loadChildren]);

  const ai = !!health?.ai_available;

  return (
    <Drawer open={open} onClose={onClose} title="Sort settings" size={400} styles={{ body: { paddingTop: 12 } }}>
      <Row label="Folder to sort" hint="inside the mounted library">
        <TreeSelect
          className="w-full"
          treeDataSimpleMode
          value={settings.source}
          treeData={tree}
          loadData={(node) => loadChildren(String(node.value))}
          onChange={(v) => set("source", v ?? "")}
          treeDefaultExpandedKeys={["__root"]}
        />
      </Row>

      <Row label="How should I organize?">
        <Segmented
          block
          value={settings.strategy}
          onChange={(v) => set("strategy", v as UiSettings["strategy"])}
          options={[
            { value: "preset", label: <span className="inline-flex items-center gap-1"><Shapes size={14} />Preset</span> },
            { value: "custom", label: <span className="inline-flex items-center gap-1"><PencilLine size={14} />Mine</span> },
            { value: "auto", label: <span className="inline-flex items-center gap-1"><Wand2 size={14} />Auto</span> },
            { value: "date", label: <span className="inline-flex items-center gap-1"><CalendarDays size={14} />Date</span> },
          ]}
        />
        <p className="mt-2 text-xs text-plum/60">
          {settings.strategy === "preset" && "Pick a ready-made set of folders, like Lifestyle or Travel."}
          {settings.strategy === "custom" && "Your own folders. Describe each one with a few words and I'll match photos to it."}
          {settings.strategy === "auto" &&
            (ai
              ? "I'll discover groups myself and name them with AI (one tiny request)."
              : "I'll discover groups myself and name them from a built-in vocabulary.")}
          {settings.strategy === "date" && "Year / month folders from the capture date (EXIF), falling back to the file date."}
        </p>
      </Row>

      {settings.strategy === "preset" && (
        <Row label="Preset">
          <Select
            className="w-full"
            value={settings.presetId}
            onChange={(v) => set("presetId", v)}
            options={presets.map((p) => ({ value: p.id, label: `${p.name} · ${p.categories.length} folders` }))}
          />
          <div className="mt-2 flex flex-wrap gap-1">
            {presets
              .find((p) => p.id === settings.presetId)
              ?.categories.map((c) => (
                <span key={c.id} className="rounded-full border border-rose-100 bg-white px-2 py-0.5 text-[11px] text-plum/70">
                  {c.emoji} {c.name}
                </span>
              ))}
          </div>
        </Row>
      )}

      {settings.strategy === "custom" && (
        <Row label="My category set">
          <div className="flex gap-2">
            <Select
              className="flex-1"
              placeholder="Create a set first →"
              value={settings.customSetId ?? undefined}
              onChange={(v) => set("customSetId", v)}
              options={customSets.map((p) => ({ value: p.id, label: `${p.name} · ${p.categories.length}` }))}
            />
            <Button onClick={onEditCategories}>Edit…</Button>
          </div>
        </Row>
      )}

      {settings.strategy === "date" && (
        <Row label="Granularity">
          <Radio.Group
            value={settings.dateGranularity}
            onChange={(e) => set("dateGranularity", e.target.value)}
            options={[
              { value: "year", label: "Year" },
              { value: "month", label: "Month" },
              { value: "day", label: "Day" },
            ]}
            optionType="button"
          />
        </Row>
      )}

      {settings.strategy === "auto" && (
        <Row label="Max folders" hint="the best number is picked automatically">
          <InputNumber min={2} max={30} value={settings.maxClusters} onChange={(v) => set("maxClusters", v ?? 12)} />
        </Row>
      )}

      {(settings.strategy === "preset" || settings.strategy === "custom") && (
        <>
          <Row label="Confidence threshold" hint="below it, files go to Unsorted">
            <Slider min={0.05} max={0.9} step={0.05} value={settings.minConfidence} onChange={(v) => set("minConfidence", v)} />
          </Row>
          <Row label="AI assist for unsure files" hint={ai ? health?.model ?? "" : "no API key"}>
            <Tooltip title={ai ? "Unsure files are sent as tiny thumbnails, 12 per request" : "Set OPENAI_API_KEY in .env to enable"}>
              <span className="inline-flex items-center gap-2">
                <Switch checked={settings.aiAssist && ai} disabled={!ai} onChange={(v) => set("aiAssist", v)} />
                <Sparkles size={14} className="text-rose-400" />
              </span>
            </Tooltip>
          </Row>
        </>
      )}

      <Divider className="my-4" />

      <Row label="Detect near-duplicates" hint="resized / re-saved copies">
        <Switch checked={settings.nearDuplicates} onChange={(v) => set("nearDuplicates", v)} />
      </Row>
      <Row label="Separate Photos and Videos folders">
        <Switch checked={settings.splitMedia} onChange={(v) => set("splitMedia", v)} />
      </Row>
      <Row label="When applying" hint="every apply can be undone">
        <Radio.Group
          value={settings.applyMode}
          onChange={(e) => set("applyMode", e.target.value)}
          options={[
            { value: "move", label: "Move files" },
            { value: "copy", label: "Copy files" },
          ]}
          optionType="button"
        />
      </Row>
    </Drawer>
  );
}

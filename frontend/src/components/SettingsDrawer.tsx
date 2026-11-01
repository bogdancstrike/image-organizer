import { Drawer, Segmented, Select, Slider, Switch, Tooltip, InputNumber, Radio, Button, Divider, Input } from "antd";
import { Sparkles, Shapes, CalendarDays, Wand2, PencilLine, Aperture } from "lucide-react";
import { Checkbox } from "antd";
import type { QualityOptions } from "@/api";
import { type CategorySet, type Health } from "@/api";
import { displayPath } from "./FolderPicker";
import type { UiSettings } from "@/settings";

interface PanelProps {
  settings: UiSettings;
  onChange: (s: UiSettings) => void;
  presets: CategorySet[];
  customSets: CategorySet[];
  health: Health | null;
  onEditCategories: () => void;
  onPickFolder: () => void;
}

interface Props extends PanelProps {
  open: boolean;
  onClose: () => void;
}

export function SettingsDrawer({ open, onClose, ...rest }: Props) {
  return (
    <Drawer open={open} onClose={onClose} title="Sort settings" size={420} styles={{ body: { paddingTop: 12 } }}>
      <SettingsPanel {...rest} />
    </Drawer>
  );
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

export function SettingsPanel({ settings, onChange, presets, customSets, health, onEditCategories, onPickFolder }: PanelProps) {
  const set = <K extends keyof UiSettings>(k: K, v: UiSettings[K]) => onChange({ ...settings, [k]: v });
  const setQ = (patch: Partial<QualityOptions>) => onChange({ ...settings, quality: { ...settings.quality, ...patch } });
  const ai = !!health?.ai_available;

  return (
    <>
      <Row label="Folder to organize" hint="sorted folders are created inside it">
        <div className="flex items-center gap-2">
          <div className="min-w-0 flex-1 truncate rounded-lg border border-line bg-surface px-3 py-1.5 text-[13px] text-plum/80" title={displayPath(health, settings.source)}>
            {displayPath(health, settings.source)}
          </div>
          <Button onClick={onPickFolder}>Change…</Button>
        </div>
      </Row>

      <Row label="Scan" hint={settings.recursive ? "goes deep into every subfolder" : "ignores subfolders"}>
        <Radio.Group
          value={settings.recursive ? "deep" : "flat"}
          onChange={(e) => set("recursive", e.target.value === "deep")}
          optionType="button"
          options={[
            { value: "flat", label: "Only this folder" },
            { value: "deep", label: "This folder + all subfolders" },
          ]}
        />
      </Row>

      <Row label="Put sorted folders">
        <Radio.Group
          value={settings.outputMode}
          onChange={(e) => set("outputMode", e.target.value)}
          options={[
            { value: "subfolder", label: "In a subfolder" },
            { value: "direct", label: "Directly in the folder" },
          ]}
          optionType="button"
        />
        {settings.outputMode === "subfolder" && (
          <Input
            className="mt-2"
            prefix={<span className="text-plum/40">{(settings.source ? settings.source.split("/").pop() : "") + "/"}</span>}
            value={settings.outputDir}
            maxLength={60}
            onChange={(e) => set("outputDir", e.target.value.replace(/[\\/:*?"<>|]/g, ""))}
            placeholder="Organized"
          />
        )}
        <p className="mt-1.5 text-[11px] text-plum/50">
          e.g. {(settings.source ? settings.source.split("/").pop() + "/" : "")}
          {settings.outputMode === "subfolder" ? `${settings.outputDir || "Organized"}/` : ""}
          {settings.splitMedia ? "Photos/" : ""}Food & cafés/IMG_0042.jpg
        </p>
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
            { value: "cull", label: <span className="inline-flex items-center gap-1"><Aperture size={14} />Cull</span> },
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
          {settings.strategy === "cull" &&
            "For a shoot: Keepers, Smiling, and rejects (Blurry, Eyes closed, Too dark/bright). Tune the checks below."}
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
                <span key={c.id} className="rounded-full border border-line bg-surface px-2 py-0.5 text-[11px] text-plum/70">
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
                <Sparkles size={14} className="text-petal" />
              </span>
            </Tooltip>
          </Row>
        </>
      )}

      <Divider className="my-4" />

      <div className="mb-3 flex items-center gap-2 label-caps">
        <Aperture size={13} /> Pro · culling & quality
      </div>
      {settings.strategy !== "cull" && (
        <Row label="Check photo quality" hint="sharpness, eyes, smiles, exposure">
          <Switch checked={settings.quality.enabled} onChange={(v) => setQ({ enabled: v })} />
        </Row>
      )}
      {(settings.strategy === "cull" || settings.quality.enabled) && (
        <div className="mb-5 rounded-xl border border-line bg-surface/60 p-3">
          <div className="mb-3 grid grid-cols-2 gap-y-1.5">
            <Checkbox checked={settings.quality.blur} onChange={(e) => setQ({ blur: e.target.checked })}>Blurry / out of focus</Checkbox>
            <Checkbox
              checked={settings.quality.eyes_closed}
              disabled={!health?.faces_available}
              onChange={(e) => setQ({ eyes_closed: e.target.checked })}
            >
              Eyes closed
            </Checkbox>
            <Checkbox checked={settings.quality.exposure} onChange={(e) => setQ({ exposure: e.target.checked })}>Too dark / bright</Checkbox>
            <Checkbox
              checked={settings.quality.smiles}
              disabled={!health?.faces_available}
              onChange={(e) => setQ({ smiles: e.target.checked })}
            >
              Smiles ({settings.strategy === "cull" ? "own folder" : "tag"})
            </Checkbox>
          </div>
          <Row label="Sharpness needed" hint={`${Math.round(settings.quality.blur_threshold * 100)}%`}>
            <Slider min={0.2} max={0.85} step={0.01} value={settings.quality.blur_threshold} onChange={(v) => setQ({ blur_threshold: v })} />
          </Row>
          <Row label="Eyes-closed sensitivity" hint={`blink ≥ ${Math.round(settings.quality.blink_threshold * 100)}%`}>
            <Slider min={0.2} max={0.9} step={0.05} value={settings.quality.blink_threshold} onChange={(v) => setQ({ blink_threshold: v })} />
          </Row>
          <Row label="Smile needed" hint={`≥ ${Math.round(settings.quality.smile_threshold * 100)}%`}>
            <Slider min={0.2} max={0.9} step={0.05} value={settings.quality.smile_threshold} onChange={(v) => setQ({ smile_threshold: v })} />
          </Row>
          {settings.strategy !== "cull" && (
            <Row label="Bad shots">
              <Radio.Group
                value={settings.quality.action}
                onChange={(e) => setQ({ action: e.target.value })}
                optionType="button"
                options={[
                  { value: "reject", label: "Move to _Rejects/" },
                  { value: "tag", label: "Only tag them" },
                ]}
              />
            </Row>
          )}
          {!health?.faces_available && <p className="text-[11px] text-plum/50">Face model not found: eyes & smile checks are off.</p>}
        </div>
      )}
      <Row label="Keep RAW + JPEG pairs & sidecars together" hint=".ARW/.CR2/.NEF… + .xmp">
        <Switch checked={settings.pairSidecars} onChange={(v) => set("pairSidecars", v)} />
      </Row>

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
    </>
  );
}

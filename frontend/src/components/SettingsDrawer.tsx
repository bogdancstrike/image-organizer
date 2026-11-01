import { useEffect, useState, type ReactNode } from "react";
import { Button, Checkbox, Drawer, Input, InputNumber, Popconfirm, Radio, Rate, Segmented, Select, Slider, Switch, Tag, Tooltip } from "antd";
import {
  Aperture,
  CalendarDays,
  Copy,
  Cpu,
  FolderOpen,
  FolderTree,
  Palette,
  PencilLine,
  RotateCcw,
  Shapes,
  Sparkles,
  Wand2,
  Workflow,
} from "lucide-react";
import { api, type AIOptions, type CategorySet, type Health, type QualityOptions } from "@/api";
import { DEFAULT_SETTINGS, type UiSettings } from "@/settings";
import { THEMES, useTheme } from "@/theme";
import { cn } from "@/lib/utils";
import { displayPath } from "./FolderPicker";
import { Card } from "./ui/card";

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
    <Drawer open={open} onClose={onClose} title="Sort settings" size={560} styles={{ body: { padding: "8px 28px 32px" } }}>
      <SettingsPanel {...rest} layout="drawer" />
    </Drawer>
  );
}

/* ------------------------------------------------------------------ building blocks */

function Row({ label, hint, children, inline }: { label: string; hint?: ReactNode; children: ReactNode; inline?: boolean }) {
  return (
    <div className={cn("py-3", inline && "flex items-center justify-between gap-6")}>
      <div className={cn("flex items-baseline justify-between gap-3", !inline && "mb-2")}>
        <span className="text-[13px] font-medium text-plum">{label}</span>
        {hint && !inline && <span className="text-right text-[11px] text-plum/50">{hint}</span>}
      </div>
      {inline ? (
        <div className="flex items-center gap-3">
          {hint && <span className="text-right text-[11px] text-plum/50">{hint}</span>}
          {children}
        </div>
      ) : (
        children
      )}
    </div>
  );
}

const SECTIONS = [
  { id: "folder", title: "Folder", icon: FolderOpen, desc: "What to sort and where the sorted folders go." },
  { id: "organize", title: "Organizing", icon: Shapes, desc: "How files are grouped into folders." },
  { id: "pro", title: "Pro · culling & quality", icon: Aperture, desc: "Sharpness, eyes closed, smiles and exposure, for photographers." },
  { id: "files", title: "Files & duplicates", icon: FolderTree, desc: "Duplicates, RAW pairs and how files are moved." },
  { id: "ai", title: "AI", icon: Sparkles, desc: "Optional help from OpenAI. Everything else runs locally." },
  { id: "appearance", title: "Appearance", icon: Palette, desc: "Pick a theme. It is remembered on this device." },
  { id: "system", title: "System", icon: Cpu, desc: "What is running, and resetting settings." },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

function Section({ id, page, children }: { id: SectionId; page: boolean; children: ReactNode }) {
  const meta = SECTIONS.find((s) => s.id === id)!;
  const Icon = meta.icon;
  if (!page) {
    return (
      <section className="border-b border-line py-4 last:border-0">
        <div className="mb-1 flex items-center gap-2 label-caps">
          <Icon size={13} /> {meta.title}
        </div>
        <div className="divide-y divide-line/60">{children}</div>
      </section>
    );
  }
  return (
    <Card id={`settings-${id}`} className="scroll-mt-6 px-6 py-5">
      <header className="mb-2 flex items-start gap-3">
        <span className="rounded-xl bg-tint p-2 text-plum/80">
          <Icon size={18} />
        </span>
        <div>
          <h3 className="text-[16px] font-semibold text-plum">{meta.title}</h3>
          <p className="text-xs text-plum/55">{meta.desc}</p>
        </div>
      </header>
      <div className="divide-y divide-line/60">{children}</div>
    </Card>
  );
}

/* ------------------------------------------------------------------ the panel */

export function SettingsPanel({
  settings,
  onChange,
  presets,
  customSets,
  health,
  onEditCategories,
  onPickFolder,
  layout = "drawer",
}: PanelProps & { layout?: "drawer" | "page" }) {
  const set = <K extends keyof UiSettings>(k: K, v: UiSettings[K]) => onChange({ ...settings, [k]: v });
  const setQ = (patch: Partial<QualityOptions>) => onChange({ ...settings, quality: { ...settings.quality, ...patch } });
  const setAI = (patch: Partial<AIOptions>) => onChange({ ...settings, ai: { ...settings.ai, ...patch } });
  const [models, setModels] = useState<string[]>([]);
  useEffect(() => {
    if (health?.ai_available) api.aiModels().then((r) => setModels(r.models)).catch(() => {});
  }, [health?.ai_available]);
  const { theme, setTheme } = useTheme();
  const ai = !!health?.ai_available;
  const page = layout === "page";
  const folderName = settings.source ? settings.source.split("/").pop() + "/" : "";
  const example = `${folderName}${settings.outputMode === "subfolder" ? `${settings.outputDir || "Organized"}/` : ""}${settings.splitMedia ? "Photos/" : ""}Food & cafés/IMG_0042.jpg`;
  const qualityOn = settings.strategy === "cull" || settings.quality.enabled;

  const body = (
    <>
      <Section id="folder" page={page}>
        <Row label="Folder to organize" hint="sorted folders are created inside it">
          <div className="flex items-center gap-2">
            <div
              className="min-w-0 flex-1 truncate rounded-lg border border-line bg-surface px-3 py-1.5 text-[13px] text-plum/80"
              title={displayPath(health, settings.source)}
            >
              {displayPath(health, settings.source)}
            </div>
            <Button onClick={onPickFolder} icon={<FolderOpen size={14} />}>
              Change…
            </Button>
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
          <div className="flex flex-wrap items-center gap-2">
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
                className="!w-48"
                value={settings.outputDir}
                maxLength={60}
                onChange={(e) => set("outputDir", e.target.value.replace(/[\\/:*?"<>|]/g, ""))}
                placeholder="Organized"
              />
            )}
          </div>
          <p className="mt-2 truncate font-mono text-[11px] text-plum/50">→ {example}</p>
        </Row>
        <Row label="Separate Photos/ and Videos/" inline>
          <Switch checked={settings.splitMedia} onChange={(v) => set("splitMedia", v)} />
        </Row>
      </Section>

      <Section id="organize" page={page}>
        <Row label="Strategy">
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
            {settings.strategy === "preset" && "Ready-made folders such as Lifestyle, People & Style, Wedding day or Real estate. All of them can be edited."}
            {settings.strategy === "custom" && "Your own folders. Describe each one in a few words and photos are matched to it."}
            {settings.strategy === "auto" &&
              (ai
                ? "Groups are discovered automatically and named by AI (a single small request)."
                : "Groups are discovered automatically and named from a built-in vocabulary.")}
            {settings.strategy === "date" && "Year / month folders from the capture date (EXIF), falling back to the file date."}
            {settings.strategy === "cull" &&
              "For a shoot: Keepers, Smiling, and rejects (Blurry, Eyes closed, Too dark/bright). Tune the checks under Pro."}
          </p>
        </Row>

        {settings.strategy === "preset" && (
          <Row label="Preset" hint={<a onClick={onEditCategories}>edit…</a>}>
            <Select
              className="w-full"
              value={settings.presetId}
              onChange={(v) => set("presetId", v)}
              options={presets.map((p) => ({
                value: p.id,
                label: `${p.name} · ${p.categories.length} folders${p.modified ? " · edited" : ""}`,
              }))}
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
              <Button onClick={onEditCategories} icon={<PencilLine size={14} />}>
                Edit…
              </Button>
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
          <>
            <Row label="Group by" hint="what should separate the folders?">
              <Select
                className="w-full"
                value={settings.focus}
                onChange={(v) => set("focus", v)}
                options={[
                  { value: "auto", label: "✨ Whatever separates them best" },
                  { value: "scene", label: "🏞️ Scene & location (studio, mountains, beach, city…)" },
                  { value: "framing", label: "🧍 Framing & pose (close-up, full-body, sitting, details…)" },
                  { value: "outfit", label: "👗 Outfit (dress, suit, swimwear, costume…)" },
                  { value: "lighting", label: "💡 Lighting (golden hour, low-key, studio flash, B&W…)" },
                  { value: "subject", label: "🔎 Subject (portraits, couple, food, pets, cars…)" },
                ]}
              />
            </Row>
            <Row label="Granularity" hint={settings.granularity === "fine" ? "more, smaller folders" : settings.granularity === "coarse" ? "a few big folders" : "balanced"}>
              <Segmented
                value={settings.granularity}
                onChange={(v) => set("granularity", v as UiSettings["granularity"])}
                options={[
                  { value: "coarse", label: "Coarse" },
                  { value: "normal", label: "Normal" },
                  { value: "fine", label: "Fine" },
                ]}
              />
            </Row>
            <Row label="Max folders" hint="upper bound; the best number is chosen automatically" inline>
              <InputNumber min={2} max={30} value={settings.maxClusters} onChange={(v) => set("maxClusters", v ?? 12)} />
            </Row>
          </>
        )}

        {(settings.strategy === "preset" || settings.strategy === "custom") && (
          <Row label="Confidence threshold" hint={`below ${Math.round(settings.minConfidence * 100)}%, files go to Unsorted`}>
            <Slider min={0.05} max={0.9} step={0.05} value={settings.minConfidence} onChange={(v) => set("minConfidence", v)} />
          </Row>
        )}
      </Section>

      <Section id="pro" page={page}>
        {settings.strategy !== "cull" && (
          <Row label="Check photo quality" hint="sharpness · eyes · smiles · exposure" inline>
            <Switch checked={settings.quality.enabled} onChange={(v) => setQ({ enabled: v })} />
          </Row>
        )}
        {qualityOn ? (
          <>
            <Row label="Checks">
              <div className="grid grid-cols-1 gap-y-1.5 sm:grid-cols-2">
                <Checkbox checked={settings.quality.blur} onChange={(e) => setQ({ blur: e.target.checked })}>
                  🌫️ Blurry / out of focus
                </Checkbox>
                <Checkbox
                  checked={settings.quality.eyes_closed}
                  disabled={!health?.faces_available}
                  onChange={(e) => setQ({ eyes_closed: e.target.checked })}
                >
                  😑 Eyes closed
                </Checkbox>
                <Checkbox checked={settings.quality.exposure} onChange={(e) => setQ({ exposure: e.target.checked })}>
                  🌑 Too dark / bright
                </Checkbox>
                <Checkbox
                  checked={settings.quality.smiles}
                  disabled={!health?.faces_available}
                  onChange={(e) => setQ({ smiles: e.target.checked })}
                >
                  😄 Smiles ({settings.strategy === "cull" ? "own folder" : "tag"})
                </Checkbox>
              </div>
            </Row>
            <Row label="Sharpness needed" hint={`${Math.round(settings.quality.blur_threshold * 100)}%: higher is stricter`}>
              <Slider min={0.2} max={0.85} step={0.01} value={settings.quality.blur_threshold} onChange={(v) => setQ({ blur_threshold: v })} />
            </Row>
            <Row label="Eyes-closed sensitivity" hint={`blink ≥ ${Math.round(settings.quality.blink_threshold * 100)}%`}>
              <Slider min={0.2} max={0.9} step={0.05} value={settings.quality.blink_threshold} onChange={(v) => setQ({ blink_threshold: v })} />
            </Row>
            <Row label="Smile needed" hint={`≥ ${Math.round(settings.quality.smile_threshold * 100)}%`}>
              <Slider min={0.2} max={0.9} step={0.05} value={settings.quality.smile_threshold} onChange={(v) => setQ({ smile_threshold: v })} />
            </Row>
            <Row label="Whose eyes & smile count">
              <Radio.Group
                value={settings.quality.faces_rule}
                onChange={(e) => setQ({ faces_rule: e.target.value })}
                optionType="button"
                options={[
                  { value: "any", label: "Any face (group shots)" },
                  { value: "main", label: "Main subject only" },
                ]}
              />
            </Row>
            <Row label="Exposure limits" hint={`dark < ${Math.round(settings.quality.dark_threshold * 100)}% · bright > ${Math.round(settings.quality.bright_threshold * 100)}%`}>
              <Slider
                range
                min={0}
                max={1}
                step={0.01}
                value={[settings.quality.dark_threshold, settings.quality.bright_threshold]}
                onChange={(v) => setQ({ dark_threshold: Math.min(0.5, v[0]), bright_threshold: Math.max(0.5, v[1]) })}
              />
            </Row>
            <Row label="Best of burst" hint="near-identical frames seconds apart: keep the best" inline>
              <Switch checked={settings.quality.bursts} onChange={(v) => setQ({ bursts: v })} />
            </Row>
            {settings.quality.bursts && (
              <div className="grid gap-x-6 sm:grid-cols-2">
                <Row label="Burst window" hint={`${settings.quality.burst_seconds}s`}>
                  <Slider min={0.5} max={10} step={0.5} value={settings.quality.burst_seconds} onChange={(v) => setQ({ burst_seconds: v })} />
                </Row>
                <Row label="Burst similarity" hint={`${Math.round(settings.quality.burst_similarity * 100)}%`}>
                  <Slider min={0.8} max={0.98} step={0.01} value={settings.quality.burst_similarity} onChange={(v) => setQ({ burst_similarity: v })} />
                </Row>
              </div>
            )}
            {settings.strategy === "cull" && (
              <Row label="Keepers need at least" hint={settings.quality.keeper_min_stars ? "others go to Maybe" : "off"} inline>
                <Rate value={settings.quality.keeper_min_stars} onChange={(v) => setQ({ keeper_min_stars: v })} allowClear />
              </Row>
            )}
            {settings.strategy !== "cull" && (
              <Row label="Bad shots">
                <Radio.Group
                  value={settings.quality.action}
                  onChange={(e) => setQ({ action: e.target.value })}
                  optionType="button"
                  options={[
                    { value: "reject", label: "Move to _Rejects/<reason>" },
                    { value: "tag", label: "Only tag them" },
                  ]}
                />
              </Row>
            )}
            {!health?.faces_available && <p className="py-2 text-[11px] text-plum/50">Face model not found: eyes & smile checks are off.</p>}
          </>
        ) : (
          <p className="py-2 text-xs text-plum/50">Turn on to flag blurry shots, closed eyes and bad exposure, or pick the Cull strategy.</p>
        )}
      </Section>

      <Section id="files" page={page}>
        <Row label="Detect near-duplicates" hint="resized / re-saved copies" inline>
          <Switch checked={settings.nearDuplicates} onChange={(v) => set("nearDuplicates", v)} />
        </Row>
        <Row label="Keep RAW + JPEG pairs & sidecars together" hint=".ARW .CR2 .NEF … + .xmp" inline>
          <Switch checked={settings.pairSidecars} onChange={(v) => set("pairSidecars", v)} />
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
      </Section>

      <Section id="ai" page={page}>
        <Row label="Status" inline>
          {ai ? <Tag color="green">connected · {health?.model}</Tag> : <Tag>off · no OPENAI_API_KEY</Tag>}
        </Row>
        <Row label="AI assist for unsure files" hint="preset & custom strategies" inline>
          <Tooltip title={ai ? "Only unsure files are sent, as small thumbnails, 12 per request" : "Set OPENAI_API_KEY in .env to enable"}>
            <Switch checked={settings.aiAssist && ai} disabled={!ai} onChange={(v) => set("aiAssist", v)} />
          </Tooltip>
        </Row>
        <Row label="Model" hint={`server default: ${health?.model ?? "–"}`}>
          <Select
            className="w-full"
            disabled={!ai}
            allowClear
            placeholder={health?.model ?? "default"}
            value={settings.ai.model ?? undefined}
            onChange={(v) => setAI({ model: v ?? null })}
            options={(models.length ? models : health?.model ? [health.model] : []).map((m) => ({ value: m, label: m }))}
            showSearch
          />
        </Row>
        <Row label="Reasoning effort" hint="low = fast & cheap">
          <Segmented
            disabled={!ai}
            value={settings.ai.reasoning_effort ?? "default"}
            onChange={(v) => setAI({ reasoning_effort: v === "default" ? null : (v as AIOptions["reasoning_effort"]) })}
            options={[
              { value: "default", label: "Default" },
              { value: "minimal", label: "Minimal" },
              { value: "low", label: "Low" },
              { value: "medium", label: "Medium" },
              { value: "high", label: "High" },
            ]}
          />
        </Row>
        <Row label="Naming instructions" hint="added to the auto-naming prompt">
          <Input.TextArea
            disabled={!ai}
            autoSize={{ minRows: 2, maxRows: 6 }}
            maxLength={1500}
            showCount
            value={settings.ai.naming_instructions}
            onChange={(e) => setAI({ naming_instructions: e.target.value })}
            placeholder="e.g. Use short lowercase names like my Instagram folders. Separate indoor and outdoor. Name in Romanian."
          />
        </Row>
        <Row label="Assist instructions" hint="added to the AI-assist prompt">
          <Input.TextArea
            disabled={!ai}
            autoSize={{ minRows: 2, maxRows: 6 }}
            maxLength={1500}
            showCount
            value={settings.ai.assist_instructions}
            onChange={(e) => setAI({ assist_instructions: e.target.value })}
            placeholder="e.g. Motorbikes always go to “moto”, even with people on them."
          />
        </Row>
        <Row label="Photos per assist request" hint="fewer = more accurate, more requests" inline>
          <InputNumber disabled={!ai} min={1} max={24} value={settings.ai.assist_batch} onChange={(v) => setAI({ assist_batch: v ?? 12 })} />
        </Row>
        <p className="py-2 text-[11px] text-plum/50">
          Auto mode names its groups with a single request. Images are sent at low detail, and reasoning effort is low. Nothing is sent
          without a key. Private content? Keep AI assist off: CLIP runs fully offline.
        </p>
      </Section>

      <Section id="appearance" page={page}>
        <div className="grid grid-cols-2 gap-2 py-3 sm:grid-cols-4">
          {THEMES.map((t) => (
            <button
              key={t.id}
              onClick={() => setTheme(t.id)}
              className={cn(
                "group cursor-pointer rounded-xl border border-line p-1.5 text-left transition-transform hover:-translate-y-0.5",
                theme === t.id && "ring-2 ring-petal",
              )}
            >
              <div className="h-12 rounded-lg" style={{ background: `linear-gradient(135deg, ${t.swatch[0]} 0%, ${t.swatch[1]} 100%)` }} />
              <div className="mt-1.5 truncate px-0.5 text-[11px] text-plum/80">{t.label}</div>
            </button>
          ))}
        </div>
      </Section>

      <Section id="system" page={page}>
        <Row label="Version" inline>
          <span className="text-xs text-plum/70">v{health?.version ?? "…"}</span>
        </Row>
        <Row label="Mounted library" inline>
          <span className="max-w-72 truncate font-mono text-xs text-plum/70">{health?.library_host_path ?? "/library"}</span>
        </Row>
        <Row label="Engines" inline>
          <span className="flex flex-wrap justify-end gap-1">
            <Tag className="m-0">CLIP ViT-B/32 · local</Tag>
            <Tag className="m-0" color={health?.faces_available ? "green" : undefined}>
              MediaPipe faces {health?.faces_available ? "· on" : "· off"}
            </Tag>
          </span>
        </Row>
        <Row label="Reset all settings" hint="themes and category sets are kept" inline>
          <Popconfirm title="Restore every sort setting to its default?" onConfirm={() => onChange(DEFAULT_SETTINGS)}>
            <Button icon={<RotateCcw size={14} />}>Reset</Button>
          </Popconfirm>
        </Row>
        <Row label="Copy settings as JSON" hint="handy for bug reports" inline>
          <Button icon={<Copy size={14} />} onClick={() => navigator.clipboard?.writeText(JSON.stringify(settings, null, 2))}>
            Copy
          </Button>
        </Row>
      </Section>
    </>
  );

  if (!page) return body;

  return (
    <div className="grid gap-8 lg:grid-cols-[220px_minmax(0,1fr)]">
      <nav className="hidden lg:block">
        <div className="sticky top-6 space-y-0.5">
          <div className="mb-2 flex items-center gap-2 label-caps">
            <Workflow size={12} /> Settings
          </div>
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                onClick={() => document.getElementById(`settings-${s.id}`)?.scrollIntoView({ behavior: "smooth", block: "start" })}
                className="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[13px] text-plum/75 hover:bg-tint hover:text-plum"
              >
                <Icon size={14} /> {s.title}
              </button>
            );
          })}
          <p className="px-2.5 pt-3 text-[11px] text-plum/45">Changes are saved automatically.</p>
        </div>
      </nav>
      <div className="max-w-3xl space-y-5">{body}</div>
    </div>
  );
}

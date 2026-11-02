import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { PromptRulesInput } from "./PromptRulesInput";
import { FacePicker } from "./FacePicker";
import { Button, Checkbox, Drawer, Input, InputNumber, Modal, Popconfirm, Radio, Segmented, Select, Slider, Switch, Tag, Tooltip } from "antd";
import {
  Aperture,
  CalendarDays,
  Users,
  Plane,
  MapPin,
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
import { api, type AIDefaults, type AIOptions, type CategorySet, type Health, type QualityOptions } from "@/api";
import { DEFAULT_SETTINGS, type UiSettings } from "@/settings";
import { THEMES, useTheme } from "@/theme";
import { LANGS, useI18n } from "@/i18n";
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
  gpsAvailable?: boolean; // the folder has photos with GPS: offer trips & places
}

interface Props extends PanelProps {
  open: boolean;
  onClose: () => void;
  onOpenAll: () => void;
}

/** Quick settings: only what you tweak between sorts (how to organize, culling). Everything else lives on /settings. */
export function SettingsDrawer({ open, onClose, onOpenAll, ...rest }: Props) {
  const { t } = useI18n();
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={t("quick.title")}
      size={600}
      styles={{ body: { padding: "8px 28px 32px" } }}
      footer={
        <div className="flex items-center justify-between">
          <span className="text-xs text-plum/50">{t("quick.saved")}</span>
          <Button type="link" onClick={onOpenAll}>
            {t("quick.all")}
          </Button>
        </div>
      }
    >
      <SettingsPanel {...rest} layout="drawer" only={["organize", "pro"]} />
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

const RESET_PHRASE = "delete all data";

/** Factory reset, GitHub-style: type the phrase to enable the button. Photos on disk are never touched. */
function DangerZone() {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [cache, setCache] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ok = typed.trim().toLowerCase() === RESET_PHRASE;
  const close = () => {
    setOpen(false);
    setTyped("");
    setError(null);
  };
  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.factoryReset(typed, cache);
      try {
        Object.keys(localStorage)
          .filter((k) => k.startsWith("aio."))
          .forEach((k) => localStorage.removeItem(k));
      } catch {
        /* storage unavailable */
      }
      window.location.assign("/sort");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };
  return (
    <div className="mt-4 rounded-xl border border-red-500/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[13px] font-semibold text-red-500">Danger zone · delete all app data</div>
          <div className="text-[11px] text-plum/55">History, statistics, saved sorts, settings, faces and your category sets. Like a fresh install.</div>
        </div>
        <Button danger onClick={() => setOpen(true)}>
          Delete all data…
        </Button>
      </div>
      <Modal
        open={open}
        onCancel={close}
        title="Delete all app data?"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={close}>Cancel</Button>
            <Button danger type="primary" disabled={!ok} loading={busy} onClick={run}>
              I understand, delete everything
            </Button>
          </div>
        }
      >
        <ul className="mb-3 list-disc space-y-1 pl-5 text-[13px] text-plum/80">
          <li>History and undo records: <b>applied sorts can no longer be undone</b>.</li>
          <li>Statistics, saved sorts, settings, uploaded faces.</li>
          <li>Your category sets and edits to presets (presets come back as shipped).</li>
          <li>Your photos and folders are <b>not</b> touched. Files in a <code>.aio-trash</code> folder stay there.</li>
        </ul>
        <Checkbox checked={cache} onChange={(e) => setCache(e.target.checked)}>
          Also clear the analysis cache (thumbnails, embeddings, faces, OCR: the next sort re-analyzes everything)
        </Checkbox>
        <p className="mb-1.5 mt-4 text-[13px]">
          To confirm, type <b className="select-all font-mono">{RESET_PHRASE}</b>
        </p>
        <Input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={RESET_PHRASE} status={typed && !ok ? "warning" : undefined} autoFocus />
        {error && <p className="mt-2 text-[12px] text-red-500">{error}</p>}
      </Modal>
    </div>
  );
}

const CHECK_KEYS = ["blur", "eyes_closed", "smiles", "exposure", "noise_check", "face_crop", "tilt_check", "bursts"] as const;

/** Lightroom-style optional panel: a switch; its controls only appear when it is on. */
function Check({ label, hint, on, set, disabled, children }: { label: string; hint?: string; on: boolean; set: (v: boolean) => void; disabled?: boolean; children?: ReactNode }) {
  return (
    <div className={cn("border-b border-line/60 last:border-0", disabled && "opacity-50")}>
      <label className="flex cursor-pointer items-center justify-between gap-4 py-2.5">
        <span className="min-w-0">
          <span className="text-[13px] font-medium text-plum">{label}</span>
          {hint && <span className="ml-2 text-[11px] text-plum/50">{hint}</span>}
        </span>
        <Switch size="small" checked={on && !disabled} disabled={disabled} onChange={set} />
      </label>
      {on && !disabled && children && <div className="mb-2 ml-1 border-l-2 border-line pl-4">{children}</div>}
    </div>
  );
}

const SECTIONS = [
  { id: "folder", key: "st.folder", title: "Folder", icon: FolderOpen, desc: "What to sort and where the sorted folders go." },
  { id: "organize", key: "st.organize", title: "Organizing", icon: Shapes, desc: "How files are grouped into folders." },
  { id: "pro", key: "st.pro", title: "Pro · culling & quality", icon: Aperture, desc: "Sharpness, eyes closed, smiles and exposure, for photographers." },
  { id: "files", key: "st.files", title: "Files & duplicates", icon: FolderTree, desc: "Duplicates, RAW pairs and how files are moved." },
  { id: "ai", key: "st.ai", title: "AI", icon: Sparkles, desc: "Optional help from OpenAI. Everything else runs locally." },
  { id: "appearance", key: "st.appearance", title: "Appearance", icon: Palette, desc: "Pick a theme. It is remembered on this device." },
  { id: "system", key: "st.system", title: "System", icon: Cpu, desc: "What is running, and resetting settings." },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

const OnlyCtx = createContext<SectionId[] | null>(null);

function Section({ id, page, children }: { id: SectionId; page: boolean; children: ReactNode }) {
  const only = useContext(OnlyCtx);
  const { t } = useI18n();
  if (only && !only.includes(id)) return null;
  const meta = SECTIONS.find((s) => s.id === id)!;
  const Icon = meta.icon;
  if (!page) {
    return (
      <section className="border-b border-line py-4 last:border-0">
        <div className="mb-1 flex items-center gap-2 label-caps">
          <Icon size={13} /> {t(meta.key)}
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
          <h3 className="text-[16px] font-semibold text-plum">{t(meta.key)}</h3>
          <p className="text-xs text-plum/55">{meta.desc}</p>
        </div>
      </header>
      <div className="divide-y divide-line/60">{children}</div>
    </Card>
  );
}

/** A prompt shown pre-filled with the default; editing stores a custom template, Reset goes back to the default. */
function PromptEditor(props: {
  label: string;
  value: string;
  fallback: string;
  placeholders: string[];
  format?: string;
  note?: string;
  disabled?: boolean;
  onChange: (v: string) => void;
}) {
  const custom = !!props.value;
  return (
    <Row
      label={props.label}
      hint={
        custom ? (
          <a onClick={() => props.onChange("")}>reset to default</a>
        ) : (
          <span>default</span>
        )
      }
    >
      <Input.TextArea
        disabled={props.disabled}
        autoSize={{ minRows: 4, maxRows: 12 }}
        maxLength={4000}
        value={props.value || props.fallback}
        onChange={(e) => props.onChange(e.target.value === props.fallback ? "" : e.target.value)}
        className="font-mono !text-[12px]"
      />
      <p className="mt-1.5 text-[11px] text-plum/50">
        Placeholders: {props.placeholders.map((p) => <code key={p} className="mr-1">{p}</code>)}
        {props.note ? <> · {props.note}</> : null}
        {props.format ? <> · Always appended: <code>{props.format}</code></> : null}
      </p>
    </Row>
  );
}

/** Clickable cards: name, folder count and a preview of the folders. */
function SetPicker({ sets, value, onPick }: { sets: CategorySet[]; value: string | null; onPick: (id: string) => void }) {
  return (
    <div className="grid max-h-[340px] grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
      {sets.map((s) => {
        const active = s.id === value;
        return (
          <button
            key={s.id}
            onClick={() => onPick(s.id)}
            className={cn(
              "cursor-pointer rounded-xl border p-2.5 text-left transition-all hover:-translate-y-px",
              active ? "border-plum/60 bg-tint ring-1 ring-plum/40" : "border-line bg-surface/60 hover:border-plum/30",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-[13px] font-medium text-plum">
                {s.name}
                {s.modified && <span className="ml-1 text-[10px] text-amber-500">●</span>}
              </span>
              <span className="shrink-0 text-[11px] text-plum/45">{s.categories.length}</span>
            </div>
            <div className="mt-1 truncate text-[12px] leading-5 text-plum/60" title={s.categories.map((c) => c.name).join(" · ")}>
              {s.categories.slice(0, 8).map((c) => c.emoji ?? "📁").join(" ")}
            </div>
            <div className="truncate text-[11px] text-plum/45">{s.categories.slice(0, 4).map((c) => c.name).join(" · ")}…</div>
          </button>
        );
      })}
    </div>
  );
}

function LangSelect() {
  const { lang, setLang } = useI18n();
  return (
    <Select
      value={lang}
      onChange={setLang}
      className="w-44"
      options={LANGS.map((l) => ({ value: l.id, label: `${l.flag} ${l.label}` }))}
    />
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
  gpsAvailable = false,
  layout = "drawer",
  only,
}: PanelProps & { layout?: "drawer" | "page"; only?: SectionId[] }) {
  const set = <K extends keyof UiSettings>(k: K, v: UiSettings[K]) => onChange({ ...settings, [k]: v });
  const setQ = (patch: Partial<QualityOptions>) => {
    const q = { ...settings.quality, ...patch };
    q.enabled = CHECK_KEYS.some((k) => q[k]);
    onChange({ ...settings, quality: q });
  };
  const Q = settings.quality;
  const latest = useRef(settings);
  latest.current = settings;
  const onFace = useCallback((id: string | null) => onChange({ ...latest.current, peopleReference: id }), [onChange]);
  const faces = !!health?.faces_available;
  const anyCheck = CHECK_KEYS.some((k) => Q[k]);
  const setAI = (patch: Partial<AIOptions>) => onChange({ ...settings, ai: { ...settings.ai, ...patch } });
  const [models, setModels] = useState<string[]>([]);
  const [defaults, setDefaults] = useState<AIDefaults | null>(null);
  useEffect(() => {
    api.aiDefaults().then(setDefaults).catch(() => {});
    if (health?.ai_available) api.aiModels().then((r) => setModels(r.models)).catch(() => {});
  }, [health?.ai_available]);
  const { theme, setTheme } = useTheme();
  const { t } = useI18n();
  const ai = !!health?.ai_available;
  const page = layout === "page";
  const folderName = settings.source ? settings.source.split("/").pop() + "/" : "";
  const example = `${folderName}${settings.outputMode === "subfolder" ? `${settings.outputDir || "Organized"}/` : ""}${settings.splitMedia ? "Photos/" : ""}Food & cafés/IMG_0042.jpg`;

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
        <Row label="Separate Photos/ and Videos/" hint={settings.strategy === "rules" ? "Prompt rules use your exact destination paths." : undefined} inline>
          <Switch checked={settings.splitMedia && settings.strategy !== "rules"} disabled={settings.strategy === "rules"} onChange={(v) => set("splitMedia", v)} />
        </Row>
      </Section>

      <Section id="organize" page={page}>
        <Row label="Strategy">
          <Segmented
            block
            value={settings.strategy}
            onChange={(v) => set("strategy", v as UiSettings["strategy"])}
            options={[
              { value: "rules", label: <span className="inline-flex items-center gap-1"><Wand2 size={14} />{t("rules.title")}</span> },
              { value: "preset", label: <span className="inline-flex items-center gap-1"><Shapes size={14} />Preset</span> },
              { value: "custom", label: <span className="inline-flex items-center gap-1"><PencilLine size={14} />Mine</span> },
              { value: "auto", label: <span className="inline-flex items-center gap-1"><Wand2 size={14} />Auto</span> },
              { value: "date", label: <span className="inline-flex items-center gap-1"><CalendarDays size={14} />Date</span> },
              { value: "cull", label: <span className="inline-flex items-center gap-1"><Aperture size={14} />Cull</span> },
              { value: "people", label: <span className="inline-flex items-center gap-1"><Users size={14} />People</span> },
              ...(gpsAvailable || settings.strategy === "trips" || settings.strategy === "places"
                ? [
                    { value: "trips", label: <span className="inline-flex items-center gap-1"><Plane size={14} />Trips</span> },
                    { value: "places", label: <span className="inline-flex items-center gap-1"><MapPin size={14} />Places</span> },
                  ]
                : []),
            ]}
          />
          <p className="mt-2 text-xs text-plum/60">
            {settings.strategy === "trips" && "Trips from GPS and dates, named like “Rome · May 2025”. Everything else goes to Everyday."}
            {settings.strategy === "places" && "One folder per country (or city) from GPS. Place names are looked up offline."}
            {settings.strategy === "preset" && "Ready-made folders such as Lifestyle, People & Style, Wedding day or Real estate. All of them can be edited."}
            {settings.strategy === "custom" && "Your own folders. Describe each one in a few words and photos are matched to it."}
            {settings.strategy === "auto" &&
              (ai
                ? "Groups are discovered automatically and named by AI (a single small request)."
                : "Groups are discovered automatically and named from a built-in vocabulary.")}
            {settings.strategy === "date" && "Year / month folders from the capture date (EXIF), falling back to the file date."}
            {settings.strategy === "people" && "One folder per person, recognized by face. Group photos and photos without people get their own folders. You can rename people after sorting."}
          {settings.strategy === "cull" &&
              "For a shoot: Keepers, Smiling, and rejects (Blurry, Eyes closed, Too dark/bright). Tune the checks under Pro."}
          </p>
        </Row>

        {settings.strategy === "rules" && (
          <PromptRulesInput value={settings.rulesPrompt} onChange={(v) => set("rulesPrompt", v)} aiAvailable={ai} />
        )}
        {settings.strategy === "preset" && (
          <Row label="Preset" hint={<a onClick={onEditCategories}>edit presets…</a>}>
            <SetPicker sets={presets} value={settings.presetId} onPick={(id) => set("presetId", id)} />
          </Row>
        )}

        {settings.strategy === "custom" && (
          <Row label="My category set" hint={<a onClick={onEditCategories}>new / edit…</a>}>
            {customSets.length ? (
              <SetPicker sets={customSets} value={settings.customSetId} onPick={(id) => set("customSetId", id)} />
            ) : (
              <Button onClick={onEditCategories} icon={<PencilLine size={14} />}>
                Create your first set…
              </Button>
            )}
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

        {settings.strategy === "places" && (
          <Row label="Folders per">
            <Segmented
              value={settings.placeGranularity}
              onChange={(v) => set("placeGranularity", v as UiSettings["placeGranularity"])}
              options={[
                { value: "country", label: "Country" },
                { value: "city", label: "City" },
              ]}
            />
          </Row>
        )}
        {settings.strategy === "people" && <FacePicker value={settings.peopleReference} onChange={onFace} />}
        {settings.strategy === "people" && !settings.peopleReference && (
          <>
            <Row label="A person needs at least" hint={`${settings.peopleMinPhotos} photos, otherwise “Other people”`} inline>
              <InputNumber min={1} max={50} value={settings.peopleMinPhotos} onChange={(v) => set("peopleMinPhotos", v ?? 3)} />
            </Row>
            <Row label="Photos with several people">
              <Radio.Group
                value={settings.peopleMulti}
                onChange={(e) => set("peopleMulti", e.target.value)}
                optionType="button"
                options={[
                  { value: "main", label: "Main face only (default)" },
                  { value: "copy", label: "A copy for every person" },
                ]}
              />
            </Row>
            <Row label="Same-person strictness" hint={settings.peopleSimilarity > 0.42 ? "strict: may split one person" : settings.peopleSimilarity < 0.3 ? "loose: may merge look-alikes" : "balanced"}>
              <Slider min={0.25} max={0.55} step={0.01} value={settings.peopleSimilarity} onChange={(v) => set("peopleSimilarity", v)} />
            </Row>
            {!health?.people_available && <p className="py-2 text-[11px] text-red-500">Face recognition models are missing in this build.</p>}
          </>
        )}
        <Row label="Recognition model" hint={settings.model === "siglip2" ? "more accurate · ~5× slower first run" : "fast"}>
          <Segmented
            value={settings.model}
            onChange={(v) => set("model", v as UiSettings["model"])}
            options={[
              { value: "clip", label: "CLIP · fast" },
              { value: "siglip2", label: "SigLIP 2 · accurate" },
            ]}
          />
        </Row>
        {(settings.strategy === "preset" || settings.strategy === "custom") && (
          <Row label="Read text in photos (OCR)" hint="text-heavy photos go to documents / captions folders; text becomes searchable" inline>
            <Switch checked={settings.ocr} disabled={health?.ocr_available === false} onChange={(v) => set("ocr", v)} />
          </Row>
        )}
        {(settings.strategy === "preset" || settings.strategy === "custom") && (
          <Row label="Confidence threshold" hint={`below ${Math.round(settings.minConfidence * 100)}%, files go to Unsorted`}>
            <Slider min={0.05} max={0.9} step={0.05} value={settings.minConfidence} onChange={(v) => set("minConfidence", v)} />
          </Row>
        )}
      </Section>

      <Section id="pro" page={page}>
        <p className="pb-1 text-[11px] text-plum/55">
          Every check is optional. Turn one on and its controls appear below it.
          {settings.strategy === "cull" ? " Cull always sorts into Keepers, Rejects and Maybe." : ""}
        </p>
        <Check label="🌫️ Blurry / out of focus" on={Q.blur} set={(v) => setQ({ blur: v })}>
          <Row label="Sharpness needed" hint={`${Math.round(Q.blur_threshold * 100)}%: higher is stricter`}>
            <Slider min={0.2} max={0.85} step={0.01} value={Q.blur_threshold} onChange={(v) => setQ({ blur_threshold: v })} />
          </Row>
        </Check>
        <Check label="😑 Eyes closed" on={Q.eyes_closed} disabled={!faces} set={(v) => setQ({ eyes_closed: v })}>
          <Row label="Eyes-closed sensitivity" hint={`blink ≥ ${Math.round(Q.blink_threshold * 100)}%`}>
            <Slider min={0.2} max={0.9} step={0.05} value={Q.blink_threshold} onChange={(v) => setQ({ blink_threshold: v })} />
          </Row>
        </Check>
        <Check label={`😄 Smiles (${settings.strategy === "cull" ? "own folder" : "tag"})`} on={Q.smiles} disabled={!faces} set={(v) => setQ({ smiles: v })}>
          <Row label="Smile needed" hint={`≥ ${Math.round(Q.smile_threshold * 100)}%`}>
            <Slider min={0.2} max={0.9} step={0.05} value={Q.smile_threshold} onChange={(v) => setQ({ smile_threshold: v })} />
          </Row>
        </Check>
        {(Q.eyes_closed || Q.smiles) && (
          <Row label="Whose eyes & smile count">
            <Radio.Group
              value={Q.faces_rule}
              onChange={(e) => setQ({ faces_rule: e.target.value })}
              optionType="button"
              options={[
                { value: "any", label: "Any face (group shots)" },
                { value: "main", label: "Main subject only" },
              ]}
            />
          </Row>
        )}
        <Check label="🌑 Too dark / too bright" on={Q.exposure} set={(v) => setQ({ exposure: v })}>
          <Row label="Exposure limits" hint={`dark < ${Math.round(Q.dark_threshold * 100)}% · bright > ${Math.round(Q.bright_threshold * 100)}%`}>
            <Slider
              range
              min={0}
              max={1}
              step={0.01}
              value={[Q.dark_threshold, Q.bright_threshold]}
              onChange={(v) => setQ({ dark_threshold: Math.min(0.5, v[0]), bright_threshold: Math.max(0.5, v[1]) })}
            />
          </Row>
        </Check>
        <Check label="🌪️ Noisy (high ISO)" on={Q.noise_check} set={(v) => setQ({ noise_check: v })}>
          <Row label="Noise limit" hint={`grain σ > ${(Q.noise_threshold * 100).toFixed(1)}%`}>
            <Slider min={0.01} max={0.12} step={0.005} value={Q.noise_threshold} onChange={(v) => setQ({ noise_threshold: v })} />
          </Row>
        </Check>
        <Check label="✂️ Face cut off by the frame" on={Q.face_crop} disabled={!faces} set={(v) => setQ({ face_crop: v })} />
        <Check label="📐 Tilted horizon (beta)" on={Q.tilt_check} set={(v) => setQ({ tilt_check: v })}>
          <Row label="Tilt tolerance" hint={`flag from ${Q.tilt_tolerance}°`}>
            <Slider min={0.5} max={6} step={0.5} value={Q.tilt_tolerance} onChange={(v) => setQ({ tilt_tolerance: v })} />
          </Row>
        </Check>
        <Check label="🎞️ Best of burst" hint="keep the best of near-identical frames" on={Q.bursts} set={(v) => setQ({ bursts: v })}>
          <Row label="Also group similar shots taken at any time" hint="best of similar, same folder" inline>
            <Switch size="small" checked={Q.similar_any_time} onChange={(v) => setQ({ similar_any_time: v })} />
          </Row>
          {!Q.similar_any_time && (
            <div className="grid gap-x-6 sm:grid-cols-2">
              <Row label="Burst window" hint={`${Q.burst_seconds}s`}>
                <Slider min={0.5} max={10} step={0.5} value={Q.burst_seconds} onChange={(v) => setQ({ burst_seconds: v })} />
              </Row>
              <Row label="Burst similarity" hint={`${Math.round(Q.burst_similarity * 100)}%`}>
                <Slider min={0.8} max={0.98} step={0.01} value={Q.burst_similarity} onChange={(v) => setQ({ burst_similarity: v })} />
              </Row>
            </div>
          )}
        </Check>
        {settings.strategy === "cull" && (
          <>
            <Row label="Recommendation profile" hint="adapts keeper ratings and top picks to the kind of photography">
              <Select aria-label="Recommendation profile" className="w-full" value={Q.pick_profile ?? "auto"}
                onChange={(v) => setQ({ pick_profile: v })}
                options={[
                  { value: "auto", label: "Auto · detect per photo" },
                  { value: "portrait", label: "Portrait · eyes, expression, light" },
                  { value: "fashion", label: "Fashion / modeling · pose, styling, light" },
                  { value: "landscape", label: "Landscape · detail, depth, light" },
                  { value: "general", label: "General · detail, composition, story" },
                ]} />
              <p className="mt-2 text-[11px] leading-relaxed text-plum/55">
                Scores combine technical quality, expression, composition and local AI presentation signals.
                Picks favor variety and skip near-duplicates. Review the reasons in the photo viewer.
              </p>
            </Row>
            <Row label="Picks from" hint="/ 5 · strongest unique photos; similar frames go to Similar alternatives">
              <InputNumber aria-label="Picks from" min={1} max={5} step={0.1} precision={1} value={Q.pick_min_rating}
                onChange={(v) => v !== null && setQ({ pick_min_rating: v, keeper_min_rating: Math.min(Q.keeper_min_rating, v), keeper_min_stars: 0 })} />
            </Row>
            <Row label="Keepers from" hint={`/ 5 · up to ${Q.pick_min_rating.toFixed(1)}, then Picks; lower ratings go to Maybe`}>
              <InputNumber aria-label="Keepers from" min={1} max={5} step={0.1} precision={1} value={Q.keeper_min_rating}
                onChange={(v) => v !== null && setQ({ keeper_min_rating: v, pick_min_rating: Math.max(Q.pick_min_rating, v), keeper_min_stars: 0 })} />
            </Row>
          </>
        )}
        <Check label="🏷️ Write ratings to XMP on Apply" hint="★ + color labels for Lightroom / Capture One" on={Q.write_xmp} set={(v) => setQ({ write_xmp: v })} />
        {settings.strategy !== "cull" && anyCheck && (
          <Row label="Bad shots">
            <Radio.Group
              value={Q.action}
              onChange={(e) => setQ({ action: e.target.value })}
              optionType="button"
              options={[
                { value: "reject", label: "Move to _Rejects/<reason>" },
                { value: "tag", label: "Only tag them" },
              ]}
            />
          </Row>
        )}
        {!faces && <p className="py-2 text-[11px] text-plum/50">Face model not found: eyes, smile and face-crop checks are unavailable.</p>}
      </Section>

      <Section id="files" page={page}>
        <Row label="Duplicates: extra copies go…">
          <Radio.Group
            value={settings.duplicatesAction}
            onChange={(e) => set("duplicatesAction", e.target.value)}
            className="!grid gap-1.5 sm:grid-cols-2"
            options={[
              { value: "folder", label: "🗂️ Set aside in _Duplicates/" },
              { value: "with_original", label: "📎 Next to the original" },
              { value: "keep", label: "📍 Leave them where they are" },
              { value: "delete", label: "🗑️ Delete (recoverable trash)" },
            ]}
          />
          {settings.duplicatesAction === "delete" && (
            <p className="mt-2 text-[11px] text-plum/55">
              Copies move to a hidden <code>.aio-trash/</code> folder. Undo brings them back; <b>History → Empty trash</b> deletes them for good.
            </p>
          )}
        </Row>
        <Row label="Which copy is the original">
          <Segmented
            value={settings.duplicateKeep}
            onChange={(v) => set("duplicateKeep", v as UiSettings["duplicateKeep"])}
            options={[
              { value: "best", label: "Best quality" },
              { value: "oldest", label: "Oldest" },
              { value: "newest", label: "Newest" },
            ]}
          />
        </Row>
        <Row label="Detect near-duplicates" hint="resized / re-saved copies, not just identical files" inline>
          <Switch checked={settings.nearDuplicates} onChange={(v) => set("nearDuplicates", v)} />
        </Row>
        {settings.nearDuplicates && (
          <Row label="Near-duplicate strictness" hint={settings.nearDupDistance <= 2 ? "only almost identical" : settings.nearDupDistance >= 8 ? "loose: also small edits" : "balanced"}>
            <Slider min={0} max={12} step={1} value={settings.nearDupDistance} onChange={(v) => set("nearDupDistance", v)} />
          </Row>
        )}
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
        <Row label="AI assist" hint="let AI help place photos (preset & custom strategies)" inline>
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
        <Row label="Use AI for" hint="preset & custom strategies, when AI assist is on">
          <Radio.Group
            disabled={!ai}
            value={settings.ai.assist_scope}
            onChange={(e) => setAI({ assist_scope: e.target.value })}
            optionType="button"
            options={[
              { value: "unsure", label: "Unsure photos only (cheap)" },
              { value: "all", label: "Every photo (most accurate)" },
            ]}
          />
          <p className="mt-1.5 text-[11px] text-plum/50">
            {settings.ai.assist_scope === "all"
              ? `About ${Math.ceil(settings.aiMaxFiles / settings.ai.assist_batch)} requests per ${settings.aiMaxFiles} photos (${settings.ai.assist_batch} thumbnails each, low detail).`
              : "Only photos CLIP is not sure about are sent."}
          </p>
        </Row>
        <div className="grid gap-x-6 sm:grid-cols-2">
          <Row label="Max photos sent to AI" inline>
            <InputNumber disabled={!ai} min={10} max={5000} step={50} value={settings.aiMaxFiles} onChange={(v) => set("aiMaxFiles", v ?? 300)} />
          </Row>
          <Row label="Photos per request" inline>
            <InputNumber disabled={!ai} min={1} max={24} value={settings.ai.assist_batch} onChange={(v) => setAI({ assist_batch: v ?? 12 })} />
          </Row>
        </div>
        <PromptEditor
          label="Folder-naming prompt (Auto)"
          disabled={!ai}
          value={settings.ai.naming_prompt}
          fallback={defaults?.naming_prompt ?? ""}
          placeholders={defaults?.naming_placeholders ?? []}
          format={defaults?.naming_format}
          onChange={(v) => setAI({ naming_prompt: v })}
        />
        <PromptEditor
          label="Assist prompt (Preset & My categories)"
          disabled={!ai}
          value={settings.ai.assist_prompt}
          fallback={defaults?.assist_prompt ?? ""}
          placeholders={defaults?.assist_placeholders ?? []}
          format={defaults?.assist_format}
          onChange={(v) => setAI({ assist_prompt: v })}
          note="Each folder is listed with its own AI hint (Category editor), or its descriptions when it has none."
        />
        <p className="py-2 text-[11px] text-plum/50">
          Auto mode names its groups with a single request. Images are sent at low detail, and reasoning effort is low. Nothing is sent
          without a key. Private content? Keep AI assist off: CLIP runs fully offline.
        </p>
      </Section>

      <Section id="appearance" page={page}>
        <Row label="Language" inline>
          <LangSelect />
        </Row>
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
        <Row label="Recognition device" inline>
          <Tag>{health?.device === "gpu" ? "NVIDIA GPU · CUDA" : "CPU (default)"}</Tag>
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
        <DangerZone />
      </Section>
    </>
  );

  if (!page) return <OnlyCtx.Provider value={only ?? null}>{body}</OnlyCtx.Provider>;

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
                <Icon size={14} /> {t(s.key)}
              </button>
            );
          })}
          <p className="px-2.5 pt-3 text-[11px] text-plum/45">{t("st.saved")}</p>
        </div>
      </nav>
      <div className="min-w-0 space-y-5">{body}</div>
    </div>
  );
}

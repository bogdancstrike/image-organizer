import { ExplainedTag as Tag } from "./PhotoBadge";
import { useEffect, useMemo, useState } from "react";
import { App, Button, Input, Modal, Popconfirm, Segmented, Select } from "antd";
import { ArrowDown, ArrowUp, Plus, RotateCcw, Sparkles, Trash2 } from "lucide-react";
import { api, type Category, type CategorySet } from "@/api";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";

interface Props {
  open: boolean;
  onClose: () => void;
  presets: CategorySet[];
  customSets: CategorySet[];
  onSaved: (set: CategorySet | null) => void;
  /** what to open: a set to edit (presets included), a set to copy, or a blank new set */
  initial?: { set: CategorySet | null; mode: "edit" | "copy" | "new" } | null;
}

type Media = "any" | "image" | "video";
interface Folder {
  key: string;
  name: string;
  emoji: string;
  prompts: string[];
  media: Media;
  ai_hint: string;
}
interface Draft {
  name: string;
  description: string;
  folders: Folder[];
}

const BAD = /[/\\:*?"<>|]/;
let seq = 0;
const newKey = () => `f${++seq}`;
const toFolder = (c: Category): Folder => ({
  key: newKey(),
  name: c.name,
  emoji: c.emoji ?? "📁",
  prompts: c.prompts ?? [],
  media: c.media ?? "any",
  ai_hint: c.ai_hint ?? "",
});
const blankFolder = (): Folder => ({ key: newKey(), name: "", emoji: "📁", prompts: [], media: "any", ai_hint: "" });

function problems(d: Draft): Record<string, string> {
  const out: Record<string, string> = {};
  const seen = new Map<string, string>();
  for (const f of d.folders) {
    const n = f.name.trim();
    if (!n) out[f.key] = "Give this folder a name";
    else if (BAD.test(n)) out[f.key] = 'Names can’t contain / \\ : * ? " < > |';
    else if (seen.has(n.toLowerCase())) out[f.key] = `Another folder is already called “${n}”`;
    seen.set(n.toLowerCase(), f.key);
  }
  return out;
}

/** Create / edit category sets (built-in presets included) in a calm master-detail layout. */
export function CategoryEditor({ open, onClose, presets, customSets, onSaved, initial }: Props) {
  const { message } = App.useApp();
  const { t } = useI18n();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>({ name: "My folders", description: "", folders: [blankFolder()] });
  const [sel, setSel] = useState(0);
  const [saving, setSaving] = useState(false);

  const load = (s: CategorySet | null, asCopy = false) => {
    setEditingId(s && !asCopy ? s.id : null);
    setDraft(
      s
        ? { name: asCopy ? `${s.name} (mine)` : s.name, description: s.description ?? "", folders: s.categories.map(toFolder) }
        : { name: "My folders", description: "", folders: [blankFolder()] },
    );
    setSel(0);
  };

  useEffect(() => {
    if (!open) return;
    if (initial) load(initial.mode === "new" ? null : initial.set, initial.mode === "copy");
    else load(customSets[0] ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const preset = useMemo(() => presets.find((p) => p.id === editingId), [presets, editingId]);
  const errs = useMemo(() => problems(draft), [draft]);
  const cur = draft.folders[sel];

  const patch = (p: Partial<Folder>) =>
    setDraft((d) => ({ ...d, folders: d.folders.map((f, i) => (i === sel ? { ...f, ...p } : f)) }));
  const move = (dir: -1 | 1) =>
    setDraft((d) => {
      const fs = [...d.folders];
      const j = sel + dir;
      if (j < 0 || j >= fs.length) return d;
      [fs[sel], fs[j]] = [fs[j], fs[sel]];
      setSel(j);
      return { ...d, folders: fs };
    });
  const add = () => {
    setDraft((d) => ({ ...d, folders: [...d.folders, blankFolder()] }));
    setSel(draft.folders.length);
  };
  const remove = () => {
    if (draft.folders.length <= 1) return;
    setDraft((d) => ({ ...d, folders: d.folders.filter((_, i) => i !== sel) }));
    setSel((i) => Math.max(0, i - 1));
  };

  const save = async () => {
    const firstBad = draft.folders.findIndex((f) => errs[f.key]);
    if (!draft.name.trim()) return message.error("Give the set a name");
    if (firstBad >= 0) {
      setSel(firstBad);
      return message.error(errs[draft.folders[firstBad].key]);
    }
    setSaving(true);
    try {
      const saved = await api.saveSet(editingId, {
        name: draft.name.trim(),
        description: draft.description.trim() || undefined,
        categories: draft.folders.map((f) => ({
          id: "",
          name: f.name.trim(),
          emoji: f.emoji || undefined,
          prompts: f.prompts,
          media: f.media,
          ai_hint: f.ai_hint.trim() || null,
        })),
      });
      message.success(`Saved “${saved.name}”`);
      setEditingId(saved.id);
      onSaved(saved);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const discard = async () => {
    if (!editingId) return;
    await api.deleteSet(editingId);
    message.success(preset ? `“${preset.name}” reset to default` : "Deleted");
    onSaved(null);
    if (preset) onClose();
    else load(null);
  };

  const switcher = [
    { label: "My sets", options: customSets.map((s) => ({ value: `c:${s.id}`, label: s.name })) },
    { label: "Presets", options: presets.map((p) => ({ value: `p:${p.id}`, label: p.name + (p.modified ? " · edited" : "") })) },
  ];
  const switchTo = (v: string) => {
    if (v === "new") return load(null);
    const [kind, id] = [v.slice(0, 1), v.slice(2)];
    load((kind === "c" ? customSets : presets).find((s) => s.id === id) ?? null);
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      centered
      width="min(980px, 96vw)"
      closable
      title={
        <div className="flex flex-wrap items-center gap-2 pr-8">
          <Select
            variant="borderless"
            className="min-w-48 !text-[15px] font-semibold"
            popupMatchSelectWidth={260}
            value={editingId ? `${preset ? "p" : "c"}:${editingId}` : "new"}
            onChange={switchTo}
            options={[{ value: "new", label: "＋ New set" }, ...switcher]}
          />
          {preset && <Tag className="m-0 rounded-full">built-in{preset.modified ? " · edited" : ""}</Tag>}
        </div>
      }
      styles={{ body: { padding: 0 } }}
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            {editingId && (!preset || preset.modified) && (
              <Popconfirm
                title={preset ? "Restore the built-in folders?" : "Delete this set?"}
                okButtonProps={{ danger: !preset }}
                onConfirm={discard}
              >
                <Button type="text" danger={!preset} icon={preset ? <RotateCcw size={14} /> : <Trash2 size={14} />}>
                  {preset ? "Reset to default" : "Delete set"}
                </Button>
              </Popconfirm>
            )}
          </div>
          <div className="flex gap-2">
            <Button onClick={onClose}>{t("ed.cancel")}</Button>
            <Button type="primary" loading={saving} onClick={save}>
              {t("ed.save")}
            </Button>
          </div>
        </div>
      }
    >
      <div className="grid overflow-hidden border-y border-line md:h-[min(70vh,640px)] md:grid-cols-[280px_minmax(0,1fr)] md:grid-rows-1">
        {/* ── master: set info + folder list ───────────────────────── */}
        <aside className="flex max-h-[45vh] min-h-0 flex-col border-b border-line md:h-full md:max-h-none md:border-b-0 md:border-r">
          <div className="px-4 pb-2 pt-4">
            <Input
              variant="borderless"
              className="!px-0 !text-[18px] !font-semibold"
              value={draft.name}
              maxLength={60}
              placeholder="Set name"
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
            />
            <Input
              variant="borderless"
              className="!px-0 !text-[12px] !text-plum/60"
              value={draft.description}
              maxLength={200}
              placeholder="Add a short description"
              onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
            />
          </div>
          <div className="px-4 pb-1 pt-2 label-caps">{draft.folders.length} folders</div>
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
            {draft.folders.map((f, i) => (
              <button
                key={f.key}
                onClick={() => setSel(i)}
                className={cn(
                  "flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors",
                  i === sel ? "bg-plum text-on-ink" : "text-plum hover:bg-tint",
                )}
              >
                <span className="w-5 text-center text-[15px]">{f.emoji || "📁"}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium">{f.name || <em className="opacity-50">Untitled</em>}</span>
                  <span className={cn("block truncate text-[11px]", i === sel ? "opacity-70" : "text-plum/45")}>
                    {f.media === "video" ? "Videos · " : f.media === "image" ? "Photos · " : ""}
                    {f.prompts.length ? `${f.prompts.length} description${f.prompts.length > 1 ? "s" : ""}` : "no description"}
                    {f.ai_hint ? " · AI hint" : ""}
                  </span>
                </span>
                {errs[f.key] && <span className="h-2 w-2 shrink-0 rounded-full bg-red-500" title={errs[f.key]} />}
              </button>
            ))}
          </div>
          <div className="border-t border-line p-2">
            <Button type="text" block icon={<Plus size={14} />} onClick={add} className="!justify-start">
              {t("ed.add")}
            </Button>
          </div>
        </aside>

        {/* ── detail: the selected folder ─────────────────────────── */}
        {cur && (
          <section className="min-h-0 overflow-y-auto px-6 py-5 md:h-full">
            <div className="flex items-center gap-3">
              <Input
                className="!h-14 !w-14 !rounded-2xl !text-center !text-[26px]"
                value={cur.emoji}
                maxLength={4}
                onChange={(e) => patch({ emoji: e.target.value })}
                aria-label="Icon"
              />
              <div className="min-w-0 flex-1">
                <Input
                  variant="borderless"
                  className="!px-0 !text-[22px] !font-semibold"
                  value={cur.name}
                  maxLength={40}
                  placeholder="Folder name"
                  status={errs[cur.key] ? "error" : undefined}
                  onChange={(e) => patch({ name: e.target.value })}
                />
                <div className={cn("text-[11px]", errs[cur.key] ? "text-red-500" : "text-plum/45")}>
                  {errs[cur.key] ?? "This becomes the folder name on disk."}
                </div>
              </div>
            </div>

            <Field label={t("ed.accepts")}>
              <Segmented
                value={cur.media}
                onChange={(v) => patch({ media: v as Media })}
                options={[
                  { value: "any", label: t("ed.any") },
                  { value: "image", label: "Photos" },
                  { value: "video", label: "Videos" },
                ]}
              />
              <p className="mt-1.5 text-[11px] text-plum/45">If any folder takes only videos, every video goes to those folders.</p>
            </Field>

            <Field label={t("ed.look")}>
              <Select
                mode="tags"
                className="w-full"
                placeholder="e.g. people dancing at a party · disco lights   (Enter after each)"
                tokenSeparators={[","]}
                maxCount={8}
                open={false}
                suffixIcon={null}
                value={cur.prompts}
                onChange={(v) => patch({ prompts: v })}
              />
              <p className="mt-1.5 text-[11px] text-plum/45">
                Short visual descriptions improve matching. Without any, the folder name is used.
              </p>
            </Field>

            <Field
              label={
                <span className="inline-flex items-center gap-1.5">
                  <Sparkles size={13} /> {t("ed.hint")} <span className="font-normal text-plum/45">(optional)</span>
                </span>
              }
            >
              <Input.TextArea
                autoSize={{ minRows: 2, maxRows: 5 }}
                maxLength={300}
                value={cur.ai_hint}
                onChange={(e) => patch({ ai_hint: e.target.value })}
                placeholder="Only for AI assist, e.g. “only if a motorcycle is clearly visible”. Empty: the descriptions are used."
              />
            </Field>

            <div className="mt-6 flex items-center gap-1 border-t border-line pt-3">
              <Button type="text" size="small" icon={<ArrowUp size={14} />} disabled={sel === 0} onClick={() => move(-1)}>
                Up
              </Button>
              <Button type="text" size="small" icon={<ArrowDown size={14} />} disabled={sel === draft.folders.length - 1} onClick={() => move(1)}>
                Down
              </Button>
              <Button
                type="text"
                size="small"
                danger
                className="!ml-auto"
                icon={<Trash2 size={14} />}
                disabled={draft.folders.length <= 1}
                onClick={remove}
              >
                {t("ed.remove")}
              </Button>
            </div>
          </section>
        )}
      </div>
    </Modal>
  );
}

function Field({ label, children }: { label: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="mt-6">
      <div className="mb-2 text-[13px] font-medium text-plum">{label}</div>
      {children}
    </div>
  );
}

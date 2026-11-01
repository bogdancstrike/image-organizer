import { useEffect, useMemo, useState } from "react";
import { App, Button, Empty, Form, Input, Modal, Popconfirm, Segmented, Select, Tag } from "antd";
import { ArrowDown, ArrowUp, Copy, Plus, RotateCcw, Trash2 } from "lucide-react";
import { api, type CategorySet } from "@/api";
import { cn } from "@/lib/utils";

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
type FormValues = {
  name: string;
  description?: string;
  categories: { name: string; emoji?: string; prompts?: string[]; media?: Media }[];
};

const BLANK: FormValues = { name: "My folders", categories: [{ name: "", emoji: "📁", prompts: [], media: "any" }] };

/** Create / edit / delete category sets, built-in presets included (REQ-UI-4, REQ-CAT-2). */
export function CategoryEditor({ open, onClose, presets, customSets, onSaved, initial }: Props) {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const count = Form.useWatch("categories", form)?.length ?? 0;

  const load = (s: CategorySet | null, asCopy = false) => {
    setEditingId(s && !asCopy ? s.id : null);
    form.resetFields();
    form.setFieldsValue(
      s
        ? {
            name: asCopy ? `${s.name} (mine)` : s.name,
            description: s.description ?? undefined,
            categories: s.categories.map((c) => ({ name: c.name, emoji: c.emoji, prompts: c.prompts ?? [], media: c.media ?? "any" })),
          }
        : BLANK,
    );
  };

  useEffect(() => {
    if (!open) return;
    if (initial) load(initial.mode === "new" ? null : initial.set, initial.mode === "copy");
    else load(customSets[0] ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const editingPreset = useMemo(() => presets.find((p) => p.id === editingId), [presets, editingId]);

  const save = async () => {
    let values: FormValues;
    try {
      values = await form.validateFields();
    } catch {
      message.error("Fix the highlighted fields first");
      return;
    }
    setSaving(true);
    try {
      const saved = await api.saveSet(editingId, {
        name: values.name,
        description: values.description,
        categories: values.categories.map((c) => ({
          id: "",
          name: c.name.trim(),
          emoji: c.emoji || undefined,
          prompts: c.prompts ?? [],
          media: c.media ?? "any",
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

  const remove = async () => {
    if (!editingId) return;
    await api.deleteSet(editingId);
    if (editingPreset) {
      message.success(`“${editingPreset.name}” reset to default`);
      onSaved(null);
      onClose();
      return;
    }
    message.success("Deleted");
    onSaved(null);
    load(null);
  };

  const setOptions = [
    ...customSets.map((s) => ({ value: `c:${s.id}`, label: `${s.name} · ${s.categories.length}` })),
    ...presets.map((p) => ({ value: `p:${p.id}`, label: `${p.name} (preset)${p.modified ? " · edited" : ""}` })),
  ];
  const pick = (v: string) => {
    const [kind, id] = [v.slice(0, 1), v.slice(2)];
    load((kind === "c" ? customSets : presets).find((s) => s.id === id) ?? null);
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      centered
      width="min(1080px, 96vw)"
      title={
        <div className="flex flex-wrap items-center gap-2 pr-6">
          <span>{editingPreset ? "Edit preset" : editingId ? "Edit category set" : "New category set"}</span>
          {editingPreset && (
            <Tag color="gold" className="m-0">
              built-in{editingPreset.modified ? " · edited" : ""}
            </Tag>
          )}
          <span className="text-xs font-normal text-plum/50">{count} folders</span>
        </div>
      }
      styles={{ body: { maxHeight: "72vh", overflowY: "auto", overflowX: "hidden", paddingRight: 4 } }}
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            {editingPreset ? (
              editingPreset.modified ? (
                <Popconfirm title="Discard your edits and restore the built-in folders?" onConfirm={remove}>
                  <Button type="text" icon={<RotateCcw size={14} />}>
                    Reset to default
                  </Button>
                </Popconfirm>
              ) : (
                <span className="text-xs text-plum/50">Built-in preset. Your edits can be reset anytime.</span>
              )
            ) : editingId ? (
              <Popconfirm title="Delete this set?" onConfirm={remove}>
                <Button danger type="text" icon={<Trash2 size={14} />}>
                  Delete set
                </Button>
              </Popconfirm>
            ) : null}
          </div>
          <div className="flex gap-2">
            <Button onClick={onClose}>Close</Button>
            <Button type="primary" loading={saving} onClick={save}>
              Save
            </Button>
          </div>
        </div>
      }
    >
      <div className="grid gap-6 md:grid-cols-[210px_minmax(0,1fr)]">
        {/* sets: sidebar on desktop, dropdown on mobile */}
        <aside className="hidden space-y-1 md:block">
          <Button block icon={<Plus size={14} />} onClick={() => load(null)}>
            New set
          </Button>
          <div className="pt-3 label-caps">My sets</div>
          {customSets.length === 0 && <Empty className="!my-2" image={Empty.PRESENTED_IMAGE_SIMPLE} description="None yet" />}
          {customSets.map((s) => (
            <button
              key={s.id}
              onClick={() => load(s)}
              className={cn(
                "block w-full cursor-pointer truncate rounded-lg px-2.5 py-1.5 text-left text-[13px] text-plum hover:bg-tint",
                editingId === s.id && "bg-tint font-medium",
              )}
            >
              {s.name} <span className="text-plum/40">· {s.categories.length}</span>
            </button>
          ))}
          <div className="pt-3 label-caps">Presets</div>
          <div className="max-h-72 overflow-y-auto pr-1">
            {presets.map((p) => (
              <div key={p.id} className={cn("group flex items-center rounded-lg hover:bg-tint", editingId === p.id && "bg-tint")}>
                <button
                  onClick={() => load(p)}
                  className={cn(
                    "min-w-0 flex-1 cursor-pointer truncate px-2.5 py-1.5 text-left text-[13px] text-plum/80",
                    editingId === p.id && "font-medium text-plum",
                  )}
                  title="Edit this preset"
                >
                  {p.name}
                  {p.modified && <span className="ml-1 text-[10px] text-amber-500">●</span>}
                </button>
                <button
                  onClick={() => load(p, true)}
                  className="cursor-pointer px-2 text-plum/40 opacity-0 transition-opacity hover:text-plum group-hover:opacity-100 focus:opacity-100"
                  title="Copy into a new set"
                  aria-label={`Copy ${p.name}`}
                >
                  <Copy size={13} />
                </button>
              </div>
            ))}
          </div>
        </aside>
        <div className="flex gap-2 md:hidden">
          <Select className="flex-1" placeholder="Open a set or preset…" options={setOptions} onChange={pick} value={null} />
          <Button icon={<Plus size={14} />} onClick={() => load(null)} aria-label="New set" />
        </div>

        <Form form={form} layout="vertical" requiredMark={false} initialValues={BLANK} className="min-w-0">
          <div className="grid gap-x-4 sm:grid-cols-2">
            <Form.Item name="name" label="Set name" rules={[{ required: true, whitespace: true, max: 60 }]}>
              <Input placeholder="e.g. Wedding, My Instagram" />
            </Form.Item>
            <Form.Item name="description" label="Description">
              <Input placeholder="optional" maxLength={200} />
            </Form.Item>
          </div>
          <p className="-mt-2 mb-3 text-xs text-plum/55">
            Each folder needs a <b>name</b>. Add a few <b>descriptions</b> of what its photos look like (press Enter after each)
            to improve accuracy. If some folders accept only <b>Videos</b>, every video goes only to those.
          </p>

          <Form.List
            name="categories"
            rules={[
              {
                validator: async (_, cats: FormValues["categories"]) => {
                  if (!cats || cats.length < 1) throw new Error("Add at least one folder");
                  if (cats.length > 40) throw new Error("At most 40 folders");
                  const names = cats.map((c) => (c?.name || "").trim().toLowerCase()).filter(Boolean);
                  const dup = names.find((n, i) => names.indexOf(n) !== i);
                  if (dup) throw new Error(`Two folders are called “${dup}”`);
                },
              },
            ]}
          >
            {(fields, { add, remove, move }, { errors }) => (
              <div className="space-y-2.5">
                {fields.map((f, idx) => (
                  <div key={f.key} className="rounded-xl border border-line bg-surface/70 p-3">
                    <div className="flex flex-wrap items-start gap-2">
                      <Form.Item name={[f.name, "emoji"]} className="!mb-0 w-14 shrink-0">
                        <Input className="text-center" maxLength={4} aria-label="Icon" />
                      </Form.Item>
                      <Form.Item
                        name={[f.name, "name"]}
                        className="!mb-0 min-w-44 flex-1"
                        rules={[
                          { required: true, whitespace: true, message: "Name required" },
                          { pattern: /^[^/\\:*?"<>|]+$/, message: 'Not allowed: / \\ : * ? " < > |' },
                          { max: 40 },
                        ]}
                      >
                        <Input placeholder="Folder name, e.g. Dance floor" aria-label="Folder name" />
                      </Form.Item>
                      <Form.Item name={[f.name, "media"]} className="!mb-0" initialValue="any">
                        <Segmented
                          options={[
                            { value: "any", label: "Any" },
                            { value: "image", label: "Photos" },
                            { value: "video", label: "Videos" },
                          ]}
                        />
                      </Form.Item>
                      <div className="ml-auto flex">
                        <Button type="text" disabled={idx === 0} icon={<ArrowUp size={14} />} onClick={() => move(idx, idx - 1)} aria-label="Move up" />
                        <Button
                          type="text"
                          disabled={idx === fields.length - 1}
                          icon={<ArrowDown size={14} />}
                          onClick={() => move(idx, idx + 1)}
                          aria-label="Move down"
                        />
                        <Button type="text" danger icon={<Trash2 size={14} />} onClick={() => remove(f.name)} aria-label="Remove folder" />
                      </div>
                    </div>
                    <Form.Item name={[f.name, "prompts"]} className="!mb-0 !mt-2">
                      <Select
                        mode="tags"
                        className="w-full"
                        placeholder="Describe it: “people dancing at a party”, “disco lights”… (Enter after each)"
                        tokenSeparators={[","]}
                        maxCount={8}
                        open={false}
                        suffixIcon={null}
                        aria-label="Descriptions"
                      />
                    </Form.Item>
                  </div>
                ))}
                <Button type="dashed" block icon={<Plus size={14} />} onClick={() => add({ name: "", emoji: "📁", prompts: [], media: "any" })}>
                  Add folder
                </Button>
                <Form.ErrorList errors={errors} />
              </div>
            )}
          </Form.List>
        </Form>
      </div>
    </Modal>
  );
}

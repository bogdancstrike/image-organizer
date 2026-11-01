import { useEffect, useState } from "react";
import { App, Button, Empty, Form, Input, Modal, Popconfirm, Select } from "antd";
import { Plus, Trash2, Copy } from "lucide-react";
import { api, type CategorySet } from "@/api";
import { cn } from "@/lib/utils";

interface Props {
  open: boolean;
  onClose: () => void;
  presets: CategorySet[];
  customSets: CategorySet[];
  onSaved: (set: CategorySet | null) => void;
}

type FormValues = {
  name: string;
  description?: string;
  categories: { name: string; emoji?: string; prompts?: string[] }[];
};

const BLANK: FormValues = { name: "My folders", categories: [{ name: "", emoji: "📁", prompts: [] }] };

/** Create / edit / delete custom category sets (REQ-UI-4, REQ-CAT-2). */
export function CategoryEditor({ open, onClose, presets, customSets, onSaved }: Props) {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = (s: CategorySet | null, asCopy = false) => {
    setEditingId(s && !asCopy ? s.id : null);
    form.setFieldsValue(
      s
        ? {
            name: asCopy ? `${s.name} (mine)` : s.name,
            description: s.description ?? undefined,
            categories: s.categories.map((c) => ({ name: c.name, emoji: c.emoji, prompts: c.prompts ?? [] })),
          }
        : BLANK,
    );
  };

  useEffect(() => {
    if (open) load(customSets[0] ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const saved = await api.saveSet(editingId, {
        name: values.name,
        description: values.description,
        categories: values.categories.map((c) => ({
          id: "",
          name: c.name,
          emoji: c.emoji || undefined,
          prompts: c.prompts ?? [],
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
    message.success("Deleted");
    onSaved(null);
    load(null);
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title="My categories"
      width={860}
      footer={
        <div className="flex items-center justify-between">
          {editingId ? (
            <Popconfirm title="Delete this set?" onConfirm={remove}>
              <Button danger type="text" icon={<Trash2 size={14} />}>Delete set</Button>
            </Popconfirm>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button onClick={onClose}>Close</Button>
            <Button type="primary" loading={saving} onClick={save}>Save set</Button>
          </div>
        </div>
      }
    >
      <div className="grid gap-5 md:grid-cols-[200px_1fr]">
        <aside className="space-y-1.5">
          <Button block icon={<Plus size={14} />} onClick={() => load(null)}>New set</Button>
          <Select
            className="w-full"
            placeholder={<span className="inline-flex items-center gap-1"><Copy size={12} /> Start from preset</span>}
            value={null}
            onChange={(id) => load(presets.find((p) => p.id === id) ?? null, true)}
            options={presets.map((p) => ({ value: p.id, label: p.name }))}
          />
          <div className="pt-2 label-caps">Saved sets</div>
          {customSets.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="None yet" />}
          {customSets.map((s) => (
            <button
              key={s.id}
              onClick={() => load(s)}
              className={cn(
                "block w-full truncate rounded-lg px-2.5 py-1.5 text-left text-[13px] text-plum hover:bg-rose-50",
                editingId === s.id && "bg-rose-50 font-medium",
              )}
            >
              {s.name} <span className="text-plum/40">· {s.categories.length}</span>
            </button>
          ))}
        </aside>

        <Form form={form} layout="vertical" requiredMark={false} initialValues={BLANK}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Form.Item name="name" label="Set name" rules={[{ required: true, max: 60 }]}>
              <Input placeholder="Wedding" />
            </Form.Item>
            <Form.Item name="description" label="Description">
              <Input placeholder="optional" maxLength={200} />
            </Form.Item>
          </div>
          <div className="mb-2 grid grid-cols-[52px_1fr_1.6fr_32px] gap-2 label-caps">
            <span>Icon</span>
            <span>Folder name</span>
            <span>Describe it (optional, improves accuracy)</span>
            <span />
          </div>
          <Form.List
            name="categories"
            rules={[
              {
                validator: async (_, cats: FormValues["categories"]) => {
                  if (!cats || cats.length < 1) throw new Error("Add at least one folder");
                  if (cats.length > 40) throw new Error("At most 40 folders");
                  const names = cats.map((c) => (c?.name || "").trim().toLowerCase()).filter(Boolean);
                  const dup = names.find((n, i) => names.indexOf(n) !== i);
                  if (dup) throw new Error(`Duplicate folder name “${dup}”`);
                },
              },
            ]}
          >
            {(fields, { add, remove }, { errors }) => (
              <div className="max-h-[46vh] space-y-2 overflow-y-auto pr-1">
                {fields.map((f) => (
                  <div key={f.key} className="grid grid-cols-[52px_1fr_1.6fr_32px] items-start gap-2">
                    <Form.Item name={[f.name, "emoji"]} noStyle>
                      <Input className="text-center" maxLength={4} />
                    </Form.Item>
                    <Form.Item
                      name={[f.name, "name"]}
                      noStyle
                      rules={[
                        { required: true, whitespace: true, message: "Name required" },
                        { pattern: /^[^/\\:*?"<>|]+$/, message: "Invalid character" },
                        { max: 40 },
                      ]}
                    >
                      <Input placeholder="e.g. Dance floor" />
                    </Form.Item>
                    <Form.Item name={[f.name, "prompts"]} noStyle>
                      <Select mode="tags" placeholder="people dancing at a party, disco lights" tokenSeparators={[","]} maxCount={8} open={false} />
                    </Form.Item>
                    <Button type="text" icon={<Trash2 size={14} />} onClick={() => remove(f.name)} aria-label="Remove folder" />
                  </div>
                ))}
                <Button type="dashed" block icon={<Plus size={14} />} onClick={() => add({ name: "", emoji: "📁", prompts: [] })}>
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

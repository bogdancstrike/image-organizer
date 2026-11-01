import { useMemo, useState } from "react";
import { Button, Input, Tag } from "antd";
import { Search, Check, Copy, PencilLine, Plus } from "lucide-react";
import type { CategorySet } from "@/api";
import { Card } from "./ui/card";
import { cn } from "@/lib/utils";

interface Props {
  presets: CategorySet[];
  customSets: CategorySet[];
  activeId: string | null;
  onUse: (set: CategorySet, custom: boolean) => void;
  onEdit: (set: CategorySet | null, mode: "edit" | "copy" | "new") => void;
}

const mediaTag = (m?: string) => (m === "video" ? " 🎬" : m === "image" ? " 📷" : "");

function SetCard({
  set,
  active,
  custom,
  onUse,
  onEdit,
}: {
  set: CategorySet;
  active: boolean;
  custom: boolean;
  onUse: () => void;
  onEdit: (mode: "edit" | "copy") => void;
}) {
  return (
    <Card className={cn("flex flex-col gap-3 p-4", active && "ring-2 ring-petal")}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 text-[15px] font-semibold text-plum">
            {set.name}
            {custom && <Tag className="m-0" color="purple">mine</Tag>}
            {set.modified && <Tag className="m-0" color="gold">edited</Tag>}
            {active && <Tag className="m-0" color="green">in use</Tag>}
          </div>
          {set.description && <p className="mt-0.5 text-xs text-plum/60">{set.description}</p>}
        </div>
        <span className="shrink-0 text-xs text-plum/45">{set.categories.length} folders</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {set.categories.map((c) => (
          <span key={c.id} className="rounded-full border border-line bg-surface px-2 py-0.5 text-[11px] text-plum/75" title={c.prompts?.join(" · ")}>
            {c.emoji} {c.name}
            {mediaTag(c.media)}
          </span>
        ))}
      </div>
      <div className="mt-auto flex gap-2">
        <Button size="small" type={active ? "default" : "primary"} icon={<Check size={13} />} onClick={onUse} disabled={active}>
          {active ? "Selected" : "Use"}
        </Button>
        <Button size="small" icon={<PencilLine size={13} />} onClick={() => onEdit("edit")}>
          Edit
        </Button>
        <Button size="small" type="text" icon={<Copy size={13} />} onClick={() => onEdit("copy")}>
          Copy
        </Button>
      </div>
    </Card>
  );
}

/** Browse every preset and your own sets. */
export function CategoriesTab({ presets, customSets, activeId, onUse, onEdit }: Props) {
  const [q, setQ] = useState("");
  const match = (s: CategorySet) => {
    const n = q.trim().toLowerCase();
    return !n || s.name.toLowerCase().includes(n) || s.categories.some((c) => c.name.toLowerCase().includes(n));
  };
  const p = useMemo(() => presets.filter(match), [presets, q]); // eslint-disable-line react-hooks/exhaustive-deps
  const c = useMemo(() => customSets.filter(match), [customSets, q]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-3">
        <Input
          allowClear
          prefix={<Search size={14} className="text-plum/40" />}
          placeholder="Find a preset or folder (e.g. wedding, outfit, kitchen)"
          className="max-w-md"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Button icon={<Plus size={14} />} onClick={() => onEdit(null, "new")}>
          New category set
        </Button>
      </div>

      <section>
        <h2 className="mb-3 font-serif text-[22px] italic text-plum/80">My category sets</h2>
        {c.length === 0 ? (
          <p className="text-sm text-plum/55">
            None yet. Press <b>Copy</b> on any preset, or create a new set, e.g. your Instagram folders.
          </p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {c.map((s) => (
              <SetCard key={s.id} set={s} custom active={activeId === s.id} onUse={() => onUse(s, true)} onEdit={(m) => onEdit(s, m)} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-1 font-serif text-[22px] italic text-plum/80">Presets</h2>
        <p className="mb-3 text-xs text-plum/55">Every preset is editable: rename folders, add or remove them, change descriptions. Reset restores the default.</p>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {p.map((s) => (
            <SetCard key={s.id} set={s} custom={false} active={activeId === s.id} onUse={() => onUse(s, false)} onEdit={(m) => onEdit(s, m)} />
          ))}
        </div>
      </section>
    </div>
  );
}

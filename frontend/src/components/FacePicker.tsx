import { useEffect, useRef, useState } from "react";
import { App, Button, Input, Popconfirm, Segmented, Spin } from "antd";
import { Check, Trash2, Upload, UserRound } from "lucide-react";
import { api, type FaceRef } from "@/api";
import { cn } from "@/lib/utils";

interface Props {
  value: string | null; // selected reference face id; null = everyone
  onChange: (id: string | null) => void;
}

/** By person: everyone (one folder per person) or only one person, chosen by uploading a photo of their face. */
export function FacePicker({ value, onChange }: Props) {
  const { message } = App.useApp();
  const [mode, setMode] = useState<"all" | "one">(value ? "one" : "all");
  const [faces, setFaces] = useState<FaceRef[] | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.faces().then(setFaces).catch(() => setFaces([]));
  }, []);
  // a saved choice whose face was deleted elsewhere: fall back to everyone
  useEffect(() => {
    if (faces && value && !faces.some((f) => f.id === value)) onChange(null);
  }, [faces, value, onChange]);

  const upload = async (file: File) => {
    if (file.size > 25 << 20) {
      message.error("Photo too large (max 25 MB)");
      return;
    }
    setBusy(true);
    try {
      const ref = await api.addFace(file, name.trim());
      setFaces((fs) => [ref, ...(fs ?? []).filter((f) => f.id !== ref.id)]);
      setName("");
      onChange(ref.id);
      if (ref.faces_in_photo > 1) message.info(`${ref.faces_in_photo} faces in that photo: the largest one was used.`);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };

  const remove = async (id: string) => {
    try {
      await api.deleteFace(id);
      setFaces((fs) => (fs ?? []).filter((f) => f.id !== id));
      if (value === id) onChange(null);
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  return (
    <div className="py-3">
      <div className="mb-2 text-[13px] font-medium text-plum">Who</div>
      <Segmented
        block
        value={mode}
        onChange={(v) => {
          setMode(v as "all" | "one");
          if (v === "all") onChange(null);
          else if (faces?.length && !value) onChange(faces[0].id);
        }}
        options={[
          { value: "all", label: "Everyone, a folder each" },
          { value: "one", label: "Only one person" },
        ]}
      />
      {mode === "one" && (
        <div className="mt-3 rounded-xl border border-line bg-surface/60 p-3">
          <p className="mb-3 text-[11px] text-plum/55">
            Upload a clear photo of their face. Only photos where this person appears are moved; everything else stays where it is.
          </p>
          {faces === null ? (
            <Spin size="small" />
          ) : (
            faces.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {faces.map((f) => (
                  <div
                    key={f.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => onChange(f.id)}
                    onKeyDown={(e) => e.key === "Enter" && onChange(f.id)}
                    className={cn(
                      "group flex cursor-pointer items-center gap-2 rounded-full border py-1 pl-1 pr-3 text-[12px] transition",
                      value === f.id ? "border-plum bg-tint text-plum" : "border-line text-plum/70 hover:bg-tint",
                    )}
                  >
                    {f.cover ? <img src={f.cover} alt="" className="h-7 w-7 rounded-full object-cover" /> : <UserRound size={18} className="m-1" />}
                    <span className="max-w-32 truncate">{f.name}</span>
                    {value === f.id && <Check size={13} />}
                    <span onClick={(e) => e.stopPropagation()}>
                      <Popconfirm title="Forget this face?" onConfirm={() => remove(f.id)}>
                        <button aria-label={`Forget ${f.name}`} className="ml-0.5 inline-flex text-plum/35 hover:text-plum">
                          <Trash2 size={12} />
                        </button>
                      </Popconfirm>
                    </span>
                  </div>
                ))}
              </div>
            )
          )}
          {!value && faces && faces.length === 0 && <p className="mb-2 text-[11px] text-plum/55">No face yet: until you upload one, everyone is sorted.</p>}
          <div className="flex gap-2">
            <Input size="small" placeholder="Name (optional), e.g. Laura" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} />
            <Button size="small" loading={busy} icon={<Upload size={13} />} onClick={() => input.current?.click()}>
              Upload face
            </Button>
            <input ref={input} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          </div>
        </div>
      )}
    </div>
  );
}

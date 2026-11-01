export type Strategy = "preset" | "custom" | "auto" | "date";

export interface Health {
  status: string;
  version: string;
  ai_available: boolean;
  model: string | null;
  library_ok: boolean;
  library_name: string;
  library_host_path: string | null;
  output_dir: string;
}

export interface Category {
  id: string;
  name: string;
  emoji?: string;
  prompts?: string[];
  media?: "any" | "image" | "video";
}

export interface CategorySet {
  id: string;
  name: string;
  description?: string | null;
  categories: Category[];
  custom?: boolean;
}

export interface JobCategory extends Category {
  photos: number;
  videos: number;
}

export interface PlanItem {
  file_id: string;
  rel_path: string;
  name: string;
  kind: "image" | "video";
  thumb: string;
  category_id: string;
  category: string;
  confidence: number;
  source: string;
  destination: string;
  duplicate_of: string | null;
}

export interface Usage {
  calls: number;
  input_tokens: number;
  output_tokens: number;
  model: string;
}

export interface JobSnapshot {
  id: string;
  status: string;
  phase: string;
  categories: JobCategory[];
  stats: Record<string, number>;
  warnings: string[];
  errors: { rel_path: string; error: string }[];
  usage: Usage | null;
  run_id: string | null;
  error: string | null;
  plan?: PlanItem[];
}

export interface Folder {
  name: string;
  path: string;
  media_count: number;
  has_children: boolean;
}

export interface Run {
  run_id: string;
  created_at: string;
  mode: string;
  source: string;
  status: string;
  moved: number;
  failed: number;
  undo?: { restored: number; problems: { file: string; error: string }[] } | null;
}

export interface JobEvent {
  seq: number;
  type: string;
  [k: string]: any; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export interface JobRequest {
  source: string;
  strategy: Strategy;
  set_id: string | null;
  options: {
    min_confidence: number;
    near_duplicates: boolean;
    split_media: boolean;
    ai_assist: boolean;
    date_granularity: "year" | "month" | "day";
    max_clusters: number;
    output_dir: string;
    recursive: boolean;
  };
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* not json */
    }
    throw new Error(msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  health: () => req<Health>("/api/health"),
  presets: () => req<CategorySet[]>("/api/presets"),
  sets: () => req<CategorySet[]>("/api/category-sets"),
  saveSet: (id: string | null, body: Omit<CategorySet, "id">) =>
    id
      ? req<CategorySet>(`/api/category-sets/${id}`, { method: "PUT", body: JSON.stringify(body) })
      : req<CategorySet>("/api/category-sets", { method: "POST", body: JSON.stringify(body) }),
  deleteSet: (id: string) => req<void>(`/api/category-sets/${id}`, { method: "DELETE" }),
  folders: (path: string) => req<{ path: string; name: string; media_count: number; folders: Folder[] }>(
    `/api/folders?path=${encodeURIComponent(path)}`,
  ),
  startJob: (body: JobRequest) => req<{ id: string }>("/api/jobs", { method: "POST", body: JSON.stringify(body) }),
  job: (id: string) => req<JobSnapshot>(`/api/jobs/${id}`),
  cancel: (id: string) => req<{ cancelled: boolean }>(`/api/jobs/${id}/cancel`, { method: "POST" }),
  apply: (id: string, mode: "move" | "copy") =>
    req<{ run_id: string; moved: number; failed: { src: string; error: string }[]; skipped: number }>(
      `/api/jobs/${id}/apply`,
      { method: "POST", body: JSON.stringify({ mode }) },
    ),
  runs: () => req<Run[]>("/api/runs"),
  undo: (runId: string) =>
    req<{ run_id: string; status: string; undo: Run["undo"] }>(`/api/runs/${runId}/undo`, { method: "POST" }),
};

/** Subscribe to job events. EventSource reconnects replay from the start, so callers dedupe by seq. */
export function subscribe(jobId: string, onEvents: (evs: JobEvent[]) => void, onEnd: () => void): () => void {
  const es = new EventSource(`/api/jobs/${jobId}/events`);
  es.onmessage = (m) => {
    try {
      const data = JSON.parse(m.data);
      onEvents(Array.isArray(data) ? data : [data]);
    } catch {
      /* ignore malformed */
    }
  };
  es.addEventListener("end", () => {
    es.close();
    onEnd();
  });
  return () => es.close();
}

export type Strategy = "preset" | "custom" | "auto" | "date" | "cull" | "people" | "trips" | "places" | "rules";

export interface Recipe {
  id: string;
  emoji: string;
  strategy: Strategy;
  set_id?: string;
  options: { quality?: Partial<QualityOptions>; ocr?: boolean; focus?: string };
}

export interface Suggestion {
  total: number;
  photos: number;
  videos: number;
  theme?: string;
  gps_share?: number; // share of sampled photos with GPS: trips & places are only offered when > 0
  suggestions: { recipe: string; reason: { key: string; theme?: string; pct?: number } }[];
}

export interface Health {
  status: string;
  device?: "cpu" | "gpu";
  version: string;
  ai_available: boolean;
  model: string | null;
  library_ok: boolean;
  library_name: string;
  library_host_path: string | null;
  faces_available: boolean;
  people_available?: boolean;
  ocr_available?: boolean;
  output_dir: string;
}

export interface Category {
  id: string;
  name: string;
  emoji?: string;
  prompts?: string[];
  media?: "any" | "image" | "video";
  ai_hint?: string | null;
}

export interface CategorySet {
  id: string;
  name: string;
  description?: string | null;
  categories: Category[];
  custom?: boolean;
  modified?: boolean;
}

export interface JobCategory extends Category {
  cover?: string | null;
  photos: number;
  videos: number;
}

export interface ImageTag { label: string; score: number; group: string; source: string }

export interface TagFacets { tags: { label: string; count: number }[]; tagged: number; indexed: number }

export interface DecisionInfo {
  action: string;
  explanation: string;
  evidence: string[];
  kept_path?: string;
  kept_preview_path?: string;
  previous?: { category: string; explanation: string };
}

export interface PlanItem {
  decision?: DecisionInfo;
  preview_path?: string;
  tags?: ImageTag[];
  pick?: { winner?: boolean; rating?: number; score: number; reasons: string[]; picked: boolean; profile?: string; parts?: Record<string, number> } | null;
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
  sidecars: string[];
  quality: QualitySummary | null;
  burst: { group: number; size: number; best: boolean; margin?: number } | null;
  text?: string | null;
}

export interface QualitySummary {
  eyes_open?: number;
  faces_considered?: number;
  aspect_ratio?: number;
  face_regions?: { box: number[]; sharpness: number | null; blink: number }[];
  rating?: number;
  score: number;
  stars: number;
  sharpness: number;
  brightness: number;
  faces: number;
  blink: number | null;
  smile: number | null;
  flags: string[];
  smiling: boolean;
  faces_checked: boolean;
}

export interface QualityOptions {
  subject_prompt: string;
  social_media: boolean;
  social_aesthetic: boolean;
  social_format: "portrait" | "square" | "vertical" | "landscape" | "original";
  social_weight: number;
  preserve_unique: boolean;
  pareto_review: boolean;
  enabled: boolean;
  blur: boolean;
  eyes_closed: boolean;
  exposure: boolean;
  smiles: boolean;
  blur_threshold: number;
  blink_threshold: number;
  smile_threshold: number;
  action: "reject" | "tag";
  faces_rule: "any" | "main";
  dark_threshold: number;
  bright_threshold: number;
  bursts: boolean;
  burst_seconds: number;
  burst_similarity: number;
  keeper_min_stars: number;
  pick_min_rating: number;
  keeper_min_rating: number;
  noise_check: boolean;
  noise_threshold: number;
  tilt_check: boolean;
  tilt_tolerance: number;
  face_crop: boolean;
  pick_profile: "auto" | "portrait" | "fashion" | "landscape" | "general";
  picks_percent: number;
  similar_any_time: boolean;
  write_xmp: boolean;
}

export interface AIOptions {
  model: string | null;
  reasoning_effort: "minimal" | "low" | "medium" | "high" | null;
  naming_prompt: string; // "" = server default
  assist_prompt: string;
  assist_scope: "unsure" | "all";
  assist_batch: number;
}

export interface AIDefaults {
  naming_prompt: string;
  assist_prompt: string;
  naming_placeholders: string[];
  assist_placeholders: string[];
  naming_format: string;
  assist_format: string;
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
  context: { theme: string; confidence?: number; focus?: string; source?: string } | null;
  run_id: string | null;
  error: string | null;
  plan?: PlanItem[];
}

export interface FolderListing {
  path: string;
  name: string;
  media_count: number;
  folders: Folder[];
  samples?: string[];
}

export interface Place {
  kind: "pictures" | "downloads" | "desktop" | "documents" | "videos" | "dcim";
  name: string;
  path: string;
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
  in_trash?: number;
  undo?: { restored: number; problems: { file: string; error: string }[] } | null;
}

export interface HistoryItem {
  job_id: string | null;
  finished_at: number | null;
  source: string | null;
  strategy: string | null;
  model: string | null;
  files: number | null;
  photos?: number;
  videos?: number;
  embedded?: number;
  duplicates?: number;
  folders?: number;
  wall?: number;
  phases?: Record<string, number>;
  usage?: { input_tokens?: number; output_tokens?: number } | null;
  outcome: "applied" | "undone" | "not_applied" | "cancelled" | "failed";
  run: (Run & { in_trash: number }) | null;
  categories: { name: string; count: number }[];
  reopen: boolean;
}

export interface HistoryPage {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
  counts: Record<"all" | "applied" | "undone" | "not_applied" | "cancelled" | "failed", number>;
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
    rules_prompt?: string;
    min_confidence: number;
    near_duplicates: boolean;
    split_media: boolean;
    duplicates_action: "folder" | "with_original" | "keep";
    duplicate_keep: "best" | "oldest" | "newest";
    near_dup_distance: number;
    ai_assist: boolean;
    ai_max_files: number;
    model: "clip" | "siglip2";
    ocr: boolean;
    auto_tags?: boolean;
    people_min_photos: number;
    people_similarity: number;
    people_multi: "main" | "copy";
    people_reference: string | null;
    date_granularity: "year" | "month" | "day";
    place_granularity?: "country" | "city";
    max_clusters: number;
    output_dir: string;
    recursive: boolean;
    pair_sidecars: boolean;
    quality: QualityOptions;
    focus: "auto" | "scene" | "framing" | "outfit" | "lighting" | "subject";
    granularity: "coarse" | "normal" | "fine";
    ai: AIOptions;
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

export interface LibHit {
  match_explanation?: string | null;
  tags?: ImageTag[];
  path: string;
  score: number;
  thumb: string;
  captured_at: number;
}

export interface LibResults {
  results: LibHit[];
  indexed: number;
  took_ms?: number;
  missing?: boolean;
}

export interface MapPoint {
  lat: number;
  lon: number;
  count: number;
  city: string | null;
  country: string | null;
  cc: string | null;
  paths: string[];
}

export interface PlacesResult {
  points: MapPoint[];
  photos: number;
  located: number;
  countries: { name: string; count: number }[];
}

export interface TripInfo {
  name: string;
  start: number;
  end: number;
  count: number;
  center: [number, number] | null;
  countries: string[];
  samples: string[];
  paths: string[];
}

export interface TripsResult {
  trips: TripInfo[];
  home: { lat: number; lon: number; city?: string; country?: string } | null;
  photos: number;
  located: number;
}

export interface FaceRef {
  id: string;
  name: string;
  cover: string | null;
  faces_in_photo: number;
}

export interface StatsRow {
  job_id: string;
  finished_at: number;
  strategy: string;
  model: string;
  files: number;
  photos: number;
  videos: number;
  embedded: number;
  duplicates: number;
  folders: number;
  wall: number;
  phases: Record<string, number>;
  source: string;
  status: string;
}

export interface Stats {
  sorts: number;
  failed_sorts: number;
  files_processed: number;
  files_analyzed: number;
  processing_seconds: number;
  avg_files_per_second: number;
  avg_seconds_per_sort: number;
  phase_seconds: Record<string, number>;
  by_strategy: Record<string, number>;
  by_model: Record<string, number>;
  applies: number;
  photos_organized: number;
  ai_tokens: number;
  recent: StatsRow[];
}

export const thumbUrl = (path: string) => `/api/thumb?path=${encodeURIComponent(path)}`;

export const previewUrl = (relPath: string) => `/api/preview?path=${encodeURIComponent(relPath)}`;

export const api = {
  health: () => req<Health>("/api/health"),
  presets: () => req<CategorySet[]>("/api/presets"),
  sets: () => req<CategorySet[]>("/api/category-sets"),
  saveSet: (id: string | null, body: Omit<CategorySet, "id">) =>
    id
      ? req<CategorySet>(`/api/category-sets/${id}`, { method: "PUT", body: JSON.stringify(body) })
      : req<CategorySet>("/api/category-sets", { method: "POST", body: JSON.stringify(body) }),
  deleteSet: (id: string) => req<void>(`/api/category-sets/${id}`, { method: "DELETE" }),
  folders: (path: string) => req<FolderListing>(
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
  reassign: (id: string, fileIds: string[], categoryId: string) =>
    req<{ changed: PlanItem[]; categories: JobCategory[]; stats: Record<string, number> }>(`/api/jobs/${id}/plan`, {
      method: "PATCH",
      body: JSON.stringify({ file_ids: fileIds, category_id: categoryId }),
    }),
  history: (outcome: string, limit: number, offset: number) =>
    req<HistoryPage>(`/api/history?${new URLSearchParams({ outcome, limit: String(limit), offset: String(offset) })}`),
  emptyTrash: (runId: string) =>
    req<{ deleted: number; freed_bytes: number }>(`/api/runs/${runId}/empty-trash`, { method: "POST" }),
  libStatus: (folder: string, model: string) =>
    req<{ indexed: number; tagged?: number }>(`/api/library/status?${new URLSearchParams({ folder, model })}`),
  libTags: (folder: string, model: string) => req<TagFacets>(`/api/library/tags?${new URLSearchParams({ folder, model })}`),
  libSearch: (q: string, folder: string, model: string, tags: string[] = []) => {
    const params = new URLSearchParams({ q, folder, model });
    tags.forEach(tag => params.append("tag", tag));
    return req<LibResults>(`/api/library/search?${params}`);
  },
  libSimilar: (path: string, folder: string, model: string) =>
    req<LibResults>(`/api/library/similar?${new URLSearchParams({ path, folder, model })}`),
  libPlaces: (folder: string) => req<PlacesResult>(`/api/library/places?${new URLSearchParams({ folder })}`),
  libTrips: (folder: string) => req<TripsResult>(`/api/library/trips?${new URLSearchParams({ folder })}`),
  factoryReset: (confirm: string, includeCache: boolean) =>
    req<{ ok: boolean }>("/api/admin/reset", { method: "POST", body: JSON.stringify({ confirm, include_cache: includeCache }) }),
  places: () => req<Place[]>("/api/places"),
  faces: () => req<FaceRef[]>("/api/faces"),
  addFace: async (file: File, name: string) => {
    const res = await fetch(`/api/faces?name=${encodeURIComponent(name)}`, { method: "POST", body: file, headers: { "Content-Type": file.type || "application/octet-stream" } });
    if (!res.ok) {
      let msg = `${res.status} ${res.statusText}`;
      try {
        const b = await res.json();
        if (typeof b.detail === "string") msg = b.detail;
      } catch {
        /* not json */
      }
      throw new Error(msg);
    }
    return (await res.json()) as FaceRef;
  },
  deleteFace: (id: string) => req<void>(`/api/faces/${id}`, { method: "DELETE" }),
  stats: () => req<Stats>("/api/stats"),
  getSettings: () => req<Record<string, unknown>>("/api/settings"),
  putSettings: (s: unknown) => req<{ ok: boolean }>("/api/settings", { method: "PUT", body: JSON.stringify(s) }),
  recipes: () => req<Recipe[]>("/api/recipes"),
  suggest: (path: string, recursive: boolean) =>
    req<Suggestion>(`/api/suggest?path=${encodeURIComponent(path)}&recursive=${recursive}`),
  renameCategory: (jobId: string, catId: string, name: string) =>
    req<{ categories: JobCategory[]; plan: PlanItem[] }>(`/api/jobs/${jobId}/categories/${catId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  aiDefaults: () => req<AIDefaults>("/api/ai/defaults"),
  aiModels: () => req<{ default: string | null; models: string[]; error?: string }>("/api/ai/models"),
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

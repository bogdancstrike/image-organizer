import type { AIOptions, QualityOptions, Strategy } from "./api";

export interface UiSettings {
  source: string;
  strategy: Strategy;
  presetId: string;
  customSetId: string | null;
  minConfidence: number;
  nearDuplicates: boolean;
  splitMedia: boolean;
  aiAssist: boolean;
  dateGranularity: "year" | "month" | "day";
  maxClusters: number;
  applyMode: "move" | "copy";
  outputMode: "subfolder" | "direct";
  outputDir: string;
  recursive: boolean;
  pairSidecars: boolean;
  quality: QualityOptions;
  duplicatesAction: "folder" | "with_original" | "keep" | "delete";
  duplicateKeep: "best" | "oldest" | "newest";
  nearDupDistance: number;
  focus: "auto" | "scene" | "framing" | "outfit" | "lighting" | "subject";
  granularity: "coarse" | "normal" | "fine";
  ai: AIOptions;
  aiMaxFiles: number;
  recipeId: string | null;
  recipeFor: string | null; // folder the recipe was recommended for
  model: "clip" | "siglip2";
  ocr: boolean;
  peopleMinPhotos: number;
  peopleSimilarity: number;
  peopleMulti: "main" | "copy";
  peopleReference: string | null;
  qualityVersion?: number;
}

export const DEFAULT_SETTINGS: UiSettings = {
  source: "",
  strategy: "preset",
  presetId: "lifestyle",
  customSetId: null,
  minConfidence: 0.3,
  nearDuplicates: true,
  splitMedia: true,
  aiAssist: false,
  dateGranularity: "month",
  maxClusters: 12,
  applyMode: "move",
  outputMode: "subfolder",
  outputDir: "Organized",
  recursive: true,
  pairSidecars: true,
  quality: {
    enabled: false,
    blur: false,
    eyes_closed: false,
    exposure: false,
    smiles: false,
    blur_threshold: 0.5,
    blink_threshold: 0.5,
    smile_threshold: 0.5,
    action: "reject",
    faces_rule: "any",
    dark_threshold: 0.18,
    bright_threshold: 0.85,
    bursts: false,
    burst_seconds: 2,
    burst_similarity: 0.9,
    keeper_min_stars: 0,
    noise_check: false,
    noise_threshold: 0.045,
    tilt_check: false,
    tilt_tolerance: 1.5,
    face_crop: false,
    picks_percent: 0,
    similar_any_time: false,
    write_xmp: false,
  },
  duplicatesAction: "folder",
  duplicateKeep: "best",
  nearDupDistance: 4,
  focus: "auto",
  granularity: "normal",
  aiMaxFiles: 300,
  recipeId: null,
  recipeFor: null,
  model: "clip",
  ocr: false,
  peopleMinPhotos: 3,
  peopleSimilarity: 0.363,
  peopleMulti: "main",
  peopleReference: null,
  ai: { model: null, reasoning_effort: null, naming_prompt: "", assist_prompt: "", assist_scope: "unsure", assist_batch: 12 },
};

const KEY = "aio.settings.v1";
/** v2: every Pro check is optional and OFF by default; older saved settings get the new defaults once. */
export const QUALITY_VERSION = 2;

export function migrateSettings(saved: Partial<UiSettings> & { qualityVersion?: number }): UiSettings {
  const fresh = (saved.qualityVersion ?? 1) < QUALITY_VERSION;
  return {
    ...DEFAULT_SETTINGS,
    ...saved,
    qualityVersion: QUALITY_VERSION,
    quality: fresh ? DEFAULT_SETTINGS.quality : { ...DEFAULT_SETTINGS.quality, ...(saved.quality ?? {}) },
    ai: { ...DEFAULT_SETTINGS.ai, ...(saved.ai ?? {}) },
  } as UiSettings;
}

export function loadSettings(): UiSettings {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      return migrateSettings(JSON.parse(raw));
    }
  } catch {
    /* storage unavailable */
  }
  return DEFAULT_SETTINGS;
}

export function saveSettings(s: UiSettings) {
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* storage unavailable */
  }
}

import type { Strategy } from "./api";

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
};

const KEY = "aio.settings.v1";

export function loadSettings(): UiSettings {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
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

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { App as AntApp, ConfigProvider, Tooltip, theme as antdTheme, type ThemeConfig } from "antd";
import { cn } from "@/lib/utils";

export type ThemeName = "pink" | "blue" | "sage" | "peach" | "lavender" | "dark" | "midnight";

export const THEMES: { id: ThemeName; label: string; swatch: [string, string] }[] = [
  { id: "pink", label: "Blossom (pink)", swatch: ["#fbe1ec", "#e5679b"] },
  { id: "blue", label: "Sky (blue)", swatch: ["#dce9ff", "#4f8ff7"] },
  { id: "sage", label: "Sage (green)", swatch: ["#dcefe2", "#4f9a6b"] },
  { id: "peach", label: "Peach (sunset)", swatch: ["#ffe2d0", "#ee7b4a"] },
  { id: "lavender", label: "Lavender", swatch: ["#e6defd", "#8a6ae6"] },
  { id: "dark", label: "Graphite (dark)", swatch: ["#3f3f46", "#09090b"] },
  { id: "midnight", label: "Midnight (dark navy)", swatch: ["#4f6fe0", "#070b18"] },
];

const FONT = '"Inter Variable", ui-sans-serif, system-ui, sans-serif';

const ANTD: Record<ThemeName, ThemeConfig> = {
  pink: {
    token: {
      colorPrimary: "#b8467d",
      colorText: "#4a1d3b",
      colorTextSecondary: "rgba(74,29,59,.6)",
      borderRadius: 12,
      fontFamily: FONT,
      colorBgElevated: "#fffafc",
      colorBorderSecondary: "#f6dde8",
    },
    components: { Segmented: { itemSelectedBg: "#fff", trackBg: "#f8e8ef" } },
  },
  blue: {
    token: {
      colorPrimary: "#2f6fdb",
      colorText: "#142a4d",
      colorTextSecondary: "rgba(20,42,77,.6)",
      borderRadius: 12,
      fontFamily: FONT,
      colorBgElevated: "#fafcff",
      colorBorderSecondary: "#dbe7fb",
    },
    components: { Segmented: { itemSelectedBg: "#fff", trackBg: "#e6efff" } },
  },
  sage: {
    token: {
      colorPrimary: "#3f8a5c",
      colorText: "#1f3a2e",
      colorTextSecondary: "rgba(31,58,46,.6)",
      borderRadius: 12,
      fontFamily: FONT,
      colorBgElevated: "#fafdfb",
      colorBorderSecondary: "#dcebe0",
    },
    components: { Segmented: { itemSelectedBg: "#fff", trackBg: "#e3f1e7" } },
  },
  peach: {
    token: {
      colorPrimary: "#d9653a",
      colorText: "#4a2618",
      colorTextSecondary: "rgba(74,38,24,.6)",
      borderRadius: 12,
      fontFamily: FONT,
      colorBgElevated: "#fffaf7",
      colorBorderSecondary: "#fbe3d6",
    },
    components: { Segmented: { itemSelectedBg: "#fff", trackBg: "#fde4d6" } },
  },
  lavender: {
    token: {
      colorPrimary: "#7656d8",
      colorText: "#2f2350",
      colorTextSecondary: "rgba(47,35,80,.6)",
      borderRadius: 12,
      fontFamily: FONT,
      colorBgElevated: "#fcfbff",
      colorBorderSecondary: "#e6e0fa",
    },
    components: { Segmented: { itemSelectedBg: "#fff", trackBg: "#ebe5fc" } },
  },
  midnight: {
    algorithm: antdTheme.darkAlgorithm,
    token: {
      colorPrimary: "#7c9cff",
      colorText: "#e6ecff",
      colorBgBase: "#070b18",
      colorBgElevated: "#121a33",
      colorBgContainer: "#121a33",
      colorBorder: "#2a3a70",
      colorBorderSecondary: "#1f2a4a",
      borderRadius: 12,
      fontFamily: FONT,
    },
    components: { Segmented: { itemSelectedBg: "#2a3a70", trackBg: "#121a33" } },
  },
  dark: {
    algorithm: antdTheme.darkAlgorithm,
    token: {
      colorPrimary: "#fafafa",
      colorTextLightSolid: "#18181b",
      colorText: "#fafafa",
      colorBgBase: "#09090b",
      colorBgElevated: "#18181b",
      colorBgContainer: "#18181b",
      colorBorder: "#3f3f46",
      colorBorderSecondary: "#27272a",
      borderRadius: 10,
      fontFamily: FONT,
    },
    components: {
      Segmented: { itemSelectedBg: "#3f3f46", trackBg: "#18181b" },
      Button: { primaryColor: "#18181b" },
    },
  },
};

const KEY = "aio.theme";

function initialTheme(): ThemeName {
  try {
    const saved = localStorage.getItem(KEY) as ThemeName | null;
    if (saved && THEMES.some((t) => t.id === saved)) return saved;
  } catch {
    /* storage unavailable */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "pink";
}

const ThemeCtx = createContext<{ theme: ThemeName; setTheme: (t: ThemeName) => void }>({
  theme: "pink",
  setTheme: () => {},
});

export function useTheme() {
  return useContext(ThemeCtx);
}

export function ThemeRoot({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeName>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    meta?.setAttribute("content", getComputedStyle(document.documentElement).getPropertyValue("--page").trim() || "#fdf8fa");
  }, [theme]);

  const setTheme = (t: ThemeName) => {
    setThemeState(t);
    try {
      localStorage.setItem(KEY, t);
    } catch {
      /* storage unavailable */
    }
  };

  return (
    <ThemeCtx.Provider value={{ theme, setTheme }}>
      <ConfigProvider theme={ANTD[theme]}>
        <AntApp>{children}</AntApp>
      </ConfigProvider>
    </ThemeCtx.Provider>
  );
}

/** Three round swatches; the active one gets a ring. */
export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="flex items-center gap-1 rounded-full border border-line bg-surface/70 px-1.5 py-1" role="radiogroup" aria-label="Theme">
      {THEMES.map((t) => (
        <Tooltip key={t.id} title={t.label}>
          <button
            role="radio"
            aria-checked={theme === t.id}
            aria-label={t.label}
            onClick={() => setTheme(t.id)}
            className={cn(
              "h-5 w-5 cursor-pointer rounded-full border border-black/10 transition-transform hover:scale-110",
              theme === t.id && "ring-2 ring-plum/60 ring-offset-1 ring-offset-transparent",
            )}
            style={{ background: `linear-gradient(135deg, ${t.swatch[0]} 0%, ${t.swatch[1]} 100%)` }}
          />
        </Tooltip>
      ))}
    </div>
  );
}

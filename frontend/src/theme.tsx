import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { App as AntApp, ConfigProvider, Tooltip, theme as antdTheme, type ThemeConfig } from "antd";
import { cn } from "@/lib/utils";

export type ThemeName = "pink" | "blue" | "dark";

export const THEMES: { id: ThemeName; label: string; swatch: [string, string] }[] = [
  { id: "pink", label: "Blossom (pink)", swatch: ["#fbe1ec", "#e5679b"] },
  { id: "blue", label: "Sky (blue)", swatch: ["#dce9ff", "#4f8ff7"] },
  { id: "dark", label: "Graphite (dark)", swatch: ["#3f3f46", "#09090b"] },
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
    meta?.setAttribute("content", theme === "dark" ? "#09090b" : theme === "blue" ? "#f6f9ff" : "#fdf8fa");
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

import { useState } from "react";
import { Check, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import type { Recipe, Suggestion } from "@/api";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/utils";

interface Props {
  recipes: Recipe[];
  suggestion: Suggestion | null;
  loading: boolean;
  active: string | null;
  disabled?: boolean;
  onPick: (r: Recipe) => void;
}

/** "What's in this folder?": recommends a recipe (with the reason) so users never face a wall of options. */
export function RecipePicker({ recipes, suggestion, loading, active, disabled, onPick }: Props) {
  const { t } = useI18n();
  const [all, setAll] = useState(false);
  const suggested = (suggestion?.suggestions ?? [])
    .map((s) => ({ s, r: recipes.find((r) => r.id === s.recipe) }))
    .filter((x): x is { s: Suggestion["suggestions"][number]; r: Recipe } => !!x.r);
  const reason = (s: Suggestion["suggestions"][number]) =>
    t(`reason.${s.reason.key}`, { theme: s.reason.theme ?? "", pct: s.reason.pct ?? 0 });

  const card = (r: Recipe, why?: string, top?: boolean) => {
    const on = active === r.id;
    return (
      <button
        key={r.id}
        disabled={disabled}
        onClick={() => onPick(r)}
        className={cn(
          "relative flex min-w-0 cursor-pointer items-start gap-3 rounded-2xl border p-3.5 text-left transition-all hover:-translate-y-0.5 disabled:cursor-default disabled:opacity-60",
          on ? "border-plum/70 bg-tint ring-2 ring-plum/30" : "border-line bg-surface/70 hover:border-plum/30",
        )}
      >
        <span className="text-2xl leading-none">{r.emoji}</span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-1.5 text-[14px] font-semibold text-plum">
            {t(`r.${r.id}.t`)}
            {top && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-plum px-1.5 py-px text-[10px] font-medium text-on-ink">
                <Sparkles size={10} /> {t("recipe.recommended")}
              </span>
            )}
          </span>
          <span className="mt-0.5 block text-[12px] leading-snug text-plum/60">{why ?? t(`r.${r.id}.d`)}</span>
        </span>
        {on && <Check size={16} className="mt-0.5 shrink-0 text-plum" />}
      </button>
    );
  };

  return (
    <div className="mx-auto mt-8 w-full max-w-4xl text-left">
      <div className="mb-2.5 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-serif text-[22px] italic text-plum/85">{t("recipe.ask")}</h2>
        {suggestion && <span className="text-xs text-plum/50">{t("recipe.counts", { photos: suggestion.photos, videos: suggestion.videos })}</span>}
      </div>
      {loading && !suggested.length ? (
        <div className="shimmer flex h-[76px] items-center justify-center rounded-2xl text-xs text-plum/50">{t("recipe.looking")}</div>
      ) : (
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">{suggested.map(({ s, r }, i) => card(r, reason(s), i === 0))}</div>
      )}
      <button onClick={() => setAll((v) => !v)} className="mt-2.5 inline-flex cursor-pointer items-center gap-1 text-xs text-plum/55 hover:text-plum">
        {all ? <ChevronUp size={13} /> : <ChevronDown size={13} />} {all ? t("recipe.less") : t("recipe.more")}
      </button>
      {all && (
        <div className="pop-in mt-2.5 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {recipes.filter((r) => !suggested.some((x) => x.r.id === r.id)).map((r) => card(r))}
        </div>
      )}
    </div>
  );
}

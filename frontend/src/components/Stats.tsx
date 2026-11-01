import { CountUp } from "./CountUp";
import { useI18n } from "@/i18n";

export interface StatValues {
  total: number;
  videos: number;
  photos: number;
  folders: number;
  duplicates: number;
}

const ITEMS: { key: keyof StatValues; label: string; dot?: string }[] = [
  { key: "total", label: "stats.total" },
  { key: "videos", label: "stats.videos", dot: "bg-plum" },
  { key: "photos", label: "stats.photos", dot: "bg-petal" },
  { key: "folders", label: "stats.folders" },
  { key: "duplicates", label: "stats.duplicates" },
];

export function Stats({ values }: { values: StatValues }) {
  const { t } = useI18n();
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
      {ITEMS.map((it) => (
        <div key={it.key} className="min-w-0">
          <div className="label-caps flex items-center gap-1.5">
            {it.dot && <span className={`inline-block h-1.5 w-1.5 rounded-full ${it.dot}`} />}
            {t(it.label)}
          </div>
          <CountUp value={values[it.key]} className="mt-0.5 block text-3xl font-semibold tabular-nums tracking-tight sm:text-[34px]" />
        </div>
      ))}
    </div>
  );
}

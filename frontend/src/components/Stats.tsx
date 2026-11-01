import { CountUp } from "./CountUp";

export interface StatValues {
  total: number;
  videos: number;
  photos: number;
  folders: number;
  duplicates: number;
}

const ITEMS: { key: keyof StatValues; label: string; dot?: string }[] = [
  { key: "total", label: "Total files" },
  { key: "videos", label: "Videos", dot: "bg-plum" },
  { key: "photos", label: "Photos", dot: "bg-petal" },
  { key: "folders", label: "Folders created" },
  { key: "duplicates", label: "Duplicates found" },
];

export function Stats({ values }: { values: StatValues }) {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
      {ITEMS.map((it) => (
        <div key={it.key} className="min-w-0">
          <div className="label-caps flex items-center gap-1.5">
            {it.dot && <span className={`inline-block h-1.5 w-1.5 rounded-full ${it.dot}`} />}
            {it.label}
          </div>
          <CountUp value={values[it.key]} className="mt-0.5 block text-3xl font-semibold tabular-nums tracking-tight sm:text-[34px]" />
        </div>
      ))}
    </div>
  );
}

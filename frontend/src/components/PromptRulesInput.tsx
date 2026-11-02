import { useId } from "react";
import { Input } from "antd";
import { useI18n } from "@/i18n";

export function PromptRulesInput({ value, onChange, aiAvailable }: {
  value: string;
  onChange: (value: string) => void;
  aiAvailable: boolean;
}) {
  const id = useId();
  const { t } = useI18n();
  return (
    <div className="w-full space-y-2 text-left">
      <label htmlFor={id} className="text-[13px] font-medium text-plum">{t("rules.instructions")}</label>
      <Input.TextArea id={id} value={value} onChange={(e) => onChange(e.target.value)}
        autoSize={{ minRows: 3, maxRows: 8 }} maxLength={4000}
        placeholder={t("rules.example")} aria-describedby={`${id}-help`} />
      <p id={`${id}-help`} className="text-xs leading-relaxed text-plum/60">
        {aiAvailable ? t("rules.privacy") : t("rules.noai")}
      </p>
      <p className="text-[11px] leading-relaxed text-plum/50">{t("rules.paths")}</p>
    </div>
  );
}

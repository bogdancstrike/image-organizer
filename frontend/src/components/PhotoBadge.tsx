import type { ReactNode } from "react";
import { Tooltip } from "antd";

export const SOURCE_HELP: Record<string, string> = {
  ai: "AI: assigned using optional OpenAI analysis of the photo thumbnail.",
  clip: "Matched locally using CLIP or SigLIP image and text similarity.",
  cluster: "Grouped locally with visually similar photos.",
  rule: "Assigned by a sorting rule.",
  date: "Assigned using the photo capture date, or file date when unavailable.",
  duplicate: "Duplicate: another file was selected as the original to keep.",
  quality: "Assigned by photo quality checks and recommendation ratings.",
  manual: "You manually changed this photo's destination.",
  faces: "Assigned using local face recognition.",
  appearance: "Suggested person match from appearance; the face could not confirm identity.",
};

export function InfoBadge({ message, children, className }: { message: string; children: ReactNode; className?: string }) {
  return <Tooltip title={message} trigger={["hover", "focus"]}>
    <span tabIndex={0} aria-label={message} className={className}>{children}</span>
  </Tooltip>;
}

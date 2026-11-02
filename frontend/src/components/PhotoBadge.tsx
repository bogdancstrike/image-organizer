import { Children, isValidElement, type ReactNode } from "react";
import { Tag, Tooltip, type TagProps } from "antd";

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

export function badgeText(node: ReactNode): string {
  return Children.toArray(node).map(child => isValidElement<{children?:ReactNode}>(child) ? badgeText(child.props.children) : String(child)).join(" ").replace(/\s+/g," ").trim();
}

export function tagExplanation(label: string): string {
  const text=label.toLowerCase();
  if(text.includes("ai assist")) return SOURCE_HELP.ai;
  if(text.includes("ai names")) return "Optional OpenAI analysis suggests names for locally discovered photo groups.";
  if(text.includes("connected")) return "An OpenAI key is configured. Optional AI requests run only when you enable those features.";
  if(text.includes("no openai") || text.startsWith("off")) return "Optional OpenAI features are unavailable until an API key is configured.";
  if(text.includes("cpu")) return "Local analysis uses the CPU. GPU embedding acceleration can be selected in server configuration.";
  if(text.includes("gpu")) return "CLIP/SigLIP embeddings run locally on an NVIDIA GPU; other analysis still uses the CPU.";
  if(text.includes("clip")) return "Local image/text embedding model used for visual matching and semantic search.";
  if(text.includes("built-in")) return "A category preset included with the app. You can edit it or restore its defaults.";
  if(text.includes("edited")) return "This preset has changes made by you.";
  if(text.includes("in use")) return "This category set is selected for the next sort.";
  if(text.includes("mine")) return "A custom category set created by you.";
  if(text.includes("undone")) return "The Apply operation was reversed and files were returned to their source locations.";
  return `Status: ${label}.`;
}

export function ExplainedTag({ children, ...props }: TagProps) {
  const help=props.title ?? tagExplanation(badgeText(children));
  return <Tooltip title={help} trigger={["hover","focus"]}><Tag {...props} title={undefined} tabIndex={0} aria-label={help}
    onKeyDown={event=>{if(props.onClick && (event.key==="Enter"||event.key===" ")){event.preventDefault();event.currentTarget.click();}}}>{children}</Tag></Tooltip>;
}

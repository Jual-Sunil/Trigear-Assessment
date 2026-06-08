import type { HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export interface EmailClassificationChipProps {
  classification: string | null;
  size?: "xs" | "sm";
  className?: string;
}

const STYLES: Record<string, string> = {
  Work:              "bg-indigo-500/15 text-indigo-300 ring-indigo-500/20",
  Interview:         "bg-sky-500/15 text-sky-300 ring-sky-500/20",
  "Job Opportunity": "bg-emerald-500/15 text-emerald-300 ring-emerald-500/20",
  Finance:           "bg-amber-500/15 text-amber-300 ring-amber-500/20",
  Personal:          "bg-violet-500/15 text-violet-300 ring-violet-500/20",
  Promotion:         "bg-zinc-500/15 text-zinc-400 ring-zinc-500/20",
  Newsletter:        "bg-zinc-500/10 text-zinc-500 ring-zinc-500/10",
  Spam:              "bg-rose-500/15 text-rose-400 ring-rose-500/20",
  Other:             "bg-zinc-500/10 text-zinc-500 ring-zinc-500/10",
};

export function EmailClassificationChip({
  classification,
  size = "sm",
  className,
}: EmailClassificationChipProps) {
  const base =
    "inline-flex items-center font-medium ring-1 ring-inset rounded-full select-none whitespace-nowrap";
  const sizing = size === "xs"
    ? "text-[10px] px-1.5 py-px leading-4"
    : "text-[11px] px-2 py-0.5 leading-4";

  if (!classification) {
    return (
      <span
        className={cn(base, sizing, "bg-zinc-800/60 text-zinc-600 ring-zinc-700/40", className)}
      >
        —
      </span>
    );
  }

  const style = STYLES[classification] ?? "bg-zinc-500/10 text-zinc-400 ring-zinc-500/10";

  return (
    <span className={cn(base, sizing, style, className)}>
      {classification}
    </span>
  );
}

export default EmailClassificationChip;

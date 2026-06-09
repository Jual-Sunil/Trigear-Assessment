import { cn } from "../../lib/utils";

export interface EmailPriorityChipProps {
  priorityScore: number | null;
  size?: "xs" | "sm";
  className?: string;
}

interface Tier {
  label: string;
  style: string;
}

function resolveTier(score: number): Tier {
  if (score >= 80) return { label: `${score} · Critical`, style: "bg-rose-500/15 text-rose-400 ring-rose-500/25" };
  if (score >= 60) return { label: `${score} · High`,     style: "bg-amber-500/15 text-amber-400 ring-amber-500/25" };
  if (score >= 40) return { label: `${score} · Medium`,   style: "bg-sky-500/15 text-sky-400 ring-sky-500/20" };
  return             { label: `${score} · Low`,            style: "bg-zinc-500/10 text-zinc-500 ring-zinc-500/15" };
}

export function EmailPriorityChip({
  priorityScore,
  size = "sm",
  className,
}: EmailPriorityChipProps) {
  const base =
    "inline-flex items-center font-medium ring-1 ring-inset rounded-full select-none whitespace-nowrap tabular-nums";
  const sizing = size === "xs"
    ? "text-[10px] px-1.5 py-px leading-4"
    : "text-[11px] px-2 py-0.5 leading-4";

  if (priorityScore === null || priorityScore === undefined) {
    return (
      <span className={cn(base, sizing, "bg-zinc-800/60 text-zinc-600 ring-zinc-700/40", className)}>
        —
      </span>
    );
  }

  const { label, style } = resolveTier(priorityScore);

  return (
    <span className={cn(base, sizing, style, className)}>
      {label}
    </span>
  );
}

export default EmailPriorityChip;

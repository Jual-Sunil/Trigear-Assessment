import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, ChevronDown } from "lucide-react";
import { updateTask } from "../../services/api/taskApi";
import type { Task } from "../../services/api/types";
import { cn } from "../../lib/utils";

export const TASK_STATUS_OPTIONS = [
  "pending",
  "in_progress",
  "done",
  "cancelled",
] as const;

export type TaskStatus = (typeof TASK_STATUS_OPTIONS)[number];

export interface StatusMeta {
  label: string;
  dot: string;
  text: string;
  bg: string;
  ring: string;
}

export const STATUS_META: Record<string, StatusMeta> = {
  pending: {
    label: "Pending",
    dot: "bg-zinc-600",
    text: "text-zinc-400",
    bg: "bg-zinc-800/60",
    ring: "ring-zinc-700/40",
  },
  in_progress: {
    label: "In Progress",
    dot: "bg-sky-400",
    text: "text-sky-300",
    bg: "bg-sky-500/10",
    ring: "ring-sky-500/20",
  },
  done: {
    label: "Done",
    dot: "bg-emerald-500",
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    ring: "ring-emerald-500/20",
  },
  cancelled: {
    label: "Cancelled",
    dot: "bg-zinc-700",
    text: "text-zinc-600",
    bg: "bg-zinc-800/40",
    ring: "ring-zinc-700/30",
  },
};

export interface TaskStatusSelectProps {
  task: Task;
}

export function TaskStatusSelect({ task }: TaskStatusSelectProps) {
  const queryClient = useQueryClient();

  const { mutate, isPending } = useMutation({
    mutationFn: (status: string) => updateTask(task.id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const current = task.status ?? "pending";
  const meta = STATUS_META[current] ?? STATUS_META.pending;

  return (
    <div className="relative inline-flex items-center">
      <select
        value={current}
        disabled={isPending}
        onChange={(e) => mutate(e.target.value)}
        className={cn(
          "appearance-none cursor-pointer font-medium text-[11px] pl-5 pr-6 py-1 rounded-full ring-1 ring-inset transition-all duration-150",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-white/20",
          "disabled:cursor-wait disabled:opacity-60",
          meta.bg,
          meta.ring,
          meta.text
        )}
      >
        {TASK_STATUS_OPTIONS.map((s) => (
          <option key={s} value={s} className="bg-zinc-900 text-zinc-200">
            {STATUS_META[s]?.label ?? s}
          </option>
        ))}
      </select>

      {/* Left dot or spinner */}
      <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2">
        {isPending ? (
          <Loader2 size={8} className="animate-spin text-zinc-500" />
        ) : (
          <span className={cn("block h-1.5 w-1.5 rounded-full", meta.dot)} />
        )}
      </span>

      {/* Right chevron */}
      <ChevronDown
        size={9}
        className={cn("pointer-events-none absolute right-2 top-1/2 -translate-y-1/2", meta.text)}
      />
    </div>
  );
}

export default TaskStatusSelect;

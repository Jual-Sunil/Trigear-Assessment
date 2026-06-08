import { motion } from "framer-motion";
import { Calendar, Flag, CheckCircle2, Circle, XCircle, Clock } from "lucide-react";
import type { Task } from "../../services/api/types";
import { TaskStatusSelect, STATUS_META } from "./TaskStatusSelect";
import { cn } from "../../lib/utils";

export interface TaskCardProps {
  task: Task;
  index?: number;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

interface PriorityMeta {
  label: string;
  stripe: string;
  chip: string;
  icon: string;
}

function resolvePriority(priority: number | null): PriorityMeta {
  if (priority === null || priority === undefined) {
    return {
      label: "—",
      stripe: "bg-transparent",
      chip: "bg-zinc-800/40 text-zinc-600 ring-zinc-700/30",
      icon: "text-zinc-700",
    };
  }
  if (priority >= 80) return {
    label: `${priority} · Critical`,
    stripe: "bg-rose-500",
    chip: "bg-rose-500/10 text-rose-400 ring-rose-500/20",
    icon: "text-rose-500",
  };
  if (priority >= 60) return {
    label: `${priority} · High`,
    stripe: "bg-amber-400",
    chip: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
    icon: "text-amber-400",
  };
  if (priority >= 40) return {
    label: `${priority} · Medium`,
    stripe: "bg-sky-500",
    chip: "bg-sky-500/10 text-sky-400 ring-sky-500/20",
    icon: "text-sky-400",
  };
  return {
    label: `${priority} · Low`,
    stripe: "bg-zinc-700",
    chip: "bg-zinc-800/40 text-zinc-500 ring-zinc-700/30",
    icon: "text-zinc-600",
  };
}

function StatusIcon({ status }: { status: string | null }) {
  switch (status) {
    case "done":
      return <CheckCircle2 size={15} className="text-emerald-500 flex-shrink-0 mt-0.5" />;
    case "cancelled":
      return <XCircle size={15} className="text-zinc-700 flex-shrink-0 mt-0.5" />;
    case "in_progress":
      return <Clock size={15} className="text-sky-400 flex-shrink-0 mt-0.5" />;
    default:
      return <Circle size={15} className="text-zinc-700 flex-shrink-0 mt-0.5" />;
  }
}

export function TaskCard({ task, index = 0 }: TaskCardProps) {
  const priority = resolvePriority(task.priority);
  const isActive = task.status !== "done" && task.status !== "cancelled";
  const isDone = task.status === "done";
  const isCancelled = task.status === "cancelled";
  const isOverdue =
    isActive &&
    task.due_date !== null &&
    new Date(task.due_date) < new Date();

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.22, delay: index * 0.04 } }}
      whileHover={isActive ? { y: -1, transition: { duration: 0.15 } } : undefined}
      className={cn(
        "group relative rounded-xl border overflow-hidden transition-shadow duration-200",
        isDone || isCancelled
          ? "border-white/[0.04] bg-white/[0.01] opacity-60"
          : isOverdue
          ? "border-rose-500/25 bg-rose-500/[0.03] shadow-[0_0_0_1px_rgba(239,68,68,0.1)]"
          : "border-white/[0.07] bg-white/[0.02] hover:shadow-[0_4px_20px_rgba(0,0,0,0.4)]"
      )}
    >
      {/* Priority stripe */}
      <span
        className={cn(
          "absolute left-0 top-0 h-full w-[2px]",
          isActive ? priority.stripe : "bg-transparent"
        )}
      />

      <div className="pl-4 pr-4 pt-4 pb-4">
        {/* Title row */}
        <div className="flex items-start gap-2.5 mb-2.5">
          <StatusIcon status={task.status} />
          <h3
            className={cn(
              "text-[13.5px] font-semibold leading-snug flex-1 min-w-0",
              isDone
                ? "line-through text-zinc-600 decoration-zinc-700"
                : isCancelled
                ? "line-through text-zinc-700 decoration-zinc-800"
                : "text-zinc-100"
            )}
          >
            {task.title ?? "(Untitled)"}
          </h3>
        </div>

        {/* Description */}
        {task.description && !isDone && !isCancelled && (
          <p className="text-[12px] text-zinc-500 leading-[1.55] mb-3 line-clamp-2 pl-[23px]">
            {task.description}
          </p>
        )}

        {/* Divider */}
        <div className="border-t border-white/[0.05] mt-3 pt-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            {/* Left meta */}
            <div className="flex items-center gap-3 flex-wrap">
              {/* Due date */}
              <div className="flex items-center gap-1">
                <Calendar
                  size={11}
                  className={isOverdue ? "text-rose-500" : "text-zinc-700"}
                />
                <span
                  className={cn(
                    "text-[11px] tabular-nums",
                    isOverdue
                      ? "text-rose-400 font-semibold"
                      : "text-zinc-600 font-medium"
                  )}
                >
                  {formatDate(task.due_date)}
                </span>
              </div>

              {/* Priority badge */}
              {task.priority !== null && task.priority !== undefined && (
                <div className="flex items-center gap-1">
                  <Flag size={10} className={cn(priority.icon)} />
                  <span
                    className={cn(
                      "inline-flex items-center text-[10.5px] font-semibold px-1.5 py-0.5 rounded-full ring-1 ring-inset leading-4",
                      priority.chip
                    )}
                  >
                    {priority.label}
                  </span>
                </div>
              )}
            </div>

            {/* Status select */}
            <TaskStatusSelect task={task} />
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default TaskCard;

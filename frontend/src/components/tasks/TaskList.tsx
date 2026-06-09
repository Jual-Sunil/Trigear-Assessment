import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { CheckSquare, ChevronDown } from "lucide-react";
import { fetchTasks } from "../../services/api/taskApi";
import type { Task, TaskListResponse } from "../../services/api/types";
import { TaskCard } from "./TaskCard";
import { STATUS_META } from "./TaskStatusSelect";
import { cn } from "../../lib/utils";

// ── Sorting (preserved exactly) ───────────────────────────────────────────────

function sortTasks(tasks: Task[]): Task[] {
  return [...tasks].sort((a, b) => {
    const pa = a.priority ?? -1;
    const pb = b.priority ?? -1;
    if (pb !== pa) return pb - pa;
    const da = a.due_date ? new Date(a.due_date).getTime() : Infinity;
    const db = b.due_date ? new Date(b.due_date).getTime() : Infinity;
    return da - db;
  });
}

// ── Filter config ─────────────────────────────────────────────────────────────

const STATUS_TABS = [
  { value: "all",         label: "All" },
  { value: "pending",     label: "Pending" },
  { value: "in_progress", label: "In Progress" },
  { value: "done",        label: "Done" },
  { value: "cancelled",   label: "Cancelled" },
] as const;

type TabValue = (typeof STATUS_TABS)[number]["value"];

const SORT_OPTIONS = [
  { value: "priority", label: "Priority" },
  { value: "due_date", label: "Due Date" },
  { value: "title",    label: "Title" },
] as const;

type SortValue = (typeof SORT_OPTIONS)[number]["value"];

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 h-[118px]">
      <div className="flex items-start gap-2.5 mb-3">
        <div className="h-[15px] w-[15px] rounded-full bg-white/[0.06] animate-pulse flex-shrink-0 mt-0.5" />
        <div className="h-3.5 w-3/5 rounded-full bg-white/[0.07] animate-pulse" />
      </div>
      <div className="pl-[23px] space-y-2 mb-3">
        <div className="h-2.5 w-4/5 rounded-full bg-white/[0.04] animate-pulse" />
        <div className="h-2.5 w-2/3 rounded-full bg-white/[0.04] animate-pulse" />
      </div>
      <div className="border-t border-white/[0.05] pt-3 flex items-center justify-between">
        <div className="flex gap-3">
          <div className="h-3 w-16 rounded-full bg-white/[0.04] animate-pulse" />
          <div className="h-4 w-20 rounded-full bg-white/[0.05] animate-pulse" />
        </div>
        <div className="h-5 w-24 rounded-full bg-white/[0.05] animate-pulse" />
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-20 text-center">
      <span className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/[0.07] mb-5">
        <CheckSquare size={22} className="text-zinc-600" />
      </span>
      <p className="text-sm font-semibold text-zinc-400 mb-1">
        {filtered ? "No tasks match this filter" : "No tasks yet"}
      </p>
      <p className="text-xs text-zinc-600 max-w-[200px] leading-relaxed">
        {filtered
          ? "Try a different status filter or sort order."
          : "Tasks extracted from your emails will appear here."}
      </p>
    </div>
  );
}

// ── Sort helper ───────────────────────────────────────────────────────────────

function applySortAndFilter(tasks: Task[], tab: TabValue, sort: SortValue): Task[] {
  let filtered = tab === "all" ? tasks : tasks.filter((t) => t.status === tab);

  if (sort === "priority") return sortTasks(filtered);

  if (sort === "due_date") {
    return [...filtered].sort((a, b) => {
      const da = a.due_date ? new Date(a.due_date).getTime() : Infinity;
      const db = b.due_date ? new Date(b.due_date).getTime() : Infinity;
      return da - db;
    });
  }

  if (sort === "title") {
    return [...filtered].sort((a, b) =>
      (a.title ?? "").localeCompare(b.title ?? "")
    );
  }

  return filtered;
}

// ── Tab button ────────────────────────────────────────────────────────────────

function Tab({
  tab,
  active,
  count,
  onClick,
}: {
  tab: (typeof STATUS_TABS)[number];
  active: boolean;
  count?: number;
  onClick: () => void;
}) {
  const meta = tab.value !== "all" ? STATUS_META[tab.value] : null;

  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 text-[11.5px] font-semibold px-3 py-1.5 rounded-lg transition-all duration-150 focus:outline-none focus-visible:ring-1 focus-visible:ring-white/20",
        active
          ? "bg-white/[0.09] text-zinc-100"
          : "text-zinc-600 hover:text-zinc-400 hover:bg-white/[0.04]"
      )}
    >
      {meta && (
        <span className={cn("h-1.5 w-1.5 rounded-full flex-shrink-0", meta.dot)} />
      )}
      {tab.label}
      {count !== undefined && (
        <span
          className={cn(
            "text-[10px] tabular-nums px-1.5 py-0.5 rounded-full font-semibold",
            active ? "bg-white/[0.12] text-zinc-300" : "bg-white/[0.04] text-zinc-700"
          )}
        >
          {count}
        </span>
      )}
    </button>
  );
}

// ── List ──────────────────────────────────────────────────────────────────────

export function TaskList() {
  const [activeTab, setActiveTab] = useState<TabValue>("all");
  const [sort, setSort] = useState<SortValue>("priority");

  const { data, isLoading, isError } = useQuery<TaskListResponse>({
    queryKey: ["tasks"],
    queryFn: fetchTasks,
  });

  const allTasks = data ? sortTasks(data.items) : [];
  const displayTasks = data ? applySortAndFilter(allTasks, activeTab, sort) : [];

  const countFor = (tab: TabValue) =>
    tab === "all"
      ? allTasks.length
      : allTasks.filter((t) => t.status === tab).length;

  const isFiltered = activeTab !== "all";

  if (isError) {
    return (
      <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
        Failed to load tasks. Please refresh.
      </div>
    );
  }

  return (
    <div>
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        {/* Status tabs */}
        <div className="flex items-center gap-0.5 flex-wrap">
          {STATUS_TABS.map((tab) => (
            <Tab
              key={tab.value}
              tab={tab}
              active={activeTab === tab.value}
              count={isLoading ? undefined : countFor(tab.value)}
              onClick={() => setActiveTab(tab.value)}
            />
          ))}
        </div>

        {/* Sort */}
        <div className="relative">
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortValue)}
            className="appearance-none cursor-pointer bg-white/[0.04] hover:bg-white/[0.07] border border-white/[0.08] rounded-lg text-[11.5px] text-zinc-400 pl-3 pr-7 py-1.5 transition-colors duration-150 focus:outline-none focus:ring-1 focus:ring-white/20"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value} className="bg-zinc-900 text-zinc-200">
                Sort: {o.label}
              </option>
            ))}
          </select>
          <ChevronDown
            size={10}
            className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-600"
          />
        </div>
      </div>

      {/* Grid */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${activeTab}-${sort}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: { duration: 0.2 } }}
          exit={{ opacity: 0, transition: { duration: 0.1 } }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
        >
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))
          ) : displayTasks.length === 0 ? (
            <EmptyState filtered={isFiltered} />
          ) : (
            displayTasks.map((task, i) => (
              <TaskCard key={task.id} task={task} index={i} />
            ))
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

export default TaskList;

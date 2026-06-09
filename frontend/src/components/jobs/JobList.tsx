import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Briefcase, ChevronDown } from "lucide-react";
import { fetchJobs } from "../../services/api/jobApi";
import type { JobListResponse, JobOpportunity } from "../../services/api/types";
import { JobCard } from "./JobCard";
import { cn } from "../../lib/utils";

function sortJobs(jobs: JobOpportunity[]): JobOpportunity[] {
  return [...jobs].sort((a, b) => {
    const da = a.deadline ? new Date(a.deadline).getTime() : Infinity;
    const db = b.deadline ? new Date(b.deadline).getTime() : Infinity;
    return da - db;
  });
}

function isPast(iso: string | null): boolean {
  if (!iso) return false;
  return new Date(iso) < new Date();
}

// ── Filter config ─────────────────────────────────────────────────────────────

const FILTER_TABS = [
  { value: "active",  label: "Active" },
  { value: "all",     label: "All" },
  { value: "expired", label: "Expired" },
] as const;

type FilterTab = (typeof FILTER_TABS)[number]["value"];

const SORT_OPTIONS = [
  { value: "deadline", label: "Deadline" },
  { value: "company",  label: "Company" },
  { value: "role",     label: "Role" },
] as const;

type SortOption = (typeof SORT_OPTIONS)[number]["value"];

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 h-[200px] flex flex-col gap-3">
      <div className="flex items-start gap-2.5">
        <div className="w-9 h-9 rounded-lg bg-white/[0.05] animate-pulse flex-shrink-0" />
        <div className="flex-1 space-y-1.5">
          <div className="h-2.5 w-1/3 rounded-full bg-white/[0.05] animate-pulse" />
          <div className="h-3.5 w-3/5 rounded-full bg-white/[0.07] animate-pulse" />
        </div>
      </div>
      <div className="border-t border-white/[0.05]" />
      <div className="space-y-2">
        <div className="h-2.5 w-2/5 rounded-full bg-white/[0.04] animate-pulse" />
        <div className="h-2.5 w-1/3 rounded-full bg-white/[0.04] animate-pulse" />
        <div className="h-2.5 w-2/5 rounded-full bg-white/[0.04] animate-pulse" />
      </div>
      <div className="mt-auto h-7 w-24 rounded-lg bg-white/[0.05] animate-pulse" />
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-20 text-center">
      <span className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/[0.07] mb-5">
        <Briefcase size={22} className="text-zinc-600" />
      </span>
      <p className="text-sm font-semibold text-zinc-400 mb-1">
        {filtered ? "No jobs match this filter" : "No job opportunities found"}
      </p>
      <p className="text-xs text-zinc-600 max-w-[210px] leading-relaxed">
        {filtered
          ? "Try switching to All to see every opportunity."
          : "Job opportunities extracted from your emails will appear here."}
      </p>
    </div>
  );
}

// ── Tab button ────────────────────────────────────────────────────────────────

function Tab({
  label,
  active,
  count,
  onClick,
}: {
  label: string;
  active: boolean;
  count?: number;
  onClick: () => void;
}) {
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
      {label}
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

export function JobList() {
  const [activeTab, setActiveTab] = useState<FilterTab>("active");
  const [sort, setSort] = useState<SortOption>("deadline");

  const { data, isLoading, isError } = useQuery<JobListResponse>({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
  });

  const sorted = data ? sortJobs(data.items) : [];

  const filtered = sorted.filter((job) => {
    if (activeTab === "active") return !isPast(job.deadline);
    if (activeTab === "expired") return isPast(job.deadline);
    return true;
  });

  const display = [...filtered].sort((a, b) => {
    if (sort === "company")
      return (a.company ?? "").localeCompare(b.company ?? "");
    if (sort === "role")
      return (a.role ?? "").localeCompare(b.role ?? "");
    // deadline — already sorted
    const da = a.deadline ? new Date(a.deadline).getTime() : Infinity;
    const db = b.deadline ? new Date(b.deadline).getTime() : Infinity;
    return da - db;
  });

  const countFor = (tab: FilterTab) => {
    if (!data) return undefined;
    if (tab === "active") return sorted.filter((j) => !isPast(j.deadline)).length;
    if (tab === "expired") return sorted.filter((j) => isPast(j.deadline)).length;
    return sorted.length;
  };

  if (isError) {
    return (
      <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
        Failed to load job opportunities. Please refresh.
      </div>
    );
  }

  return (
    <div>
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        <div className="flex items-center gap-0.5">
          {FILTER_TABS.map((tab) => (
            <Tab
              key={tab.value}
              label={tab.label}
              active={activeTab === tab.value}
              count={isLoading ? undefined : countFor(tab.value)}
              onClick={() => setActiveTab(tab.value)}
            />
          ))}
        </div>

        <div className="relative">
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortOption)}
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
            Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
          ) : display.length === 0 ? (
            <EmptyState filtered={activeTab !== "all"} />
          ) : (
            display.map((job, i) => (
              <JobCard key={job.id} job={job} index={i} />
            ))
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

export default JobList;

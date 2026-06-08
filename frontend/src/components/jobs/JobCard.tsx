import { motion } from "framer-motion";
import {
  Building2,
  MapPin,
  DollarSign,
  Calendar,
  ExternalLink,
  Briefcase,
  AlertCircle,
} from "lucide-react";
import type { JobOpportunity } from "../../services/api/types";
import { cn } from "../../lib/utils";

export interface JobCardProps {
  job: JobOpportunity;
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

function isPastDeadline(iso: string | null): boolean {
  if (!iso) return false;
  return new Date(iso) < new Date();
}

function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  const diff = new Date(iso).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function DeadlineBadge({ deadline }: { deadline: string | null }) {
  if (!deadline) return null;
  const expired = isPastDeadline(deadline);
  const days = daysUntil(deadline);
  const urgent = !expired && days !== null && days <= 7;

  if (expired) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full ring-1 ring-inset bg-zinc-800/60 text-zinc-600 ring-zinc-700/40">
        Expired
      </span>
    );
  }

  if (urgent) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full ring-1 ring-inset bg-amber-500/10 text-amber-400 ring-amber-500/20">
        <AlertCircle size={8} />
        {days}d left
      </span>
    );
  }

  return null;
}

function CompanyInitial({ company }: { company: string | null }) {
  const letter = company ? company.trim()[0].toUpperCase() : "?";
  return (
    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-white/[0.05] border border-white/[0.08] flex items-center justify-center">
      <span className="text-[14px] font-bold text-zinc-400">{letter}</span>
    </div>
  );
}

export function JobCard({ job, index = 0 }: JobCardProps) {
  const expired = isPastDeadline(job.deadline);
  const days = daysUntil(job.deadline);
  const urgent = !expired && days !== null && days <= 7;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.22, delay: index * 0.05 } }}
      whileHover={!expired ? { y: -2, transition: { duration: 0.15 } } : undefined}
      className={cn(
        "group relative flex flex-col rounded-xl border overflow-hidden transition-shadow duration-200",
        expired
          ? "border-white/[0.04] bg-white/[0.01] opacity-50"
          : urgent
          ? "border-amber-500/20 bg-amber-500/[0.02] hover:shadow-[0_4px_24px_rgba(0,0,0,0.5)]"
          : "border-white/[0.07] bg-white/[0.02] hover:border-white/[0.12] hover:shadow-[0_4px_24px_rgba(0,0,0,0.5)]"
      )}
    >
      {/* Top accent stripe for urgent */}
      {urgent && (
        <span className="absolute top-0 left-0 right-0 h-[2px] bg-amber-400/60 rounded-t-xl" />
      )}

      <div className="flex flex-col flex-1 p-4 gap-3">
        {/* Company + role header */}
        <div className="flex items-start gap-2.5">
          <CompanyInitial company={job.company} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
              <span className="text-[11px] font-medium text-zinc-500 truncate">
                {job.company ?? "Unknown Company"}
              </span>
              <DeadlineBadge deadline={job.deadline} />
            </div>
            <h3
              className={cn(
                "text-[13.5px] font-semibold leading-snug",
                expired ? "text-zinc-600" : "text-zinc-100"
              )}
              title={job.role ?? ""}
            >
              {job.role ?? "Untitled Role"}
            </h3>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-white/[0.05]" />

        {/* Meta row */}
        <div className="flex flex-col gap-1.5">
          {job.location && (
            <div className="flex items-center gap-1.5">
              <MapPin size={11} className="text-zinc-700 flex-shrink-0" />
              <span className="text-[11.5px] text-zinc-500 truncate">{job.location}</span>
            </div>
          )}

          {job.salary && (
            <div className="flex items-center gap-1.5">
              <DollarSign size={11} className="text-zinc-700 flex-shrink-0" />
              <span className="text-[11.5px] text-zinc-500 truncate">{job.salary}</span>
            </div>
          )}

          <div className="flex items-center gap-1.5">
            <Calendar
              size={11}
              className={cn(
                "flex-shrink-0",
                expired ? "text-zinc-700" : urgent ? "text-amber-500" : "text-zinc-700"
              )}
            />
            <span
              className={cn(
                "text-[11.5px] tabular-nums",
                expired
                  ? "text-zinc-700"
                  : urgent
                  ? "text-amber-400 font-semibold"
                  : "text-zinc-500"
              )}
            >
              {expired ? "Expired · " : "Deadline · "}
              {formatDate(job.deadline)}
            </span>
          </div>
        </div>

        {/* Apply button pushed to bottom */}
        <div className="mt-auto pt-1">
          {job.apply_link ? (
            <a
              href={job.apply_link}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => expired && e.preventDefault()}
              className={cn(
                "inline-flex items-center gap-1.5 text-[11.5px] font-semibold px-3 py-1.5 rounded-lg transition-all duration-150",
                expired
                  ? "pointer-events-none bg-white/[0.03] text-zinc-700 cursor-not-allowed"
                  : "bg-white/[0.07] text-zinc-200 hover:bg-white/[0.12] hover:text-white focus:outline-none focus-visible:ring-1 focus-visible:ring-white/20"
              )}
              aria-disabled={expired}
            >
              <Briefcase size={11} />
              Apply Now
              <ExternalLink size={10} className="opacity-60" />
            </a>
          ) : (
            <span className="text-[11px] text-zinc-700 italic">No apply link</span>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default JobCard;

import { motion } from "framer-motion";
import { Building2, Video, ExternalLink, Clock } from "lucide-react";
import type { Interview } from "../../services/api/types";
import { cn } from "../../lib/utils";

export interface InterviewCardProps {
  interview: Interview;
  index?: number;
}

function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return null;
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFullDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

// Calendar visual — shows month abbrev + day number
function CalendarBlock({
  iso,
  isPast,
  isToday,
  isTomorrow,
}: {
  iso: string | null;
  isPast: boolean;
  isToday: boolean;
  isTomorrow: boolean;
}) {
  const accentBg = isPast
    ? "bg-zinc-800/60 border-zinc-700/40"
    : isToday
    ? "bg-rose-500/20 border-rose-500/30"
    : isTomorrow
    ? "bg-amber-500/15 border-amber-500/25"
    : "bg-indigo-500/15 border-indigo-500/25";

  const dayColor = isPast
    ? "text-zinc-600"
    : isToday
    ? "text-rose-300"
    : isTomorrow
    ? "text-amber-300"
    : "text-indigo-300";

  const monthColor = isPast ? "text-zinc-700" : isToday ? "text-rose-500" : isTomorrow ? "text-amber-500" : "text-indigo-500";

  if (!iso) {
    return (
      <div className="flex-shrink-0 w-12 h-14 rounded-xl border bg-zinc-800/40 border-zinc-700/30 flex flex-col items-center justify-center gap-0.5">
        <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-700">—</span>
        <span className="text-[20px] font-bold leading-none text-zinc-700">—</span>
      </div>
    );
  }

  const d = new Date(iso);
  const month = d.toLocaleDateString(undefined, { month: "short" }).toUpperCase();
  const day = d.getDate();

  return (
    <div
      className={cn(
        "flex-shrink-0 w-12 h-14 rounded-xl border flex flex-col items-center justify-center gap-0.5",
        accentBg
      )}
    >
      <span className={cn("text-[9px] font-bold uppercase tracking-widest", monthColor)}>
        {month}
      </span>
      <span className={cn("text-[22px] font-bold leading-none tabular-nums", dayColor)}>
        {day}
      </span>
    </div>
  );
}

interface CountdownBadgeProps {
  days: number | null;
  isToday: boolean;
  isTomorrow: boolean;
  isPast: boolean;
}

function CountdownBadge({ days, isToday, isTomorrow, isPast }: CountdownBadgeProps) {
  if (isPast) {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full ring-1 ring-inset bg-zinc-800/60 text-zinc-600 ring-zinc-700/40">
        Past
      </span>
    );
  }
  if (isToday) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ring-1 ring-inset bg-rose-500/15 text-rose-400 ring-rose-500/25">
        <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-pulse" />
        Today
      </span>
    );
  }
  if (isTomorrow) {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full ring-1 ring-inset bg-amber-500/15 text-amber-400 ring-amber-500/25">
        Tomorrow
      </span>
    );
  }
  if (days !== null && days <= 7) {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full ring-1 ring-inset bg-amber-500/10 text-amber-500 ring-amber-500/20">
        In {days}d
      </span>
    );
  }
  if (days !== null) {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full ring-1 ring-inset bg-indigo-500/10 text-indigo-400 ring-indigo-500/20">
        In {days}d
      </span>
    );
  }
  return null;
}

export function InterviewCard({ interview, index = 0 }: InterviewCardProps) {
  const days = daysUntil(interview.interview_date);
  const isPast = days === null && interview.interview_date !== null;
  const noDate = interview.interview_date === null;
  const isToday = days === 0;
  const isTomorrow = days === 1;

  const borderStyle = isPast || noDate
    ? "border-white/[0.04] bg-white/[0.01]"
    : isToday
    ? "border-rose-500/25 bg-rose-500/[0.025] hover:shadow-[0_4px_24px_rgba(0,0,0,0.5)]"
    : isTomorrow
    ? "border-amber-500/20 bg-amber-500/[0.02] hover:shadow-[0_4px_24px_rgba(0,0,0,0.5)]"
    : "border-white/[0.07] bg-white/[0.02] hover:border-white/[0.12] hover:shadow-[0_4px_24px_rgba(0,0,0,0.5)]";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.22, delay: index * 0.05 } }}
      whileHover={!isPast ? { y: -2, transition: { duration: 0.15 } } : undefined}
      className={cn(
        "group relative rounded-xl border overflow-hidden flex flex-col transition-shadow duration-200",
        borderStyle,
        (isPast || noDate) && "opacity-55"
      )}
    >
      {/* Today stripe */}
      {isToday && (
        <span className="absolute top-0 left-0 right-0 h-[2px] bg-rose-500/70 rounded-t-xl" />
      )}

      <div className="p-4 flex flex-col gap-3 flex-1">
        {/* Header: calendar block + company/role */}
        <div className="flex items-start gap-3">
          <CalendarBlock
            iso={interview.interview_date}
            isPast={isPast}
            isToday={isToday}
            isTomorrow={isTomorrow}
          />

          <div className="flex-1 min-w-0">
            {/* Company */}
            <div className="flex items-center gap-1 mb-0.5">
              <Building2 size={10} className="text-zinc-700 flex-shrink-0" />
              <span className="text-[11px] font-medium text-zinc-500 truncate">
                {interview.company ?? "Unknown Company"}
              </span>
            </div>

            {/* Role */}
            <h3
              className={cn(
                "text-[13.5px] font-semibold leading-snug line-clamp-2",
                isPast ? "text-zinc-600" : "text-zinc-100"
              )}
              title={interview.role ?? ""}
            >
              {interview.role ?? "Untitled Role"}
            </h3>

            {/* Countdown */}
            <div className="mt-1.5">
              <CountdownBadge
                days={days}
                isToday={isToday}
                isTomorrow={isTomorrow}
                isPast={isPast}
              />
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-white/[0.05]" />

        {/* Time row */}
        <div className="flex items-center gap-1.5">
          <Clock size={11} className={isPast ? "text-zinc-700" : "text-zinc-600"} />
          <span className={cn("text-[11.5px] tabular-nums", isPast ? "text-zinc-700" : "text-zinc-500")}>
            {interview.interview_date ? (
              <>
                <span className={cn("font-semibold", !isPast && "text-zinc-300")}>
                  {formatTime(interview.interview_date)}
                </span>
                <span className="mx-1.5 text-zinc-700">·</span>
                {formatFullDate(interview.interview_date)}
              </>
            ) : (
              <span className="text-zinc-700 italic">No date scheduled</span>
            )}
          </span>
        </div>

        {/* Join button */}
        <div className="mt-auto pt-1">
          {interview.meeting_link ? (
            <a
              href={interview.meeting_link}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => isPast && e.preventDefault()}
              aria-disabled={isPast}
              className={cn(
                "inline-flex items-center gap-1.5 text-[11.5px] font-semibold px-3 py-1.5 rounded-lg transition-all duration-150 focus:outline-none focus-visible:ring-1 focus-visible:ring-white/20",
                isPast
                  ? "pointer-events-none bg-white/[0.03] text-zinc-700 cursor-not-allowed"
                  : isToday
                  ? "bg-rose-500/20 text-rose-300 hover:bg-rose-500/30"
                  : "bg-white/[0.07] text-zinc-200 hover:bg-white/[0.12] hover:text-white"
              )}
            >
              <Video size={11} />
              Join Meeting
              <ExternalLink size={9} className="opacity-50" />
            </a>
          ) : (
            <span className="text-[11px] text-zinc-700 italic">No meeting link</span>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default InterviewCard;

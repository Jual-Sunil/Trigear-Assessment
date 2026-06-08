// ImportantEmailsWidget.tsx - Ensure widget has distinct box and full width
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Star, ChevronRight, Inbox } from "lucide-react";
import { fetchEmails } from "../../services/api/emailApi";
import type { EmailSummary } from "../../services/api/types";
import { EmailClassificationChip } from "../emails/EmailClassificationChip";
import { EmailPriorityChip } from "../emails/EmailPriorityChip";

const DISPLAY_LIMIT = 10;
const PRIORITY_MIN = 70;

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

// ─── Skeleton ───────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <div className="flex items-start gap-3 px-5 py-4 border-b border-white/[0.06]">
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-2">
          <div className="h-3 w-2/5 rounded-full bg-white/[0.08] animate-pulse" />
          <div className="h-4 w-16 rounded-full bg-white/[0.08] animate-pulse" />
        </div>
        <div className="h-2.5 w-1/4 rounded-full bg-white/[0.06] animate-pulse" />
        <div className="h-2.5 w-3/4 rounded-full bg-white/[0.06] animate-pulse" />
      </div>
      <div className="h-4 w-4 rounded bg-white/[0.06] animate-pulse mt-0.5 flex-shrink-0" />
    </div>
  );
}

// ─── Priority dot ────────────────────────────────────────────────────────────

function PriorityDot({ score }: { score: number | undefined }) {
  const s = score ?? 0;
  const color =
    s >= 90
      ? "bg-rose-500"
      : s >= 80
      ? "bg-amber-400"
      : s >= 70
      ? "bg-sky-400"
      : "bg-zinc-600";
  return (
    <span
      className={`mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0 ${color}`}
    />
  );
}

// ─── Email row ───────────────────────────────────────────────────────────────

const rowVariants = {
  hidden: { opacity: 0, x: -6 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.25 } },
};

function EmailRow({ email }: { email: EmailSummary }) {
  const subject = email.subject ?? "(No subject)";
  const sender = email.sender_name ?? email.sender_email;

  return (
    <motion.div variants={rowVariants}>
      <RouterLink
        to={`/emails/${email.id}`}
        className="group flex items-start gap-3 px-5 py-4 border-b border-white/[0.06] hover:bg-white/[0.04] transition-colors duration-150 no-underline"
      >
        <PriorityDot score={email.priority_score} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center flex-wrap gap-1.5 mb-1">
            <span
              className="text-[13px] font-semibold text-zinc-100 truncate max-w-[200px] sm:max-w-[320px] md:max-w-[460px]"
              title={subject}
            >
              {subject}
            </span>
            <EmailClassificationChip classification={email.classification} />
            <EmailPriorityChip priorityScore={email.priority_score} />
          </div>

          <p className="text-[11px] text-zinc-500 mb-0.5 truncate">
            {truncate(sender, 52)}
          </p>

          {email.summary && (
            <p className="text-[11px] text-zinc-600 leading-[1.45] line-clamp-2">
              {email.summary}
            </p>
          )}
        </div>

        <ChevronRight
          size={14}
          className="text-zinc-700 group-hover:text-zinc-400 transition-colors duration-150 mt-1 flex-shrink-0"
        />
      </RouterLink>
    </motion.div>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
      <span className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/[0.08] mb-4">
        <Inbox size={20} className="text-zinc-500" />
      </span>
      <p className="text-sm font-medium text-zinc-400 mb-1">No important emails</p>
      <p className="text-xs text-zinc-600 max-w-[220px]">
        High-priority emails will surface here as they arrive.
      </p>
    </div>
  );
}

// ─── Widget ──────────────────────────────────────────────────────────────────

const listVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.05, delayChildren: 0.1 },
  },
};

export function ImportantEmailsWidget() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["emails", "important", PRIORITY_MIN],
    queryFn: () =>
      fetchEmails({ priority_min: PRIORITY_MIN, page_size: 50, page: 1 }),
  });

  const emails: EmailSummary[] = data
    ? [...data.items]
        .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0))
        .slice(0, DISPLAY_LIMIT)
    : [];

  return (
    <div className="w-full rounded-xl border border-white/[0.12] bg-white/[0.04] overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.08] bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <Star size={14} className="text-amber-400 fill-amber-400" />
          <span className="text-[13px] font-semibold text-zinc-200 tracking-tight">
            Important Emails
          </span>
        </div>

        {!isLoading && !isError && data && (
          <span className="text-[11px] text-zinc-500 tabular-nums">
            {data.total} total · top {Math.min(emails.length, DISPLAY_LIMIT)}
          </span>
        )}
      </div>

      {/* Body */}
      {isError && (
        <div className="px-5 py-4 text-sm text-rose-400 bg-rose-500/5">
          Failed to load emails. Please refresh.
        </div>
      )}

      {!isError && (
        <>
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
          ) : emails.length === 0 ? (
            <EmptyState />
          ) : (
            <AnimatePresence>
              <motion.div
                variants={listVariants}
                initial="hidden"
                animate="visible"
              >
                {emails.map((email) => (
                  <EmailRow key={email.id} email={email} />
                ))}
              </motion.div>
            </AnimatePresence>
          )}
        </>
      )}
    </div>
  );
}

export default ImportantEmailsWidget;
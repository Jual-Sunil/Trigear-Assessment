import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Inbox, ChevronDown, ChevronRight, Search } from "lucide-react";
import { fetchEmails } from "../../services/api/emailApi";
import type { EmailListResponse, EmailListParams, EmailSummary } from "../../services/api/types";
import { EmailClassificationChip } from "../../components/emails/EmailClassificationChip";
import { EmailPriorityChip } from "../../components/emails/EmailPriorityChip";
import { cn } from "../../lib/utils";

const PAGE_SIZE = 20;

const CLASSIFICATIONS = [
  "Work", "Interview", "Job Opportunity", "Finance",
  "Personal", "Promotion", "Newsletter", "Spam", "Other",
];

const PRIORITY_OPTIONS = [
  { label: "Any", value: "" },
  { label: "25+",  value: "25" },
  { label: "50+",  value: "50" },
  { label: "70+",  value: "70" },
  { label: "90+",  value: "90" },
];

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (isToday) return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// ─── Filter Pill ──────────────────────────────────────────────────────────────

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { label: string; value: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none cursor-pointer bg-white/[0.04] hover:bg-white/[0.07] border border-white/[0.08] rounded-lg text-[12px] text-zinc-300 pl-3 pr-7 py-1.5 transition-colors duration-150 focus:outline-none focus:ring-1 focus:ring-white/20"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value} className="bg-zinc-900 text-zinc-200">
            {o.value === "" ? `${label}: All` : `${label}: ${o.label}`}
          </option>
        ))}
      </select>
      <ChevronDown
        size={11}
        className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500"
      />
    </div>
  );
}

// ─── Skeleton Row ─────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <div className="flex items-start gap-3 px-5 py-3.5 border-b border-white/[0.05]">
      <div className="mt-1 h-1.5 w-1.5 rounded-full bg-white/[0.06] flex-shrink-0" />
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-2">
          <div className="h-3 w-2/5 rounded-full bg-white/[0.07] animate-pulse" />
          <div className="h-4 w-14 rounded-full bg-white/[0.05] animate-pulse" />
        </div>
        <div className="h-2.5 w-1/4 rounded-full bg-white/[0.04] animate-pulse" />
        <div className="h-2.5 w-3/4 rounded-full bg-white/[0.04] animate-pulse" />
      </div>
      <div className="h-2.5 w-10 rounded-full bg-white/[0.04] animate-pulse mt-1" />
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-8 text-center">
      <span className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/[0.07] mb-5">
        <Inbox size={22} className="text-zinc-600" />
      </span>
      <p className="text-sm font-semibold text-zinc-400 mb-1">
        {filtered ? "No emails match your filters" : "Your inbox is empty"}
      </p>
      <p className="text-xs text-zinc-600 max-w-[200px] leading-relaxed">
        {filtered
          ? "Try adjusting the classification or priority filter."
          : "Emails will appear here as they arrive."}
      </p>
    </div>
  );
}

// ─── Priority Dot ─────────────────────────────────────────────────────────────

function PriorityDot({ score }: { score: number | undefined }) {
  const s = score ?? 0;
  if (s < 40) return <span className="mt-2 h-1.5 w-1.5 rounded-full bg-zinc-700 flex-shrink-0" />;
  const color = s >= 80 ? "bg-rose-500" : s >= 60 ? "bg-amber-400" : "bg-sky-400";
  return <span className={cn("mt-2 h-1.5 w-1.5 rounded-full flex-shrink-0", color)} />;
}

// ─── Email Row ────────────────────────────────────────────────────────────────

const rowVariants = {
  hidden: { opacity: 0, y: 4 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.22 } },
  exit:   { opacity: 0,         transition: { duration: 0.12 } },
};

function EmailRow({ email, onClick }: { email: EmailSummary; onClick: () => void }) {
  return (
    <motion.button
      variants={rowVariants}
      layout
      onClick={onClick}
      className="group w-full text-left flex items-start gap-3 px-5 py-3.5 border-b border-white/[0.05] hover:bg-white/[0.03] active:bg-white/[0.05] transition-colors duration-100 focus:outline-none focus-visible:ring-1 focus-visible:ring-white/20"
    >
      <PriorityDot score={email.priority_score ?? undefined} />

      <div className="flex-1 min-w-0">
        {/* Sender */}
        <p className="text-[11px] font-medium text-zinc-500 mb-0.5 truncate">
          {email.sender_name ?? email.sender_email}
          {email.sender_name && (
            <span className="text-zinc-700 ml-1">&lt;{email.sender_email}&gt;</span>
          )}
        </p>

        {/* Subject + chips */}
        <div className="flex items-center flex-wrap gap-1.5 mb-1">
          <span className="text-[13.5px] font-semibold text-zinc-100 truncate max-w-[200px] sm:max-w-[340px] md:max-w-[500px]">
            {email.subject ?? "(no subject)"}
          </span>
          {email.classification && (
            <EmailClassificationChip classification={email.classification} size="xs" />
          )}
          {email.priority_score != null && email.priority_score >= 50 && (
            <EmailPriorityChip priorityScore={email.priority_score} size="xs" />
          )}
        </div>

        {/* Snippet */}
        {email.snippet && (
          <p className="text-[12px] text-zinc-600 truncate leading-relaxed">
            {email.snippet}
          </p>
        )}
      </div>

      {/* Date */}
      <div className="flex items-center gap-1 flex-shrink-0 mt-0.5">
        <span className="text-[11px] text-zinc-600 tabular-nums whitespace-nowrap">
          {formatDate(email.received_at)}
        </span>
        <ChevronRight
          size={12}
          className="text-zinc-700 group-hover:text-zinc-500 transition-colors duration-100"
        />
      </div>
    </motion.button>
  );
}

// ─── Pagination ───────────────────────────────────────────────────────────────

function Pager({
  page,
  total,
  pageSize,
  onChange,
}: {
  page: number;
  total: number;
  pageSize: number;
  onChange: (p: number) => void;
}) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-1 pt-4 pb-2">
      <button
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        className="px-3 py-1.5 text-[11px] rounded-lg border border-white/[0.08] text-zinc-400 hover:bg-white/[0.06] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        Previous
      </button>
      <span className="px-3 text-[11px] text-zinc-600 tabular-nums">
        {page} / {totalPages}
      </span>
      <button
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
        className="px-3 py-1.5 text-[11px] rounded-lg border border-white/[0.08] text-zinc-400 hover:bg-white/[0.06] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const listVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04 } },
};

export function Component() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [classification, setClassification] = useState("");
  const [priorityMin, setPriorityMin] = useState("");

  const params: EmailListParams = {
    page,
    page_size: PAGE_SIZE,
    ...(classification ? { classification } : {}),
    ...(priorityMin !== "" ? { priority_min: Number(priorityMin) } : {}),
  };

  const { data, isLoading, isError } = useQuery<EmailListResponse>({
    queryKey: ["emails", params],
    queryFn: () => fetchEmails(params),
  });

  const isFiltered = Boolean(classification || priorityMin);

  function handleFilterChange() {
    setPage(1);
  }

  const classificationOptions = [
    { label: "All", value: "" },
    ...CLASSIFICATIONS.map((c) => ({ label: c, value: c })),
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.3 } }}
      className="min-h-screen bg-[#0a0a0b] text-white max-w-[1100px] mx-auto px-4 py-8 md:px-8"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-[10px] font-semibold tracking-[0.18em] uppercase text-zinc-600 mb-0.5">
            Inbox
          </p>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-50">Emails</h1>
        </div>

        {data && (
          <span className="text-[11px] text-zinc-600 tabular-nums">
            {data.total} email{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        <FilterSelect
          label="Category"
          value={classification}
          options={classificationOptions}
          onChange={(v) => { setClassification(v); handleFilterChange(); }}
        />
        <FilterSelect
          label="Priority"
          value={priorityMin}
          options={PRIORITY_OPTIONS}
          onChange={(v) => { setPriorityMin(v); handleFilterChange(); }}
        />
        {isFiltered && (
          <button
            onClick={() => {
              setClassification("");
              setPriorityMin("");
              handleFilterChange();
            }}
            className="text-[11px] text-zinc-500 hover:text-zinc-300 px-2 py-1.5 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400 mb-4">
          Failed to load emails. Please refresh.
        </div>
      )}

      {/* List panel */}
      <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] overflow-hidden">
        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
        ) : !isError && data?.items.length === 0 ? (
          <EmptyState filtered={isFiltered} />
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={`${page}-${classification}-${priorityMin}`}
              variants={listVariants}
              initial="hidden"
              animate="visible"
            >
              {data?.items.map((email) => (
                <EmailRow
                  key={email.id}
                  email={email}
                  onClick={() => navigate(`/emails/${email.id}`)}
                />
              ))}
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* Pagination */}
      {data && (
        <Pager
          page={page}
          total={data.total}
          pageSize={PAGE_SIZE}
          onChange={setPage}
        />
      )}
    </motion.div>
  );
}

export default Component;

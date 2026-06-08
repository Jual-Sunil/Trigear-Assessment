import { motion } from "framer-motion";
import { Sparkles, AlertCircle } from "lucide-react";
import type { EmailDetail } from "../../services/api/types";
import { EmailClassificationChip } from "./EmailClassificationChip";
import { EmailPriorityChip } from "./EmailPriorityChip";
import { cn } from "../../lib/utils";

export interface EmailSummaryCardProps {
  email: EmailDetail | undefined;
  isLoading: boolean;
}

// ─── Confidence bar ───────────────────────────────────────────────────────────

function ConfidenceBar({ score }: { score: number | null }) {
  if (score === null || score === undefined) return <span className="text-zinc-600 text-[12px]">—</span>;
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-400" : "bg-rose-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] text-zinc-500 tabular-nums">{pct}%</span>
    </div>
  );
}

// ─── Meta row ─────────────────────────────────────────────────────────────────

function MetaRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4 min-h-[28px]">
      <span className="text-[11px] text-zinc-600 font-medium w-32 flex-shrink-0 uppercase tracking-wide">
        {label}
      </span>
      <div className="flex items-center">{children}</div>
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-5 mb-4">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-3.5 w-3.5 rounded bg-white/[0.06] animate-pulse" />
        <div className="h-3 w-24 rounded-full bg-white/[0.06] animate-pulse" />
      </div>
      <div className="space-y-2.5 mb-4">
        {[40, 28, 36].map((w) => (
          <div key={w} className="flex items-center gap-4">
            <div className="h-2.5 w-24 rounded-full bg-white/[0.04] animate-pulse" />
            <div className={`h-4 w-${w} rounded-full bg-white/[0.05] animate-pulse`} style={{ width: `${w * 4}px` }} />
          </div>
        ))}
      </div>
      <div className="border-t border-white/[0.06] pt-3 space-y-2">
        <div className="h-2.5 w-full rounded-full bg-white/[0.04] animate-pulse" />
        <div className="h-2.5 w-4/5 rounded-full bg-white/[0.04] animate-pulse" />
        <div className="h-2.5 w-3/5 rounded-full bg-white/[0.04] animate-pulse" />
      </div>
    </div>
  );
}

// ─── Card ─────────────────────────────────────────────────────────────────────

export function EmailSummaryCard({ email, isLoading }: EmailSummaryCardProps) {
  if (isLoading) return <SkeletonCard />;

  const hasAnyMeta =
    email?.classification != null ||
    email?.confidence_score != null ||
    email?.priority_score != null ||
    email?.is_action_required != null;

  const hasSummary = Boolean(email?.summary);

  if (!hasAnyMeta && !hasSummary) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.28, delay: 0.05 } }}
      className="rounded-xl border border-white/[0.07] bg-white/[0.02] mb-4 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-5 py-3.5 border-b border-white/[0.06]">
        <Sparkles size={13} className="text-indigo-400" />
        <span className="text-[12px] font-semibold text-zinc-300 tracking-tight">
          AI Intelligence
        </span>
        {email?.is_action_required && (
          <span className="ml-auto inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 ring-1 ring-amber-500/20 rounded-full px-2 py-0.5">
            <AlertCircle size={9} />
            Action Required
          </span>
        )}
      </div>

      <div className="px-5 py-4">
        {hasAnyMeta && (
          <div className="space-y-1.5 mb-4">
            {email?.classification != null && (
              <MetaRow label="Category">
                <EmailClassificationChip classification={email.classification} size="sm" />
              </MetaRow>
            )}
            {email?.confidence_score != null && (
              <MetaRow label="Confidence">
                <ConfidenceBar score={email.confidence_score} />
              </MetaRow>
            )}
            {email?.priority_score != null && (
              <MetaRow label="Priority">
                <EmailPriorityChip priorityScore={email.priority_score} size="sm" />
              </MetaRow>
            )}
            {email?.is_action_required != null && !email.is_action_required && (
              <MetaRow label="Action">
                <span className="text-[12px] text-zinc-600 font-medium">Not required</span>
              </MetaRow>
            )}
          </div>
        )}

        {hasSummary && (
          <div className={cn(hasAnyMeta && "border-t border-white/[0.06] pt-3.5")}>
            <p className="text-[12.5px] text-zinc-400 leading-relaxed italic">
              {email!.summary}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default EmailSummaryCard;

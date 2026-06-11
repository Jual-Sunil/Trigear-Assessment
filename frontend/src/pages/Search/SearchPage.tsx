import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Mail,
  CheckSquare,
  Briefcase,
  CalendarDays,
  Sparkles,
  Command,
  Clock,
  ArrowRight,
  Zap,
} from "lucide-react";
import { cn } from "../../lib/utils";

// ── Search tips ───────────────────────────────────────────────────────────────

const TIPS = [
  { icon: <Mail size={13} />, label: "Emails", example: "Q3 report from David" },
  { icon: <CheckSquare size={13} />, label: "Tasks", example: "Review pull request" },
  { icon: <Briefcase size={13} />, label: "Jobs", example: "Senior engineer at Stripe" },
  { icon: <CalendarDays size={13} />, label: "Interviews", example: "Technical round Monday" },
];

const EXAMPLE_QUERIES = [
  "Emails about the product launch",
  "Tasks due this week",
  "Job offers from fintech companies",
  "Upcoming technical interviews",
];

// ── Coming soon badge ─────────────────────────────────────────────────────────

function ComingSoonBanner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.3, delay: 0.15 } }}
      className="flex flex-col items-center text-center px-4"
    >
      <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-3.5 py-1.5 mb-6">
        <Zap size={11} className="text-indigo-400" />
        <span className="text-[11px] font-semibold text-indigo-300 tracking-wide">
          Coming Soon
        </span>
      </div>

      <h2 className="text-[1.1rem] font-semibold text-zinc-300 mb-2 tracking-tight">
        Search is on its way
      </h2>
      <p className="text-[13px] text-zinc-600 max-w-[300px] leading-relaxed">
        AI-powered search across your emails, tasks, jobs, and interviews — launching soon.
      </p>
    </motion.div>
  );
}

// ── Tip card ──────────────────────────────────────────────────────────────────

function TipCard({
  icon,
  label,
  example,
  delay,
}: {
  icon: React.ReactNode;
  label: string;
  example: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.25, delay } }}
      className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3"
    >
      <span className="mt-0.5 flex-shrink-0 text-zinc-600">{icon}</span>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold text-zinc-500 mb-0.5 uppercase tracking-wide">
          {label}
        </p>
        <p className="text-[12px] text-zinc-600 truncate italic">"{example}"</p>
      </div>
    </motion.div>
  );
}

// ── Example query pill ────────────────────────────────────────────────────────

function ExamplePill({ text, delay }: { text: string; delay: number }) {
  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1, transition: { duration: 0.2, delay } }}
      className="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-zinc-600 hover:text-zinc-300 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/[0.1] rounded-full px-3 py-1.5 transition-all duration-150 cursor-default"
      aria-disabled
    >
      <Clock size={10} className="opacity-60" />
      {text}
    </motion.button>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function Component() {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.3 } }}
      className="min-h-screen bg-[#0a0a0b] text-white flex flex-col items-center px-4 pt-16 pb-20 md:pt-24"
    >
      {/* Eyebrow */}
      <motion.div
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0, transition: { duration: 0.25 } }}
        className="flex items-center gap-2 mb-6"
      >
        <Sparkles size={13} className="text-indigo-400" />
        <span className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-600">
          AI Search
        </span>
      </motion.div>

      {/* Heading */}
      <motion.h1
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0, transition: { duration: 0.28, delay: 0.05 } }}
        className="text-2xl md:text-3xl font-semibold tracking-tight text-zinc-100 text-center mb-2"
      >
        Search everything
      </motion.h1>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, transition: { duration: 0.28, delay: 0.1 } }}
        className="text-[13px] text-zinc-600 text-center mb-10"
      >
        Emails, tasks, jobs, and interviews — all in one place.
      </motion.p>

      {/* Search input */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0, transition: { duration: 0.28, delay: 0.08 } }}
        className="w-full max-w-[640px] mb-10"
      >
        <div
          className={cn(
            "relative flex items-center rounded-2xl border transition-all duration-200",
            focused
              ? "border-white/[0.14] bg-white/[0.05] shadow-[0_0_0_3px_rgba(99,102,241,0.12)]"
              : "border-white/[0.08] bg-white/[0.03]"
          )}
        >
          <Search
            size={16}
            className={cn(
              "absolute left-4 transition-colors duration-200",
              focused ? "text-indigo-400" : "text-zinc-600"
            )}
          />

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="Search emails, tasks, jobs, interviews…"
            disabled
            className="w-full bg-transparent text-[14px] text-zinc-300 placeholder-zinc-700 pl-10 pr-16 py-3.5 rounded-2xl focus:outline-none cursor-not-allowed"
          />

          {/* Keyboard hint */}
          <div className="absolute right-3.5 flex items-center gap-1 pointer-events-none">
            <span className="inline-flex items-center gap-0.5 rounded-md border border-white/[0.08] bg-white/[0.04] px-1.5 py-0.5">
              <Command size={9} className="text-zinc-600" />
              <span className="text-[10px] text-zinc-600 font-medium">K</span>
            </span>
          </div>
        </div>
      </motion.div>

      {/* Coming soon banner */}
      <ComingSoonBanner />

      {/* Divider */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, transition: { duration: 0.3, delay: 0.25 } }}
        className="w-full max-w-[640px] flex items-center gap-3 my-10"
      >
        <div className="flex-1 h-px bg-white/[0.05]" />
        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-700">
          What you'll be able to search
        </span>
        <div className="flex-1 h-px bg-white/[0.05]" />
      </motion.div>

      {/* Tip grid */}
      <div className="w-full max-w-[640px] grid grid-cols-1 sm:grid-cols-2 gap-2.5 mb-10">
        {TIPS.map((tip, i) => (
          <TipCard
            key={tip.label}
            icon={tip.icon}
            label={tip.label}
            example={tip.example}
            delay={0.3 + i * 0.06}
          />
        ))}
      </div>

      {/* Example queries */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, transition: { duration: 0.3, delay: 0.5 } }}
        className="w-full max-w-[640px]"
      >
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-700 mb-3 text-center">
          Example queries
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {EXAMPLE_QUERIES.map((q, i) => (
            <ExamplePill key={q} text={q} delay={0.52 + i * 0.05} />
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}

export default Component;

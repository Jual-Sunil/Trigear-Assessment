import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export interface StatCardProps {
  label: string;
  value: number | undefined;
  icon: React.ReactNode;
  isLoading: boolean;
  accentColor?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
}

function TrendBadge({ trend, value }: { trend: "up" | "down" | "neutral"; value?: string }) {
  if (trend === "up") return <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-emerald-400"><TrendingUp size={10} />{value}</span>;
  if (trend === "down") return <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-rose-400"><TrendingDown size={10} />{value}</span>;
  return <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-zinc-600"><Minus size={10} /></span>;
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.04] p-5 h-[110px] animate-pulse">
      <div className="space-y-3">
        <div className="h-3 w-24 rounded-full bg-white/[0.08]" />
        <div className="h-8 w-16 rounded-lg bg-white/[0.08]" />
      </div>
    </div>
  );
}

export function StatCard({ label, value, icon, isLoading, accentColor, trend = "neutral", trendValue }: StatCardProps) {
  if (isLoading) return <SkeletonCard />;

  return (
    <motion.div
      whileHover={{ y: -2, transition: { duration: 0.18 } }}
      className="group relative overflow-hidden rounded-xl border border-white/[0.12] bg-white/[0.05] p-5 shadow-sm hover:shadow-md transition-all duration-200 cursor-default"
      style={accentColor ? ({ "--accent": accentColor } as React.CSSProperties) : undefined}
    >
      {accentColor && (
        <span className="absolute left-0 top-0 h-full w-[3px] rounded-l-xl opacity-80" style={{ background: accentColor }} />
      )}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-semibold tracking-[0.12em] uppercase text-zinc-400">{label}</span>
        <span className="text-zinc-500 group-hover:text-zinc-300 transition-colors duration-200">{icon}</span>
      </div>
      <div className="flex items-end justify-between">
        <span className="text-[2rem] font-bold leading-none tracking-tight tabular-nums text-zinc-50">{value ?? 0}</span>
        <TrendBadge trend={trend} value={trendValue} />
      </div>
    </motion.div>
  );
}
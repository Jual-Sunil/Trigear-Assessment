import { Mail, Star, CheckSquare, CalendarDays, Briefcase } from "lucide-react";
import { motion } from "framer-motion";
import { StatCard } from "./StatCard";
import type { DashboardResponse } from "../../services/api/types";

export interface StatsCardsProps {
  data: DashboardResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}

const STAT_CONFIGS = [
  { key: "total_emails" as const, label: "Total Emails", icon: <Mail size={15} />, accentColor: "#6366f1" },
  { key: "important_emails" as const, label: "Important", icon: <Star size={15} />, accentColor: "#f59e0b" },
  { key: "pending_tasks" as const, label: "Pending Tasks", icon: <CheckSquare size={15} />, accentColor: "#10b981" },
  { key: "upcoming_interviews" as const, label: "Interviews", icon: <CalendarDays size={15} />, accentColor: "#38bdf8" },
  { key: "active_jobs" as const, label: "Active Jobs", icon: <Briefcase size={15} />, accentColor: "#a78bfa" },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.07 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export function StatsCards({ data, isLoading, isError }: StatsCardsProps) {
  if (isError) {
    return (
      <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
        Failed to load dashboard metrics. Please refresh.
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 w-full"
    >
      {STAT_CONFIGS.map((config) => (
        <motion.div key={config.key} variants={itemVariants}>
          <StatCard
            label={config.label}
            value={data?.[config.key]}
            icon={config.icon}
            isLoading={isLoading}
            accentColor={config.accentColor}
          />
        </motion.div>
      ))}
    </motion.div>
  );
}
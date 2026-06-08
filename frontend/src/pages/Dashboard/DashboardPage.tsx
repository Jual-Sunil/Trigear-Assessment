import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { fetchDashboard } from "../../services/api/dashboardApi";
import type { DashboardResponse } from "../../services/api/types";
import { StatsCards } from "../../components/dashboard/StatsCards";
import { ImportantEmailsWidget } from "../../components/dashboard/ImportantEmailsWidget";

const pageVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: [0.25, 0.46, 0.45, 0.94] as const,
    },
  },
};

export function Component() {
  const { data, isLoading, isError } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  const now = new Date();
  const hour = now.getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="visible"
      className="min-h-screen bg-[#0a0a0b] text-white"
    >
      <div className="max-w-[1400px] mx-auto px-4 py-6 md:px-8 md:py-8">
        {/* Page header */}
        <div className="mb-8 md:mb-10">
          <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
            Overview
          </p>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-zinc-50">
            {greeting}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            {now.toLocaleDateString("en-US", {
              weekday: "long",
              month: "long",
              day: "numeric",
            })}
          </p>
        </div>

        {/* Stats cards – will span full width of this container */}
        <StatsCards data={data} isLoading={isLoading} isError={isError} />

        {/* Emails widget – separate card */}
        <div className="mt-8">
          <ImportantEmailsWidget />
        </div>
      </div>
    </motion.div>
  );
}

export default Component;
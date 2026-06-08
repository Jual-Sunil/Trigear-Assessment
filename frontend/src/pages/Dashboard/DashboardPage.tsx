import { useQuery } from "@tanstack/react-query";
import { Box, Typography } from "@mui/material";
import { fetchDashboard } from "../../services/api/dashboardApi";
import type { DashboardResponse } from "../../services/api/types";
import { StatsCards } from "../../components/dashboard/StatsCards";
import { ImportantEmailsWidget } from "../../components/dashboard/ImportantEmailsWidget";

/**
 * Dashboard overview page.
 *
 * Fetches aggregated counts for the authenticated user via TanStack Query
 * and composes the page from focused child components:
 * - StatsCards: five metric cards across the top.
 * - ImportantEmailsWidget: priority-filtered email list below.
 *
 * Owns the page heading and top-level layout only.
 */
export function Component() {
  const { data, isLoading, isError } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
        Dashboard
      </Typography>

      <StatsCards data={data} isLoading={isLoading} isError={isError} />

      <Box sx={{ mt: 4 }}>
        <ImportantEmailsWidget />
      </Box>
    </Box>
  );
}

export default Component;

import { apiClient } from "./client";
import type { DashboardResponse } from "./types";

/**
 * Fetches aggregated dashboard counts for the authenticated user.
 * Returns totals for emails, important emails, pending tasks,
 * upcoming interviews, and active job opportunities.
 */
export async function fetchDashboard(): Promise<DashboardResponse> {
  const { data } = await apiClient.get<DashboardResponse>("/dashboard");
  return data;
}
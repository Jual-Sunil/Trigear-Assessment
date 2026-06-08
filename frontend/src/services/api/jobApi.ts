import { apiClient } from "./client";
import type { JobListResponse } from "./types";

/**
 * Fetches all job opportunities extracted from the authenticated user's emails.
 */
export async function fetchJobs(): Promise<JobListResponse> {
  const { data } = await apiClient.get<JobListResponse>("/jobs");
  return data;
}
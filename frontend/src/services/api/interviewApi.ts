import { apiClient } from "./client";
import type { InterviewListResponse } from "./types";

/**
 * Fetches all interviews extracted from the authenticated user's emails.
 */
export async function fetchInterviews(): Promise<InterviewListResponse> {
  const { data } = await apiClient.get<InterviewListResponse>("/interviews");
  return data;
}
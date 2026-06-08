import { apiClient } from "./client";

/**
 * Triggers a manual sync of the authenticated user's emails.
 * @returns A promise that resolves when the sync request is accepted.
 */
export async function syncEmails(): Promise<void> {
  await apiClient.post("/sync");
}
import { apiClient } from "./client";
import type { EmailListResponse, EmailDetail, EmailListParams } from "./types";

/**
 * Fetches a paginated, optionally filtered list of emails for the
 * authenticated user.
 *
 * @param params - Optional filters: classification, priority_min, page, page_size.
 */
export async function fetchEmails(
  params: EmailListParams = {}
): Promise<EmailListResponse> {
  const { data } = await apiClient.get<EmailListResponse>("/emails", {
    params,
  });
  return data;
}

/**
 * Fetches full detail for a single email by its UUID.
 * Includes body_text, body_html, gmail_message_id, and gmail_thread_id.
 *
 * @param emailId - UUID of the email to retrieve.
 */
export async function fetchEmailById(emailId: string): Promise<EmailDetail> {
  const { data } = await apiClient.get<EmailDetail>(`/emails/${emailId}`);
  return data;
}
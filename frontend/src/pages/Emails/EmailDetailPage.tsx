import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Alert, Box } from "@mui/material";
import { fetchEmailById } from "../../services/api/emailApi";
import type { EmailDetail } from "../../services/api/types";
import { EmailHeader } from "../../components/emails/EmailHeader";
import { EmailSummaryCard } from "../../components/emails/EmailSummaryCard";
import { EmailBodyViewer } from "../../components/emails/EmailBodyViewer";

/**
 * Email detail page.
 *
 * Fetches a single email by UUID via GET /emails/{id} using TanStack Query
 * and composes the view from three focused child components:
 *
 * - EmailHeader:      subject, sender, received date, back navigation.
 * - EmailSummaryCard: AI metadata — classification, confidence, priority,
 *                     action-required flag, and AI summary.
 * - EmailBodyViewer:  sandboxed HTML render or plain-text fallback.
 *
 * Owns data-fetching, loading state, and error state only.
 */
export function Component() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, isError } = useQuery<EmailDetail>({
    queryKey: ["email", id],
    queryFn: () => fetchEmailById(id!),
    enabled: Boolean(id),
  });

  return (
    <Box>
      <EmailHeader email={data} isLoading={isLoading} />

      {isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load email. It may not exist or you may not have access.
        </Alert>
      )}

      {!isError && (
        <>
          <EmailSummaryCard email={data} isLoading={isLoading} />
          <EmailBodyViewer email={data} isLoading={isLoading} />
        </>
      )}
    </Box>
  );
}

export default Component;

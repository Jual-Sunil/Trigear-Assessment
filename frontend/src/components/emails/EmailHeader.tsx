import {
  Box,
  Button,
  Skeleton,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";
import type { EmailDetail } from "../../services/api/types";

export interface EmailHeaderProps {
  /** Full email record; undefined while loading. */
  email: EmailDetail | undefined;
  /** When true, renders skeleton placeholders instead of content. */
  isLoading: boolean;
}

/**
 * Formats an ISO date string to a full locale date and time representation.
 *
 * @param iso - ISO 8601 date string.
 * @returns Human-readable date/time string.
 */
function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Renders the email detail page header.
 *
 * Contains the back navigation button, email subject as the page title,
 * and the formatted sender / received-at line below the subject.
 * Renders skeleton placeholders for all text fields while data is loading.
 */
export function EmailHeader({ email, isLoading }: EmailHeaderProps) {
  const navigate = useNavigate();

  return (
    <Box sx={{ mb: 3 }}>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/emails")}
        size="small"
        sx={{ mb: 2 }}
      >
        Back to Emails
      </Button>

      {isLoading ? (
        <>
          <Skeleton variant="text" width="60%" height={36} sx={{ mb: 0.5 }} />
          <Skeleton variant="text" width="40%" height={20} />
        </>
      ) : (
        <>
          <Typography
            variant="h5"
            sx={{ fontWeight: 700, lineHeight: 1.3, mb: 0.5 }}
          >
            {email?.subject ?? "(No subject)"}
          </Typography>

          <Typography variant="body2" color="text.secondary">
            {email?.sender_name
              ? `${email.sender_name} <${email.sender_email}>`
              : email?.sender_email ?? ""}
            {email?.received_at
              ? `  ·  ${formatDateTime(email.received_at)}`
              : ""}
          </Typography>
        </>
      )}
    </Box>
  );
}

export default EmailHeader;

import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Card,
  CardContent,
  CardHeader,
  Divider,
  List,
  ListItem,
  ListItemButton,
  Skeleton,
  Tooltip,
  Typography,
} from "@mui/material";
import StarIcon from "@mui/icons-material/Star";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { Link as RouterLink } from "react-router-dom";
import { fetchEmails } from "../../services/api/emailApi";
import type { EmailSummary } from "../../services/api/types";
import { EmailClassificationChip } from "../emails/EmailClassificationChip";
import { EmailPriorityChip } from "../emails/EmailPriorityChip";

/** Number of important emails displayed in the widget. */
const DISPLAY_LIMIT = 10;

/** Minimum priority score used to filter the API request. */
const PRIORITY_MIN = 70;

/**
 * Truncates a string to a maximum character length, appending an ellipsis
 * when the source string exceeds that length.
 *
 * @param text - Source string to truncate.
 * @param max  - Maximum allowed character count.
 * @returns Truncated string.
 */
function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

/**
 * Skeleton placeholder row rendered while data is loading.
 */
function EmailRowSkeleton() {
  return (
    <ListItem disablePadding divider sx={{ px: 0 }}>
      <Box sx={{ width: "100%", px: 2, py: 1.5 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.75 }}>
          <Skeleton variant="text" width="45%" height={18} />
          <Skeleton variant="rounded" width={90} height={20} />
        </Box>
        <Skeleton variant="text" width="30%" height={14} sx={{ mb: 0.5 }} />
        <Skeleton variant="text" width="75%" height={14} />
      </Box>
    </ListItem>
  );
}

interface EmailRowProps {
  email: EmailSummary;
}

/**
 * Renders a single important email row with subject, sender, classification,
 * priority chip, and summary. The entire row is a router link to the detail page.
 */
function EmailRow({ email }: EmailRowProps) {
  const subject = email.subject ?? "(No subject)";
  const sender = email.sender_name ?? email.sender_email;

  return (
    <ListItem disablePadding divider>
      <ListItemButton
        component={RouterLink}
        to={`/emails/${email.id}`}
        sx={{
          px: 2,
          py: 1.5,
          gap: 1,
          alignItems: "flex-start",
          "&:hover": { backgroundColor: "action.hover" },
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {/* Row 1 — subject + chips */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 0.75,
              mb: 0.5,
            }}
          >
            <Tooltip title={subject} placement="top-start" enterDelay={600}>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 600,
                  fontSize: "0.8125rem",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  maxWidth: { xs: 160, sm: 260, md: 320 },
                }}
              >
                {subject}
              </Typography>
            </Tooltip>

            <EmailClassificationChip classification={email.classification} />
            <EmailPriorityChip priorityScore={email.priority_score} />
          </Box>

          {/* Row 2 — sender */}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mb: 0.5, fontSize: "0.75rem" }}
          >
            {truncate(sender, 48)}
          </Typography>

          {/* Row 3 — AI summary */}
          {email.summary && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
                fontSize: "0.75rem",
                lineHeight: 1.4,
              }}
            >
              {email.summary}
            </Typography>
          )}
        </Box>

        <ChevronRightIcon
          fontSize="small"
          sx={{ color: "text.disabled", mt: 0.25, flexShrink: 0 }}
        />
      </ListItemButton>
    </ListItem>
  );
}

/**
 * Dashboard widget that displays the top important emails.
 *
 * Fetches emails filtered by `priority_min=70` using the shared
 * `fetchEmails` service, sorts them descending by priority score
 * client-side, and renders the top 10 as clickable rows linking to
 * the individual email detail page.
 *
 * Handles loading state with skeleton rows and surfaces a user-facing
 * Alert on fetch failure.
 */
export function ImportantEmailsWidget() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["emails", "important", PRIORITY_MIN],
    queryFn: () =>
      fetchEmails({ priority_min: PRIORITY_MIN, page_size: 50, page: 1 }),
  });

  const emails: EmailSummary[] = data
    ? [...data.items]
        .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0))
        .slice(0, DISPLAY_LIMIT)
    : [];

  return (
    <Card variant="outlined">
      <CardHeader
        avatar={<StarIcon color="warning" fontSize="small" />}
        title={
          <Typography variant="subtitle1" sx={{ fontWeight: 700, fontSize: "0.9375rem" }}>
            Important Emails
          </Typography>
        }
        subheader={
          !isLoading && !isError && data ? (
            <Typography variant="caption" color="text.secondary">
              {data.total} total · showing top {Math.min(emails.length, DISPLAY_LIMIT)}
            </Typography>
          ) : null
        }
        sx={{ pb: 0 }}
      />

      <Divider />

      <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
        {isError && (
          <Alert severity="error" sx={{ m: 2 }}>
            Failed to load important emails. Please try again.
          </Alert>
        )}

        {!isError && (
          <List disablePadding>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <EmailRowSkeleton key={i} />
                ))
              : emails.length === 0
              ? (
                <ListItem sx={{ px: 2, py: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    No important emails found.
                  </Typography>
                </ListItem>
              )
              : emails.map((email) => (
                  <EmailRow key={email.id} email={email} />
                ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
}

export default ImportantEmailsWidget;

import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Divider,
  LinearProgress,
  Skeleton,
  Tooltip,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import type { EmailDetail } from "../../services/api/types";
import { EmailClassificationChip } from "./EmailClassificationChip";
import { EmailPriorityChip } from "./EmailPriorityChip";

export interface EmailSummaryCardProps {
  /** Full email record; undefined while loading. */
  email: EmailDetail | undefined;
  /** When true, renders skeleton placeholders instead of content. */
  isLoading: boolean;
}

interface MetaRowProps {
  label: string;
  children: React.ReactNode;
}

/**
 * Renders a single label/value metadata row with consistent spacing.
 */
function MetaRow({ label, children }: MetaRowProps) {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        minHeight: 28,
      }}
    >
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ minWidth: 140, fontSize: "0.8125rem" }}
      >
        {label}
      </Typography>
      {children}
    </Box>
  );
}

/**
 * Renders a confidence score as a labelled linear progress bar.
 *
 * @param score - Confidence value in the range 0–1, or null.
 */
function ConfidenceBar({ score }: { score: number | null }) {
  if (score === null || score === undefined) {
    return (
      <Typography variant="body2" color="text.disabled">
        —
      </Typography>
    );
  }

  const pct = Math.round(score * 100);

  return (
    <Tooltip title={`${pct}% confidence`} placement="right">
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}>
        <LinearProgress
          variant="determinate"
          value={pct}
          color={pct >= 80 ? "success" : pct >= 50 ? "warning" : "error"}
          sx={{ flex: 1, maxWidth: 120, height: 6, borderRadius: 3 }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          {pct}%
        </Typography>
      </Box>
    </Tooltip>
  );
}

/**
 * Renders the AI intelligence card for an email detail view.
 *
 * Displays classification, confidence score, priority score, action-required
 * flag, and the AI-generated summary in a compact metadata card.
 * All fields are optional — rows are omitted when the value is null.
 * Renders skeleton placeholders while data is loading.
 */
export function EmailSummaryCard({ email, isLoading }: EmailSummaryCardProps) {
  const hasAnyMeta =
    email?.classification != null ||
    email?.confidence_score != null ||
    email?.priority_score != null ||
    email?.is_action_required != null;

  const hasSummary = Boolean(email?.summary);

  if (!isLoading && !hasAnyMeta && !hasSummary) {
    return null;
  }

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardHeader
        avatar={<AutoAwesomeIcon color="primary" fontSize="small" />}
        title={
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            AI Intelligence
          </Typography>
        }
        sx={{ pb: 0 }}
      />

      <Divider sx={{ mt: 1 }} />

      <CardContent sx={{ pt: 1.5, pb: "12px !important" }}>
        {isLoading ? (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            <Skeleton variant="text" width="45%" height={22} />
            <Skeleton variant="text" width="35%" height={22} />
            <Skeleton variant="text" width="55%" height={22} />
            <Divider sx={{ my: 1 }} />
            <Skeleton variant="text" width="100%" height={16} />
            <Skeleton variant="text" width="90%" height={16} />
            <Skeleton variant="text" width="70%" height={16} />
          </Box>
        ) : (
          <>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
              {email?.classification != null && (
                <MetaRow label="Classification">
                  <EmailClassificationChip classification={email.classification} />
                </MetaRow>
              )}

              {email?.confidence_score != null && (
                <MetaRow label="Confidence">
                  <ConfidenceBar score={email.confidence_score} />
                </MetaRow>
              )}

              {email?.priority_score != null && (
                <MetaRow label="Priority Score">
                  <EmailPriorityChip priorityScore={email.priority_score} />
                </MetaRow>
              )}

              {email?.is_action_required != null && (
                <MetaRow label="Action Required">
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: email.is_action_required ? "warning.main" : "text.secondary",
                      fontSize: "0.8125rem",
                    }}
                  >
                    {email.is_action_required ? "Yes" : "No"}
                  </Typography>
                </MetaRow>
              )}
            </Box>

            {hasSummary && (
              <>
                {hasAnyMeta && <Divider sx={{ my: 1.5 }} />}
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{
                    display: "block",
                    fontSize: "0.8rem",
                    fontStyle: "italic",
                    lineHeight: 1.6,
                  }}
                >
                  {email!.summary}
                </Typography>
              </>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default EmailSummaryCard;

import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Tooltip,
  Typography,
} from "@mui/material";
import BusinessIcon from "@mui/icons-material/Business";
import WorkOutlineOutlinedIcon from "@mui/icons-material/WorkOutlineOutlined";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import VideoCallIcon from "@mui/icons-material/VideoCall";
import type { Interview } from "../../services/api/types";

export interface InterviewCardProps {
  /** Interview record to render. */
  interview: Interview;
}

/**
 * Formats an ISO date string to a full locale date and time.
 *
 * @param iso - ISO 8601 date string, or null.
 * @returns Formatted date/time string, or "—" when the value is absent.
 */
function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Returns the number of whole days between now and a future ISO date.
 * Returns null when the date is in the past or the value is absent.
 *
 * @param iso - ISO 8601 date string, or null.
 */
function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return null;
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

/**
 * Resolves a countdown label and colour token for the interview date chip.
 *
 * @param days - Days until interview, or null.
 */
function countdownAppearance(days: number | null): {
  label: string;
  color: "error" | "warning" | "success" | "default";
} {
  if (days === null) return { label: "Past", color: "default" };
  if (days === 0) return { label: "Today", color: "error" };
  if (days === 1) return { label: "Tomorrow", color: "error" };
  if (days <= 7) return { label: `In ${days} days`, color: "warning" };
  return { label: `In ${days} days`, color: "success" };
}

/**
 * Renders a single interview as a compact MUI Card.
 *
 * Displays company, role, interview date/time, a countdown chip, and a
 * Join button when a meeting link is available. Past interviews display
 * a muted "Past" chip and a disabled Join button.
 */
export function InterviewCard({ interview }: InterviewCardProps) {
  const days = daysUntil(interview.interview_date);
  const countdown = countdownAppearance(days);
  const isPast = days === null;

  return (
    <Card
      variant="outlined"
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        opacity: isPast ? 0.75 : 1,
        transition: "box-shadow 0.2s ease, transform 0.2s ease",
        "&:hover": {
          boxShadow: isPast ? undefined : "0 4px 16px rgba(0,0,0,0.08)",
          transform: isPast ? undefined : "translateY(-2px)",
        },
      }}
    >
      <CardContent
        sx={{
          p: 2,
          "&:last-child": { pb: 2 },
          flex: 1,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Company */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
          <BusinessIcon sx={{ fontSize: "0.875rem", color: "text.disabled" }} />
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ fontSize: "0.775rem", fontWeight: 500 }}
          >
            {interview.company ?? "—"}
          </Typography>
        </Box>

        {/* Role */}
        <Tooltip
          title={interview.role ?? ""}
          placement="top-start"
          enterDelay={600}
          disableHoverListener={!interview.role || interview.role.length <= 50}
        >
          <Box sx={{ display: "flex", alignItems: "flex-start", gap: 0.75, mb: 1.25 }}>
            <WorkOutlineOutlinedIcon
              sx={{ fontSize: "0.875rem", color: "info.main", mt: "2px", flexShrink: 0 }}
            />
            <Typography
              variant="body2"
              sx={{
                fontWeight: 700,
                fontSize: "0.9375rem",
                lineHeight: 1.3,
                overflow: "hidden",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
              }}
            >
              {interview.role ?? "—"}
            </Typography>
          </Box>
        </Tooltip>

        <Divider sx={{ my: 1 }} />

        {/* Date + countdown */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 1,
            mb: 1.5,
            mt: 0.5,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <AccessTimeIcon sx={{ fontSize: "0.8rem", color: "text.disabled" }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
              {formatDateTime(interview.interview_date)}
            </Typography>
          </Box>

          <Chip
            label={countdown.label}
            size="small"
            color={countdown.color}
            variant={isPast ? "outlined" : "filled"}
            sx={{ fontSize: "0.7rem", height: 20, fontWeight: 500 }}
          />
        </Box>

        {/* Meeting link */}
        <Box sx={{ mt: "auto" }}>
          {interview.meeting_link ? (
            <Button
              size="small"
              variant={isPast ? "outlined" : "contained"}
              disableElevation
              color="info"
              startIcon={<VideoCallIcon fontSize="small" />}
              href={interview.meeting_link}
              target="_blank"
              rel="noopener noreferrer"
              disabled={isPast}
              sx={{ textTransform: "none", fontWeight: 600 }}
            >
              Join Meeting
            </Button>
          ) : (
            <Typography variant="caption" color="text.disabled">
              No meeting link
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

export default InterviewCard;

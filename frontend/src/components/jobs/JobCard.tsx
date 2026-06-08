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
import LocationOnIcon from "@mui/icons-material/LocationOn";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import type { JobOpportunity } from "../../services/api/types";

export interface JobCardProps {
  /** Job opportunity record to render. */
  job: JobOpportunity;
}

/**
 * Formats an ISO date string to a short locale date.
 *
 * @param iso - ISO 8601 date string, or null.
 * @returns Formatted date string, or "—" when the value is absent.
 */
function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Returns true when an ISO deadline string represents a date in the past.
 *
 * @param iso - ISO 8601 date string, or null.
 */
function isPastDeadline(iso: string | null): boolean {
  if (!iso) return false;
  return new Date(iso) < new Date();
}

/**
 * Renders a single job opportunity as a compact MUI Card.
 *
 * Displays company, role, location, salary, deadline, and an apply link.
 * Cards whose deadline has already passed receive an error-coloured
 * calendar label to signal urgency. The apply button opens the link in
 * a new tab with `rel="noopener noreferrer"`.
 */
export function JobCard({ job }: JobCardProps) {
  const expired = isPastDeadline(job.deadline);

  return (
    <Card
      variant="outlined"
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        transition: "box-shadow 0.2s ease, transform 0.2s ease",
        "&:hover": {
          boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
          transform: "translateY(-2px)",
        },
      }}
    >
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 }, flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Company + role */}
        <Box sx={{ mb: 1.25 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
            <BusinessIcon sx={{ fontSize: "0.875rem", color: "text.disabled" }} />
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontSize: "0.775rem", fontWeight: 500 }}
            >
              {job.company ?? "—"}
            </Typography>
          </Box>

          <Tooltip
            title={job.role ?? ""}
            placement="top-start"
            enterDelay={600}
            disableHoverListener={!job.role || job.role.length <= 50}
          >
            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 0.75 }}>
              <WorkOutlineOutlinedIcon
                sx={{ fontSize: "0.875rem", color: "primary.main", mt: "2px", flexShrink: 0 }}
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
                {job.role ?? "—"}
              </Typography>
            </Box>
          </Tooltip>
        </Box>

        <Divider sx={{ my: 1 }} />

        {/* Location + salary */}
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 1.25 }}>
          {job.location && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <LocationOnIcon sx={{ fontSize: "0.8rem", color: "text.disabled" }} />
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
                {job.location}
              </Typography>
            </Box>
          )}

          {job.salary && (
            <Chip
              icon={<AttachMoneyIcon sx={{ fontSize: "0.8rem !important" }} />}
              label={job.salary}
              size="small"
              variant="outlined"
              color="success"
              sx={{ fontSize: "0.7rem", height: 20 }}
            />
          )}
        </Box>

        {/* Deadline */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1.5, mt: "auto" }}>
          <CalendarTodayIcon
            sx={{
              fontSize: "0.8rem",
              color: expired ? "error.main" : "text.disabled",
            }}
          />
          <Typography
            variant="caption"
            sx={{
              fontSize: "0.75rem",
              color: expired ? "error.main" : "text.secondary",
              fontWeight: expired ? 600 : 400,
            }}
          >
            {expired ? "Expired · " : "Deadline · "}
            {formatDate(job.deadline)}
          </Typography>
        </Box>

        {/* Apply button */}
        {job.apply_link ? (
          <Button
            size="small"
            variant="contained"
            disableElevation
            endIcon={<OpenInNewIcon fontSize="inherit" />}
            href={job.apply_link}
            target="_blank"
            rel="noopener noreferrer"
            disabled={expired}
            sx={{ textTransform: "none", fontWeight: 600, alignSelf: "flex-start" }}
          >
            Apply Now
          </Button>
        ) : (
          <Typography variant="caption" color="text.disabled">
            No apply link
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export default JobCard;

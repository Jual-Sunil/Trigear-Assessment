import {
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Tooltip,
  Typography,
} from "@mui/material";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import FlagIcon from "@mui/icons-material/Flag";
import type { Task } from "../../services/api/types";
import { TaskStatusSelect, statusChipColor } from "./TaskStatusSelect";

export interface TaskCardProps {
  /** Task record to render. */
  task: Task;
}

/**
 * Formats an ISO date string to a short human-readable locale date.
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
 * Maps a numeric priority value to a display label and MUI colour token.
 *
 * The backend stores priority as an integer (higher = more urgent).
 * Thresholds mirror the priority scoring range used by PriorityScoringService.
 *
 * @param priority - Raw numeric priority value, or null.
 * @returns Object containing a human-readable label and a MUI colour token.
 */
function resolvePriority(priority: number | null): {
  label: string;
  color: "error" | "warning" | "info" | "default";
} {
  if (priority === null || priority === undefined) {
    return { label: "—", color: "default" };
  }
  if (priority >= 80) return { label: `${priority} · Critical`, color: "error" };
  if (priority >= 60) return { label: `${priority} · High`, color: "warning" };
  if (priority >= 40) return { label: `${priority} · Medium`, color: "info" };
  return { label: `${priority} · Low`, color: "default" };
}

/**
 * Renders a single task as a compact MUI Card.
 *
 * Displays title, description, due date, priority badge, current status chip,
 * and an inline TaskStatusSelect for in-place status updates.
 *
 * Cards whose due date has passed and whose status is not "done" or "cancelled"
 * receive a subtle left-border warning to signal overdue state.
 */
export function TaskCard({ task }: TaskCardProps) {
  const priority = resolvePriority(task.priority);
  const isActive =
    task.status !== "done" && task.status !== "cancelled";
  const isOverdue =
    isActive &&
    task.due_date !== null &&
    new Date(task.due_date) < new Date();

  return (
    <Card
      variant="outlined"
      sx={{
        borderLeft: isOverdue ? "3px solid" : undefined,
        borderLeftColor: isOverdue ? "error.main" : undefined,
        borderRadius: isOverdue ? "0 8px 8px 0" : undefined,
        transition: "box-shadow 0.2s ease, transform 0.2s ease",
        "&:hover": {
          boxShadow: "0 4px 16px rgba(0,0,0,0.07)",
          transform: "translateY(-1px)",
        },
      }}
    >
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        {/* Title + status chip row */}
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 1,
            mb: 0.75,
          }}
        >
          <Tooltip
            title={task.title ?? ""}
            placement="top-start"
            enterDelay={600}
            disableHoverListener={!task.title || task.title.length <= 60}
          >
            <Typography
              variant="body2"
              sx={{
                fontWeight: 600,
                fontSize: "0.875rem",
                lineHeight: 1.35,
                overflow: "hidden",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                flex: 1,
              }}
            >
              {task.title ?? "(Untitled)"}
            </Typography>
          </Tooltip>

          <Chip
            label={(task.status ?? "pending").replace("_", " ")}
            size="small"
            color={statusChipColor(task.status)}
            sx={{
              textTransform: "capitalize",
              fontSize: "0.7rem",
              height: 20,
              fontWeight: 500,
              flexShrink: 0,
            }}
          />
        </Box>

        {/* Description */}
        {task.description && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              fontSize: "0.775rem",
              lineHeight: 1.45,
              mb: 1.25,
            }}
          >
            {task.description}
          </Typography>
        )}

        <Divider sx={{ my: 1 }} />

        {/* Meta row — due date + priority + status select */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 1.5,
            justifyContent: "space-between",
          }}
        >
          {/* Left: due date + priority */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap" }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <CalendarTodayIcon
                sx={{
                  fontSize: "0.8rem",
                  color: isOverdue ? "error.main" : "text.disabled",
                }}
              />
              <Typography
                variant="caption"
                sx={{
                  fontSize: "0.75rem",
                  color: isOverdue ? "error.main" : "text.secondary",
                  fontWeight: isOverdue ? 600 : 400,
                }}
              >
                {formatDate(task.due_date)}
              </Typography>
            </Box>

            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <FlagIcon sx={{ fontSize: "0.8rem", color: "text.disabled" }} />
              <Chip
                label={priority.label}
                size="small"
                color={priority.color}
                variant="outlined"
                sx={{ fontSize: "0.7rem", height: 18 }}
              />
            </Box>
          </Box>

          {/* Right: inline status select */}
          <TaskStatusSelect task={task} />
        </Box>
      </CardContent>
    </Card>
  );
}

export default TaskCard;

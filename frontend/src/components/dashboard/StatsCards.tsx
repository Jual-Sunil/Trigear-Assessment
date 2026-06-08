import { Alert, Grid } from "@mui/material";
import EmailIcon from "@mui/icons-material/Email";
import StarIcon from "@mui/icons-material/Star";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import WorkIcon from "@mui/icons-material/Work";
import { useTheme } from "@mui/material/styles";
import { StatCard } from "./StatCard";
import type { DashboardResponse } from "../../services/api/types";

export interface StatsCardsProps {
  /** Aggregated dashboard counts from the API; undefined while loading. */
  data: DashboardResponse | undefined;
  /** When true, all cards render skeleton placeholders. */
  isLoading: boolean;
  /** When true, renders an error alert above the card grid. */
  isError: boolean;
}

/**
 * Renders the full responsive grid of dashboard stat cards.
 *
 * Displays five metric cards for total emails, important emails,
 * pending tasks, upcoming interviews, and active job opportunities.
 * Each card receives a distinct MUI theme-colour accent stripe.
 *
 * Propagates isLoading and isError states to child StatCard instances
 * and surfaces a user-facing error alert when isError is true.
 */
export function StatsCards({ data, isLoading, isError }: StatsCardsProps) {
  const theme = useTheme();

  const stats = [
    {
      label: "Total Emails",
      value: data?.total_emails,
      icon: <EmailIcon fontSize="small" color="primary" />,
      accentColor: theme.palette.primary.main,
    },
    {
      label: "Important Emails",
      value: data?.important_emails,
      icon: <StarIcon fontSize="small" color="warning" />,
      accentColor: theme.palette.warning.main,
    },
    {
      label: "Pending Tasks",
      value: data?.pending_tasks,
      icon: <TaskAltIcon fontSize="small" color="success" />,
      accentColor: theme.palette.success.main,
    },
    {
      label: "Upcoming Interviews",
      value: data?.upcoming_interviews,
      icon: <CalendarTodayIcon fontSize="small" color="info" />,
      accentColor: theme.palette.info.main,
    },
    {
      label: "Active Jobs",
      value: data?.active_jobs,
      icon: <WorkIcon fontSize="small" color="secondary" />,
      accentColor: theme.palette.secondary.main,
    },
  ] as const;

  return (
    <>
      {isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load dashboard data. Please try again.
        </Alert>
      )}

      <Grid container spacing={2}>
        {stats.map((stat) => (
          <Grid key={stat.label} size={{ xs: 12, sm: 6, md: 4, lg: 4 }}>
            <StatCard
              label={stat.label}
              value={stat.value}
              icon={stat.icon}
              isLoading={isLoading}
              accentColor={stat.accentColor}
            />
          </Grid>
        ))}
      </Grid>
    </>
  );
}

export default StatsCards;

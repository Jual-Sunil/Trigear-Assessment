import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Grid,
  Skeleton,
  Card,
  CardContent,
  Divider,
  Typography,
} from "@mui/material";
import { fetchTasks } from "../../services/api/taskApi";
import type { Task, TaskListResponse } from "../../services/api/types";
import { TaskCard } from "./TaskCard";

/**
 * Sorts tasks first by priority descending (higher priority first),
 * then by due_date ascending (earlier deadlines first) as a tiebreaker.
 * Null priorities sort after defined values.
 * Null due dates sort after defined dates.
 *
 * @param tasks - Unsorted array of Task records.
 * @returns New sorted array; the input array is not mutated.
 */
function sortTasks(tasks: Task[]): Task[] {
  return [...tasks].sort((a, b) => {
    const pa = a.priority ?? -1;
    const pb = b.priority ?? -1;
    if (pb !== pa) return pb - pa;

    const da = a.due_date ? new Date(a.due_date).getTime() : Infinity;
    const db = b.due_date ? new Date(b.due_date).getTime() : Infinity;
    return da - db;
  });
}

/**
 * Skeleton placeholder rendered for each card while data is loading.
 * Matches the approximate height of a populated TaskCard.
 */
function TaskCardSkeleton() {
  return (
    <Card variant="outlined">
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.75 }}>
          <Skeleton variant="text" width="60%" height={20} />
          <Skeleton variant="rounded" width={68} height={20} />
        </Box>
        <Skeleton variant="text" width="90%" height={14} />
        <Skeleton variant="text" width="75%" height={14} sx={{ mb: 1.25 }} />
        <Divider sx={{ my: 1 }} />
        <Box sx={{ display: "flex", justifyContent: "space-between" }}>
          <Box sx={{ display: "flex", gap: 1.5 }}>
            <Skeleton variant="rounded" width={72} height={18} />
            <Skeleton variant="rounded" width={84} height={18} />
          </Box>
          <Skeleton variant="rounded" width={120} height={24} />
        </Box>
      </CardContent>
    </Card>
  );
}

/**
 * Renders the full task list for the Tasks page.
 *
 * Fetches all tasks via GET /tasks using TanStack Query, sorts them
 * by priority descending then due_date ascending, and renders each as a
 * TaskCard in a responsive MUI Grid.
 *
 * Handles loading state with skeleton placeholders, surfaces an Alert on
 * fetch failure, and renders an empty state message when no tasks exist.
 */
export function TaskList() {
  const { data, isLoading, isError } = useQuery<TaskListResponse>({
    queryKey: ["tasks"],
    queryFn: fetchTasks,
  });

  const tasks = data ? sortTasks(data.items) : [];

  if (isError) {
    return (
      <Alert severity="error">
        Failed to load tasks. Please try again.
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Grid container spacing={2}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Grid key={i} size={{ xs: 12, sm: 6, lg: 4 }}>
            <TaskCardSkeleton />
          </Grid>
        ))}
      </Grid>
    );
  }

  if (tasks.length === 0) {
    return (
      <Box
        sx={{
          py: 8,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          No tasks found.
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={2}>
      {tasks.map((task) => (
        <Grid key={task.id} size={{ xs: 12, sm: 6, lg: 4 }}>
          <TaskCard task={task} />
        </Grid>
      ))}
    </Grid>
  );
}

export default TaskList;

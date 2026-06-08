import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Chip,
  CircularProgress,
  FormControl,
  MenuItem,
  Select,
  type SelectChangeEvent,
} from "@mui/material";
import { updateTask } from "../../services/api/taskApi";
import type { Task } from "../../services/api/types";

/** All valid task status values accepted by PATCH /tasks/{id}. */
export const TASK_STATUS_OPTIONS = [
  "pending",
  "in_progress",
  "done",
  "cancelled",
] as const;

export type TaskStatus = (typeof TASK_STATUS_OPTIONS)[number];

/**
 * Maps a task status string to a MUI Chip colour token.
 *
 * @param status - Task status value, or null.
 * @returns MUI colour token for the Chip component.
 */
export function statusChipColor(
  status: string | null
): "default" | "primary" | "success" | "error" {
  switch (status) {
    case "pending":
      return "default";
    case "in_progress":
      return "primary";
    case "done":
      return "success";
    case "cancelled":
      return "error";
    default:
      return "default";
  }
}

export interface TaskStatusSelectProps {
  /** Task record owning the status field to update. */
  task: Task;
}

/**
 * Inline status selector for a single task.
 *
 * Fires PATCH /tasks/{id} on change via a TanStack Query mutation,
 * then invalidates the "tasks" query cache to trigger a fresh list fetch.
 * Renders a loading spinner overlay on the select while the mutation is in-flight
 * and disables the control to prevent concurrent updates on the same task.
 */
export function TaskStatusSelect({ task }: TaskStatusSelectProps) {
  const queryClient = useQueryClient();

  const { mutate, isPending } = useMutation({
    mutationFn: (status: string) => updateTask(task.id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  function handleChange(e: SelectChangeEvent<string>) {
    mutate(e.target.value);
  }

  return (
    <FormControl size="small" variant="standard" disabled={isPending}>
      <Select
        value={task.status ?? "pending"}
        onChange={handleChange}
        disableUnderline
        startAdornment={
          isPending ? (
            <CircularProgress
              size={12}
              sx={{ mr: 0.5, color: "text.secondary" }}
            />
          ) : null
        }
        sx={{ minWidth: 130 }}
      >
        {TASK_STATUS_OPTIONS.map((s) => (
          <MenuItem key={s} value={s}>
            <Chip
              label={s.replace("_", " ")}
              size="small"
              color={statusChipColor(s)}
              sx={{
                cursor: "pointer",
                textTransform: "capitalize",
                fontSize: "0.7rem",
                height: 20,
                fontWeight: 500,
              }}
            />
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

export default TaskStatusSelect;

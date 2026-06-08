import { apiClient } from "./client";
import type { TaskListResponse, TaskUpdateRequest, TaskUpdateResponse } from "./types";

/**
 * Fetches all tasks extracted from the authenticated user's emails.
 */
export async function fetchTasks(): Promise<TaskListResponse> {
  const { data } = await apiClient.get<TaskListResponse>("/tasks");
  return data;
}

/**
 * Partially updates a task's status, priority, or due date.
 * Only fields present in the payload are applied.
 *
 * @param taskId - UUID of the task to update.
 * @param payload - Fields to update. All fields are optional.
 */
export async function updateTask(
  taskId: string,
  payload: TaskUpdateRequest
): Promise<TaskUpdateResponse> {
  const { data } = await apiClient.patch<TaskUpdateResponse>(
    `/tasks/${taskId}`,
    payload
  );
  return data;
}
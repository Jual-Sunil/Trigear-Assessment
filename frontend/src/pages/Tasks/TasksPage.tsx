import { Box, Typography } from "@mui/material";
import { TaskList } from "../../components/tasks/TaskList";

/**
 * Tasks page.
 *
 * Lists all tasks extracted from the authenticated user's emails,
 * sorted by priority descending then due date ascending.
 * Delegates all data-fetching, sorting, loading, and error handling
 * to the TaskList component.
 *
 * Owns the page heading and top-level layout only.
 */
export function Component() {
  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
        Tasks
      </Typography>

      <TaskList />
    </Box>
  );
}

export default Component;

import { Box, Typography } from "@mui/material";
import { InterviewList } from "../../components/interviews/InterviewList";

/**
 * Interviews page.
 *
 * Lists all interviews extracted from the authenticated user's emails,
 * sorted by nearest interview date ascending.
 * Delegates all data-fetching, sorting, loading, and error handling
 * to the InterviewList component.
 *
 * Owns the page heading and top-level layout only.
 */
export function Component() {
  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
        Interviews
      </Typography>

      <InterviewList />
    </Box>
  );
}

export default Component;

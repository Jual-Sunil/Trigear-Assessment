import { Box, Typography } from "@mui/material";
import { JobList } from "../../components/jobs/JobList";

/**
 * Job opportunities page.
 *
 * Lists all job opportunities extracted from the authenticated user's emails,
 * sorted by nearest deadline ascending.
 * Delegates all data-fetching, sorting, loading, and error handling
 * to the JobList component.
 *
 * Owns the page heading and top-level layout only.
 */
export function Component() {
  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
        Job Opportunities
      </Typography>

      <JobList />
    </Box>
  );
}

export default Component;

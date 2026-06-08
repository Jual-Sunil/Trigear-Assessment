import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Divider,
  Grid,
  Skeleton,
  Typography,
} from "@mui/material";
import { fetchJobs } from "../../services/api/jobApi";
import type { JobListResponse, JobOpportunity } from "../../services/api/types";
import { JobCard } from "./JobCard";

/**
 * Sorts job opportunities by deadline ascending (nearest deadline first).
 * Jobs with no deadline are placed at the end.
 *
 * @param jobs - Unsorted array of JobOpportunity records.
 * @returns New sorted array; the input is not mutated.
 */
function sortJobs(jobs: JobOpportunity[]): JobOpportunity[] {
  return [...jobs].sort((a, b) => {
    const da = a.deadline ? new Date(a.deadline).getTime() : Infinity;
    const db = b.deadline ? new Date(b.deadline).getTime() : Infinity;
    return da - db;
  });
}

/**
 * Skeleton placeholder matching the approximate height of a JobCard.
 */
function JobCardSkeleton() {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        <Skeleton variant="text" width="40%" height={14} sx={{ mb: 0.5 }} />
        <Skeleton variant="text" width="70%" height={22} sx={{ mb: 1.25 }} />
        <Divider sx={{ my: 1 }} />
        <Box sx={{ display: "flex", gap: 1, mb: 1.25 }}>
          <Skeleton variant="rounded" width={90} height={18} />
          <Skeleton variant="rounded" width={72} height={18} />
        </Box>
        <Skeleton variant="text" width="50%" height={14} sx={{ mb: 1.5 }} />
        <Skeleton variant="rounded" width={96} height={30} />
      </CardContent>
    </Card>
  );
}

/**
 * Renders the full list of job opportunities.
 *
 * Fetches jobs via GET /jobs using TanStack Query, sorts them by
 * nearest deadline ascending, and renders each as a JobCard in a
 * responsive MUI Grid.
 *
 * Handles loading state with skeleton cards, surfaces an Alert on
 * fetch failure, and renders an empty state message when no jobs exist.
 */
export function JobList() {
  const { data, isLoading, isError } = useQuery<JobListResponse>({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
  });

  const jobs = data ? sortJobs(data.items) : [];

  if (isError) {
    return (
      <Alert severity="error">
        Failed to load job opportunities. Please try again.
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Grid container spacing={2}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Grid key={i} size={{ xs: 12, sm: 6, lg: 4 }}>
            <JobCardSkeleton />
          </Grid>
        ))}
      </Grid>
    );
  }

  if (jobs.length === 0) {
    return (
      <Box sx={{ py: 8, display: "flex", justifyContent: "center" }}>
        <Typography variant="body2" color="text.secondary">
          No job opportunities found.
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={2}>
      {jobs.map((job) => (
        <Grid key={job.id} size={{ xs: 12, sm: 6, lg: 4 }}>
          <JobCard job={job} />
        </Grid>
      ))}
    </Grid>
  );
}

export default JobList;

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
import { fetchInterviews } from "../../services/api/interviewApi";
import type { Interview, InterviewListResponse } from "../../services/api/types";
import { InterviewCard } from "./InterviewCard";

/**
 * Sorts interviews by interview_date ascending (nearest date first).
 * Interviews with no date are placed at the end.
 * Past interviews sort before null-date records but after upcoming ones,
 * preserving their chronological order for reference.
 *
 * @param interviews - Unsorted array of Interview records.
 * @returns New sorted array; the input is not mutated.
 */
function sortInterviews(interviews: Interview[]): Interview[] {
  return [...interviews].sort((a, b) => {
    const da = a.interview_date ? new Date(a.interview_date).getTime() : Infinity;
    const db = b.interview_date ? new Date(b.interview_date).getTime() : Infinity;
    return da - db;
  });
}

/**
 * Skeleton placeholder matching the approximate height of an InterviewCard.
 */
function InterviewCardSkeleton() {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        <Skeleton variant="text" width="35%" height={14} sx={{ mb: 0.5 }} />
        <Skeleton variant="text" width="65%" height={22} sx={{ mb: 1.25 }} />
        <Divider sx={{ my: 1 }} />
        <Box sx={{ display: "flex", gap: 1, mb: 1.5, alignItems: "center" }}>
          <Skeleton variant="text" width="55%" height={14} />
          <Skeleton variant="rounded" width={60} height={20} />
        </Box>
        <Skeleton variant="rounded" width={108} height={30} />
      </CardContent>
    </Card>
  );
}

/**
 * Renders the full list of interviews.
 *
 * Fetches interviews via GET /interviews using TanStack Query, sorts them
 * by nearest interview_date ascending, and renders each as an InterviewCard
 * in a responsive MUI Grid.
 *
 * Handles loading state with skeleton cards, surfaces an Alert on
 * fetch failure, and renders an empty state message when no interviews exist.
 */
export function InterviewList() {
  const { data, isLoading, isError } = useQuery<InterviewListResponse>({
    queryKey: ["interviews"],
    queryFn: fetchInterviews,
  });

  const interviews = data ? sortInterviews(data.items) : [];

  if (isError) {
    return (
      <Alert severity="error">
        Failed to load interviews. Please try again.
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Grid container spacing={2}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Grid key={i} size={{ xs: 12, sm: 6, lg: 4 }}>
            <InterviewCardSkeleton />
          </Grid>
        ))}
      </Grid>
    );
  }

  if (interviews.length === 0) {
    return (
      <Box sx={{ py: 8, display: "flex", justifyContent: "center" }}>
        <Typography variant="body2" color="text.secondary">
          No interviews found.
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={2}>
      {interviews.map((interview) => (
        <Grid key={interview.id} size={{ xs: 12, sm: 6, lg: 4 }}>
          <InterviewCard interview={interview} />
        </Grid>
      ))}
    </Grid>
  );
}

export default InterviewList;

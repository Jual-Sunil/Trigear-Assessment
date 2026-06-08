import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Pagination,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Paper,
} from "@mui/material";
import { fetchEmails } from "../../services/api/emailApi";
import type { EmailListResponse, EmailListParams } from "../../services/api/types";

const PAGE_SIZE = 20;

const CLASSIFICATIONS = [
  "Work",
  "Interview",
  "Job Opportunity",
  "Finance",
  "Personal",
  "Promotion",
  "Newsletter",
  "Spam",
  "Other",
];

/**
 * Formats an ISO date string to a short locale date representation.
 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Paginated email list page.
 * Supports filtering by classification label and minimum priority score.
 */
export function Component() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [classification, setClassification] = useState<string>("");
  const [priorityMin, setPriorityMin] = useState<string>("");

  const params: EmailListParams = {
    page,
    page_size: PAGE_SIZE,
    ...(classification ? { classification } : {}),
    ...(priorityMin !== "" ? { priority_min: Number(priorityMin) } : {}),
  };

  const { data, isLoading, isError } = useQuery<EmailListResponse>({
    queryKey: ["emails", params],
    queryFn: () => fetchEmails(params),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  function handleFilterChange() {
    setPage(1);
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb:3 }}>
        Emails
      </Typography>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb:3 }}>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Classification</InputLabel>
          <Select
            value={classification}
            label="Classification"
            onChange={(e) => {
              setClassification(e.target.value);
              handleFilterChange();
            }}
          >
            <MenuItem value="">All</MenuItem>
            {CLASSIFICATIONS.map((c) => (
              <MenuItem key={c} value={c}>
                {c}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Min Priority</InputLabel>
          <Select
            value={priorityMin}
            label="Min Priority"
            onChange={(e) => {
              setPriorityMin(e.target.value);
              handleFilterChange();
            }}
          >
            <MenuItem value="">Any</MenuItem>
            <MenuItem value="25">25+</MenuItem>
            <MenuItem value="50">50+</MenuItem>
            <MenuItem value="70">70+</MenuItem>
            <MenuItem value="90">90+</MenuItem>
          </Select>
        </FormControl>
      </Stack>

      {isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load emails. Please try again.
        </Alert>
      )}

      {isLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Subject</TableCell>
                  <TableCell>From</TableCell>
                  <TableCell>Classification</TableCell>
                  <TableCell>Priority</TableCell>
                  <TableCell>Received</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data?.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py:3 }}>
                        No emails found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {data?.items.map((email) => (
                  <TableRow
                    key={email.id}
                    hover
                    sx={{ cursor: "pointer" }}
                    onClick={() => navigate(`/emails/${email.id}`)}
                  >
                    <TableCell>
                      <Typography variant="body2" noWrap sx={{ maxWidth: 320, fontWeight: 700 }}>
                        {email.subject ?? "(no subject)"}
                      </Typography>
                      {email.snippet && (
                        <Typography variant="caption" color="text.secondary" noWrap  sx={{ maxWidth: 320,display: "block" }}>
                          {email.snippet}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" noWrap>
                        {email.sender_name ?? email.sender_email}
                      </Typography>
                      {email.sender_name && (
                        <Typography variant="caption" color="text.secondary" noWrap  sx={{display:"block"}}>
                          {email.sender_email}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {email.classification ? (
                        <Chip label={email.classification} size="small" />
                      ) : (
                        <Typography variant="caption" color="text.disabled">—</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {email.priority_score ?? "—"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" noWrap>
                        {formatDate(email.received_at)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {totalPages > 1 && (
            <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
              <Pagination
                count={totalPages}
                page={page}
                onChange={(_, value) => setPage(value)}
                color="primary"
              />
            </Box>
          )}

          {data && (
            <Typography variant="caption" color="text.secondary" sx={{display:"block", mt:1, textAlign:"right"}}>
              {data.total} total email{data.total !== 1 ? "s" : ""}
            </Typography>
          )}
        </>
      )}
    </Box>
  );
}

export default Component;

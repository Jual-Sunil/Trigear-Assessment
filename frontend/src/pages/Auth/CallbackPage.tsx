import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Box, CircularProgress, Typography, Alert } from "@mui/material";
import { useAuthCallback } from "../../hooks/useAuth";

/**
 * OAuth2 callback landing page.
 *
 * Google redirects here after the user completes the consent screen.
 * The backend has already exchanged the code and set the HttpOnly session
 * cookie by the time this component mounts. This page calls GET /auth/me
 * to hydrate the Zustand store with the authenticated user, then
 * navigates to the dashboard.
 */
export function Component() {
  const navigate = useNavigate();
  const { resolveCallback, isLoading, error } = useAuthCallback();
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    resolveCallback().then(() => {
      navigate("/", { replace: true });
    });
  }, []);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 2,
      }}
    >
      {!error && (
        <>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary">
            Completing sign-in…
          </Typography>
        </>
      )}

      {error && (
        <Alert
          severity="error"
          sx={{ maxWidth: 400 }}
          action={
            <Typography
              variant="body2"
              sx={{ cursor: "pointer", textDecoration: "underline" }}
              onClick={() => navigate("/login", { replace: true })}
            >
              Try again
            </Typography>
          }
        >
          {error}
        </Alert>
      )}
    </Box>
  );
}

export default Component;
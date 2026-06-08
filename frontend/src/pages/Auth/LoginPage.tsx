import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Paper, Typography, Alert } from "@mui/material";
import EmailIcon from "@mui/icons-material/Email";
import { LoginButton } from "../../components/auth/LoginButton";
import { useAuthStore } from "../../store/authStore";
import { useLogin } from "../../hooks/useAuth";

/**
 * Full-page login screen.
 * Redirects already-authenticated users to the dashboard.
 * Renders the Google OAuth sign-in button for unauthenticated users.
 */
export function Component() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const navigate = useNavigate();
  const { error } = useLogin();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <Paper
        elevation={2}
        sx={{
          px: 6,
          py: 7,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 3,
          maxWidth: 400,
          width: "100%",
          borderRadius: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <EmailIcon color="primary" sx={{ fontSize: 32 }} />
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Mail Intel
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
          AI-powered email intelligence. Sign in with your Google account to
          get started.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ width: "100%" }}>
            {error}
          </Alert>
        )}

        <LoginButton />

        <Typography variant="caption" color="text.disabled" sx={{ textAlign: "center" }}>
          Read-only Gmail access. No emails are modified.
        </Typography>
      </Paper>
    </Box>
  );
}

export default Component;
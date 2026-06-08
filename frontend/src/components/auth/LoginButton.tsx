import { Button, CircularProgress } from "@mui/material";
import GoogleIcon from "@mui/icons-material/Google";
import { useLogin } from "../../hooks/useAuth";

/**
 * Renders a Google sign-in button.
 * On click, calls the backend login endpoint and redirects the browser
 * to the Google OAuth2 consent screen.
 */
export function LoginButton() {
  const { initiateLogin, isLoading } = useLogin();

  return (
    <Button
      variant="contained"
      size="large"
      startIcon={
        isLoading ? (
          <CircularProgress size={18} color="inherit" />
        ) : (
          <GoogleIcon />
        )
      }
      onClick={initiateLogin}
      disabled={isLoading}
      sx={{
        textTransform: "none",
        fontWeight: 600,
        px: 4,
        py: 1.5,
        borderRadius: 2,
      }}
    >
      {isLoading ? "Redirecting…" : "Sign in with Google"}
    </Button>
  );
}
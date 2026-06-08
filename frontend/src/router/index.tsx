import { createBrowserRouter, Navigate } from "react-router-dom";
import App from "../App";
import { AppLayout } from "../layouts/AppLayout";
import { useAuthStore } from "../store/authStore";

/**
 * Guards a route subtree behind authentication.
 * Redirects unauthenticated users to /login.
 */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      {
        path: "/",
        element: (
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        ),
        children: [
          {
            index: true,
            lazy: () => import("../pages/Dashboard/DashboardPage"),
          },
          {
            path: "emails",
            lazy: () => import("../pages/Emails/EmailsPage"),
          },
          {
            path: "emails/:id",
            lazy: () => import("../pages/Emails/EmailDetailPage"),
          },
          {
            path: "tasks",
            lazy: () => import("../pages/Tasks/TasksPage"),
          },
          {
            path: "jobs",
            lazy: () => import("../pages/Jobs/JobsPage"),
          },
          {
            path: "interviews",
            lazy: () => import("../pages/Interviews/InterviewsPage"),
          },
          {
            path: "search",
            lazy: () => import("../pages/Search/SearchPage"),
          },
        ],
      },
      {
        path: "login",
        lazy: () => import("../pages/Auth/LoginPage"),
      },
      {
        path: "auth/callback",
        lazy: () => import("../pages/Auth/CallbackPage"),
      },
    ],
  },
]);

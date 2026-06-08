import { useState } from "react";
import { useAuthStore } from "../store/authStore";
import { fetchLoginUrl, fetchCurrentUser, postLogout } from "../services/api/authApi";
import type { ApiError } from "../services/api/client";

interface UseLoginResult {
  initiateLogin: () => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

/**
 * Provides login initiation logic.
 * Calls GET /auth/login, receives the Google OAuth2 authorization URL,
 * and performs a full browser redirect to begin the consent flow.
 */
export function useLogin(): UseLoginResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function initiateLogin() {
    setIsLoading(true);
    setError(null);
    try {
      const url = await fetchLoginUrl();
      window.location.href = url;
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.message ?? "Failed to initiate login.");
      setIsLoading(false);
    }
  }

  return { initiateLogin, isLoading, error };
}

interface UseCallbackResult {
  resolveCallback: () => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

/**
 * Handles the post-OAuth-callback session hydration.
 * After the backend sets the session cookie, calls GET /auth/me to resolve
 * the authenticated user and persists them in the Zustand store.
 */
export function useAuthCallback(): UseCallbackResult {
  const setUser = useAuthStore((s) => s.setUser);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function resolveCallback() {
    setIsLoading(true);
    setError(null);
    try {
      const user = await fetchCurrentUser();
      setUser(user);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.message ?? "Authentication failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return { resolveCallback, isLoading, error };
}

interface UseLogoutResult {
  logout: () => Promise<void>;
  isLoading: boolean;
}

/**
 * Clears the server session cookie and wipes local Zustand auth state.
 */
export function useLogout(): UseLogoutResult {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [isLoading, setIsLoading] = useState(false);

  async function logout() {
    setIsLoading(true);
    try {
      await postLogout();
    } finally {
      clearAuth();
      setIsLoading(false);
      window.location.href = "/login";
    }
  }

  return { logout, isLoading };
}
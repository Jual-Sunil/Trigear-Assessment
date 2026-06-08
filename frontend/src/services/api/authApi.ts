import { apiClient } from "./client";
import type { LoginResponse } from "./types";
import type { AuthUser } from "../../store/authStore";

/**
 * Fetches the Google OAuth2 authorization URL from the backend.
 * The caller is responsible for redirecting the browser to the returned URL.
 */
export async function fetchLoginUrl(): Promise<string> {
  const { data } = await apiClient.get<LoginResponse>("/auth/login");
  return data.authorization_url;
}

/**
 * Fetches the profile of the currently authenticated user.
 * Relies on the HttpOnly session cookie being present on the request.
 * Throws an ApiError with status 401 if no valid session exists.
 */
export async function fetchCurrentUser(): Promise<AuthUser> {
  const { data } = await apiClient.get<AuthUser>("/auth/me");
  return data;
}

/**
 * Clears the server-side session cookie, effectively logging the user out.
 */
export async function postLogout(): Promise<void> {
  await apiClient.post("/auth/logout");
}
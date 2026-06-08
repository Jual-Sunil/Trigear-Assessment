import axios from "axios";
import type {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "../../store/authStore";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function createApiClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: BASE_URL,
    withCredentials: true,
    timeout: 30_000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    return config;
  });

  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      if (error.response?.status === 401) {
        useAuthStore.getState().clearAuth();
        window.location.href = "/login";
      }
      return Promise.reject(normalizeError(error));
    }
  );

  return instance;
}

function normalizeError(error: AxiosError): ApiError {
  return {
    status: error.response?.status ?? 0,
    message:
      (error.response?.data as { detail?: string })?.detail ??
      error.message ??
      "An unexpected error occurred.",
  };
}

export interface ApiError {
  status: number;
  message: string;
}

export const apiClient = createApiClient();
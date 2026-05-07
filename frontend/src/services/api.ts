import axios from "axios";
import { clearAccessToken, getAccessToken } from "../lib/auth";

const defaultApiBaseUrl = import.meta.env.DEV ? "http://localhost:8000/api" : "/api";
const DEFAULT_API_TIMEOUT_MS = 60000;

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl,
  timeout: DEFAULT_API_TIMEOUT_MS,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAccessToken();
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

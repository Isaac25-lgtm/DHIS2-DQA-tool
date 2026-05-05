import axios from "axios";
import { getAccessToken } from "../lib/auth";

const defaultApiBaseUrl = import.meta.env.DEV ? "http://localhost:8000/api" : "/api";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl,
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

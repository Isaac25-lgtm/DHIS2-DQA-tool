import { api } from "./api";
import type { ApiMessage, AuthUser, LoginPayload, LoginResponse } from "../types";

export const authService = {
  async login(payload: LoginPayload) {
    const { data } = await api.post<LoginResponse>("/auth/login", payload);
    return data;
  },

  async getCurrentUser() {
    const { data } = await api.get<AuthUser>("/auth/me");
    return data;
  },

  async logout() {
    const { data } = await api.post<ApiMessage>("/auth/logout");
    return data;
  },
};


import { api } from "./api";
import type { User, UserFormPayload } from "../types";

export const userService = {
  async listUsers() {
    const { data } = await api.get<User[]>("/users");
    return data;
  },

  async createUser(payload: UserFormPayload) {
    const { data } = await api.post<User>("/users", payload);
    return data;
  },

  async updateUser(userId: string, payload: UserFormPayload) {
    const { data } = await api.put<User>(`/users/${userId}`, payload);
    return data;
  },

  async activateUser(userId: string) {
    const { data } = await api.patch<User>(`/users/${userId}/activate`);
    return data;
  },

  async deactivateUser(userId: string) {
    const { data } = await api.patch<User>(`/users/${userId}/deactivate`);
    return data;
  },

  async deleteUser(userId: string) {
    await api.delete(`/users/${userId}`);
  },
};

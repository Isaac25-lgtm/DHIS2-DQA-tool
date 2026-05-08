import { api } from "./api";
import type { ManagerNotification } from "../types";

export const notificationService = {
  async listManagerNotifications(limit = 20) {
    const response = await api.get<ManagerNotification[]>("/notifications/manager", {
      params: { limit },
    });
    return response.data;
  },
};

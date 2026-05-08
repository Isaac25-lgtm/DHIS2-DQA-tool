import { api } from "./api";
import type { ManagerNotification } from "../types";

export const notificationService = {
  async listManagerNotifications(limit = 20) {
    const response = await api.get<ManagerNotification[]>("/notifications/manager", {
      params: { limit },
    });
    return response.data;
  },
  async markManagerNotificationsSeen(notificationIds: string[]) {
    if (notificationIds.length === 0) {
      return { marked_seen: 0 };
    }
    const response = await api.post<{ marked_seen: number }>("/notifications/manager/mark-seen", {
      notification_ids: notificationIds,
    });
    return response.data;
  },
};

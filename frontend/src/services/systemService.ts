import { api } from "./api";
import type { SystemInfo } from "../types";

export const systemService = {
  async getSystemInfo() {
    const { data } = await api.get<SystemInfo>("/system/info");
    return data;
  },
};

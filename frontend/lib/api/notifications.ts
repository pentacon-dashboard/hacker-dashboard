import { apiFetch } from "./client";

export interface Notification {
  id: string;
  title: string;
  message: string | null;
  severity: "info" | "warning" | "critical";
  category: "price" | "portfolio" | "alert" | "system";
  unread: boolean;
  created_at: string;
}

export interface MarkAllReadResponse {
  marked_count: number;
}

export interface MarkReadResponse {
  id: string;
  unread: boolean;
}

export async function getNotifications(
  limit = 10,
  unread_only = false,
): Promise<Notification[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    unread_only: String(unread_only),
  });
  return apiFetch<Notification[]>(`/notifications?${params}`);
}

export async function markRead(id: string): Promise<MarkReadResponse> {
  return apiFetch<MarkReadResponse>(`/notifications/${encodeURIComponent(id)}/read`, {
    method: "POST",
  });
}

export async function markAllRead(): Promise<MarkAllReadResponse> {
  return apiFetch<MarkAllReadResponse>("/notifications/read-all", {
    method: "POST",
  });
}

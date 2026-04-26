"use client";

import { useQuery } from "@tanstack/react-query";
import { API_BASE } from "@/lib/api/client";

interface DataSettingsResponse {
  refresh_interval_sec: number;
  auto_refresh: boolean;
  auto_backup: boolean;
  cache_size_mb: number;
}

const DEFAULT_DATA_SETTINGS: DataSettingsResponse = {
  refresh_interval_sec: 30,
  auto_refresh: true,
  auto_backup: false,
  cache_size_mb: 128,
};

async function fetchDataSettings(): Promise<DataSettingsResponse> {
  try {
    const res = await fetch(`${API_BASE}/users/me/settings`);
    if (!res.ok) return DEFAULT_DATA_SETTINGS;
    const json = await res.json();
    // BE returns full settings; pluck the "data" sub-object
    const data = json?.data ?? json;
    return {
      refresh_interval_sec:
        typeof data?.refresh_interval_sec === "number"
          ? data.refresh_interval_sec
          : DEFAULT_DATA_SETTINGS.refresh_interval_sec,
      auto_refresh:
        typeof data?.auto_refresh === "boolean"
          ? data.auto_refresh
          : DEFAULT_DATA_SETTINGS.auto_refresh,
      auto_backup:
        typeof data?.auto_backup === "boolean"
          ? data.auto_backup
          : DEFAULT_DATA_SETTINGS.auto_backup,
      cache_size_mb:
        typeof data?.cache_size_mb === "number"
          ? data.cache_size_mb
          : DEFAULT_DATA_SETTINGS.cache_size_mb,
    };
  } catch {
    return DEFAULT_DATA_SETTINGS;
  }
}

export interface UseDataSettingsResult {
  refreshIntervalMs: number;
  autoRefresh: boolean;
}

/**
 * Reads data-refresh settings from /users/me/settings and exposes them as
 * ready-to-use TanStack Query `refetchInterval` values.
 *
 * Invalidate ["users", "me", "settings"] after a PATCH to auto-update callers.
 */
export function useDataSettings(): UseDataSettingsResult {
  const { data } = useQuery<DataSettingsResponse>({
    queryKey: ["users", "me", "settings"],
    queryFn: fetchDataSettings,
    staleTime: 60_000,
    // Never throw — fall back to defaults so callers always get a value
    throwOnError: false,
  });

  const settings = data ?? DEFAULT_DATA_SETTINGS;

  return {
    refreshIntervalMs: settings.refresh_interval_sec * 1_000,
    autoRefresh: settings.auto_refresh,
  };
}

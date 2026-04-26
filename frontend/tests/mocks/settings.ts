/**
 * settings.ts — MSW handlers for /users/me/settings
 *
 * C-7 설정 페이지 픽스처.
 * BE γ-sprint 완료 후 실 엔드포인트로 swap.
 */
import { http, HttpResponse } from "msw";

export const USER_SETTINGS = {
  user_id: "demo",
  display_name: "Demo User",
  email: "demo@example.com",
  language: "ko",
  timezone: "Asia/Seoul",
  notifications: {
    email_alerts: true,
    push_alerts: false,
    price_threshold_pct: 5.0,
    daily_digest: true,
  },
  theme: "dark",
  accent_color: "violet",
  data: {
    refresh_interval_sec: 30,
    auto_refresh: true,
    auto_backup: false,
    cache_size_mb: 128,
  },
  connected_accounts: {
    google: false,
    apple: false,
    kakao: false,
    github: true,
  },
  system: {
    version: "0.3.1-sprint-08",
    api_status: "healthy",
    build_time: new Date(Date.now() - 3600000).toISOString(),
    cache_size_mb: 42,
  },
};

export const settingsHandlers = [
  // GET /users/me/settings
  http.get("http://localhost:8000/users/me/settings", () =>
    HttpResponse.json(USER_SETTINGS),
  ),

  // PATCH /users/me/settings
  http.patch("http://localhost:8000/users/me/settings", async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...USER_SETTINGS, ...patch });
  }),

  // GET /users/me
  http.get("http://localhost:8000/users/me", () =>
    HttpResponse.json({
      user_id: USER_SETTINGS.user_id,
      display_name: USER_SETTINGS.display_name,
      email: USER_SETTINGS.email,
    }),
  ),
];

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
  // GET /health
  http.get("http://localhost:8000/health", () =>
    HttpResponse.json({
      status: "ok",
      services: {
        db: "ok",
        redis: "ok",
      },
      uptime_seconds: 3600,
      version: USER_SETTINGS.system.version,
    }),
  ),

  // GET /notifications
  http.get("http://localhost:8000/notifications", ({ request }) => {
    const url = new URL(request.url);
    const unreadOnly = url.searchParams.get("unread_only") === "true";
    const limit = Number(url.searchParams.get("limit") ?? 10);
    const notifications = [
      {
        id: "demo-risk-alert",
        title: "리스크 점검",
        message: "고객 A 포트폴리오의 암호화폐 비중을 확인하세요.",
        severity: "warning",
        category: "portfolio",
        unread: true,
        created_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
      },
      {
        id: "demo-system-ok",
        title: "데이터 동기화 완료",
        message: "고객장부 목업 데이터가 최신 상태입니다.",
        severity: "info",
        category: "system",
        unread: false,
        created_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
      },
    ];
    const filtered = unreadOnly
      ? notifications.filter((notification) => notification.unread)
      : notifications;
    return HttpResponse.json(filtered.slice(0, limit));
  }),

  // POST /notifications/read-all
  http.post("http://localhost:8000/notifications/read-all", () =>
    HttpResponse.json({ marked_count: 1 }),
  ),

  // POST /notifications/{id}/read
  http.post(/\/notifications\/[^/]+\/read$/, ({ request }) => {
    const id = request.url.split("/").at(-2) ?? "";
    return HttpResponse.json({ id, unread: false });
  }),

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

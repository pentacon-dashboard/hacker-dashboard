"use client";

/**
 * MswProvider — 브라우저 MSW 워커 부트스트랩.
 *
 * - Copilot SSE 모킹은 기존대로 Next.js API Route(app/api/copilot/query/route.ts)가 처리.
 * - 대시보드(/portfolio/summary, /portfolio/snapshots, /search/news) 등 추가 엔드포인트의
 *   브라우저 레벨 모킹이 필요할 때 NEXT_PUBLIC_USE_MSW_WORKER=1 (또는 NEXT_PUBLIC_COPILOT_MOCK=1)
 *   로 활성화. Backend가 없어도 데모 수치로 전체 대시보드가 렌더된다.
 */
import { useEffect, useState } from "react";

const WORKER_ENABLED =
  process.env["NEXT_PUBLIC_USE_MSW_WORKER"] === "1" ||
  process.env["NEXT_PUBLIC_COPILOT_MOCK"] === "1";

export function MswProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(!WORKER_ENABLED);

  useEffect(() => {
    if (!WORKER_ENABLED) return;
    let cancelled = false;
    (async () => {
      const { worker } = await import("@/tests/mocks/browser");
      await worker.start({
        onUnhandledRequest: "bypass",
        serviceWorker: { url: "/mockServiceWorker.js" },
      });
      if (!cancelled) setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) return null;
  return <>{children}</>;
}

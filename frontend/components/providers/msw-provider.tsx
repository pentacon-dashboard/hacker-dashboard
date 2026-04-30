"use client";

/**
 * Browser MSW is only for customer/portfolio demo data.
 * Market data, news, watchlist, realtime quotes, and Copilot pass through to
 * the real backend/API unless a route-specific test explicitly mocks them.
 */
import { useEffect, useState } from "react";

const WORKER_ENABLED =
  process.env["NEXT_PUBLIC_CLIENT_MOCK"] === "1" ||
  process.env["NEXT_PUBLIC_USE_MSW_WORKER"] === "1";

export function MswProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(!WORKER_ENABLED);

  useEffect(() => {
    if (!WORKER_ENABLED) return;
    let cancelled = false;
    (async () => {
      try {
        const { worker } = await import("@/tests/mocks/browser");
        await worker.start({
          onUnhandledRequest: "bypass",
          serviceWorker: { url: "/mockServiceWorker.js" },
        });
      } catch {
        // Playwright can block service workers while route mocks cover API calls.
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) return null;
  return <>{children}</>;
}

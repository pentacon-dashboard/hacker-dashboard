import { Suspense } from "react";
import { WatchlistPageClient } from "@/components/watchlist/watchlist-page-client";

export const dynamic = "force-dynamic";

export default function WatchlistPage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
          관심 종목을 불러오는 중입니다.
        </div>
      }
    >
      <WatchlistPageClient />
    </Suspense>
  );
}

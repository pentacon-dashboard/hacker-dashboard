import { WatchlistTable } from "@/components/watchlist/watchlist-table";

export const dynamic = "force-dynamic";

export default function WatchlistPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">워치리스트</h1>
        <p className="text-sm text-muted-foreground">
          관심 종목을 추가하고 실시간 시세를 확인하세요.
        </p>
      </div>
      <WatchlistTable />
    </div>
  );
}

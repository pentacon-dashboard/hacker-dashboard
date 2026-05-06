import { Suspense } from "react";
import { NewsPageClient } from "@/components/news/news-page-client";

export const dynamic = "force-dynamic";

export default function NewsPage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
          관련 뉴스를 불러오는 중입니다.
        </div>
      }
    >
      <NewsPageClient />
    </Suspense>
  );
}

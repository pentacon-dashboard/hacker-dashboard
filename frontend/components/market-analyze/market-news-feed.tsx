"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Newspaper, TrendingUp, TrendingDown, Minus, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";

interface NewsItem {
  id: string;
  title: string;
  source: string;
  published_at: string;
  url: string;
  sentiment?: "positive" | "negative" | "neutral";
}

interface MarketNewsFeedProps {
  news: NewsItem[];
  loading?: boolean;
}

export function MarketNewsFeed({ news, loading }: MarketNewsFeedProps) {
  const { t } = useLocale();

  function formatTime(iso: string): string {
    try {
      const d = new Date(iso);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffH = Math.floor(diffMs / 3600000);
      if (diffH < 1) return t("market.timeAgo.justNow");
      if (diffH < 24) return t("market.timeAgo.hoursAgo", { n: diffH });
      return t("market.timeAgo.daysAgo", { n: Math.floor(diffH / 24) });
    } catch {
      return iso;
    }
  }

  return (
    <Card data-testid="market-news-feed">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Newspaper className="h-4 w-4 text-primary" aria-hidden="true" />
          {t("market.mainNews")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading && (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-muted/20" />
            ))}
          </div>
        )}

        {!loading && news.length === 0 && (
          <div className="py-6 text-center text-sm text-muted-foreground">{t("market.noNews")}</div>
        )}

        {!loading &&
          news.map((item) => {
            const sentiment = item.sentiment ?? "neutral";
            return (
              <a
                key={item.id}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-2.5 rounded-lg border border-border bg-card/50 px-3 py-2 transition-colors hover:border-primary/40 hover:bg-muted/30"
                data-testid={`news-${item.id}`}
              >
                {/* 감성 아이콘 */}
                <div
                  className={cn(
                    "mt-0.5 shrink-0 rounded p-0.5",
                    sentiment === "positive"
                      ? "bg-green-500/20 text-green-500"
                      : sentiment === "negative"
                        ? "bg-destructive/20 text-destructive"
                        : "bg-muted text-muted-foreground",
                  )}
                >
                  {sentiment === "positive" ? (
                    <TrendingUp className="h-3 w-3" aria-hidden="true" />
                  ) : sentiment === "negative" ? (
                    <TrendingDown className="h-3 w-3" aria-hidden="true" />
                  ) : (
                    <Minus className="h-3 w-3" aria-hidden="true" />
                  )}
                </div>

                {/* 제목 + 메타 */}
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-2 text-xs font-medium leading-snug">{item.title}</p>
                  <div className="mt-1 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <span className="font-semibold">{item.source}</span>
                    <span>·</span>
                    <span>{formatTime(item.published_at)}</span>
                  </div>
                </div>

                <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/40" aria-hidden="true" />
              </a>
            );
          })}
      </CardContent>
    </Card>
  );
}

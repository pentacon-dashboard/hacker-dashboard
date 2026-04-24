"use client";

import { useEffect, useState } from "react";
import { IndexKpiStrip, type IndexSnapshot } from "@/components/market-analyze/index-kpi-strip";
import { WorldHeatmap, type CountryHeatmapItem } from "@/components/market-analyze/world-heatmap";
import { SectorKpiGrid, type SectorItem } from "@/components/market-analyze/sector-kpi-grid";
import { CommodityPanel, type CommodityItem } from "@/components/market-analyze/commodity-panel";
import { MarketNewsFeed } from "@/components/market-analyze/market-news-feed";
import { API_BASE } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n/locale-provider";

// BE 실 스키마 기반 NewsItem (search/news 응답 구조)
interface NewsItem {
  doc_id: number;
  chunk_id: number;
  source_url: string;
  title: string;
  published_at: string;
  excerpt: string;
  score?: number;
}

// MarketNewsFeed 내부 interface 와 매핑
interface MappedNewsItem {
  id: string;
  title: string;
  source: string;
  published_at: string;
  url: string;
  sentiment?: "positive" | "negative" | "neutral";
}

function mapNewsItem(item: NewsItem): MappedNewsItem {
  return {
    id: String(item.chunk_id),
    title: item.title,
    source: new URL(item.source_url).hostname.replace("www.", ""),
    published_at: item.published_at,
    url: item.source_url,
  };
}

async function safeFetch<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url);
    if (!res.ok) return fallback;
    return res.json() as Promise<T>;
  } catch {
    return fallback;
  }
}

export default function MarketAnalyzePage() {
  const { t } = useLocale();
  const [indices, setIndices] = useState<IndexSnapshot[]>([]);
  const [sectors, setSectors] = useState<SectorItem[]>([]);
  const [commodities, setCommodities] = useState<CommodityItem[]>([]);
  const [heatmap, setHeatmap] = useState<CountryHeatmapItem[]>([]);
  const [news, setNews] = useState<MappedNewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      safeFetch<IndexSnapshot[]>(`${API_BASE}/market/indices`, []),
      safeFetch<SectorItem[]>(`${API_BASE}/market/sectors`, []),
      safeFetch<CommodityItem[]>(`${API_BASE}/market/commodities`, []),
      safeFetch<CountryHeatmapItem[]>(`${API_BASE}/market/world-heatmap`, []),
      // /market/news 없음 → /search/news?query=market 사용
      safeFetch<NewsItem[]>(`${API_BASE}/search/news?query=market&limit=6`, []),
    ]).then(([idx, sec, com, hm, n]) => {
      setIndices(Array.isArray(idx) ? idx : []);
      setSectors(Array.isArray(sec) ? sec : []);
      setCommodities(Array.isArray(com) ? com : []);
      setHeatmap(Array.isArray(hm) ? hm : []);
      setNews(Array.isArray(n) ? n.map(mapNewsItem) : []);
      setLoading(false);
    });
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("market.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("market.subtitle")}
        </p>
      </div>

      {/* 1. 상단 KPI Strip — 7 지수 */}
      <IndexKpiStrip indices={indices} loading={loading} />

      {/* 2. 중단: 히트맵(좌) + 섹터(우) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <WorldHeatmap data={heatmap} loading={loading} />
        </div>
        <div className="lg:col-span-4">
          <SectorKpiGrid sectors={sectors} loading={loading} />
        </div>
      </div>

      {/* 3. 하단: 원자재(좌) + 뉴스(우) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CommodityPanel commodities={commodities} loading={loading} />
        <MarketNewsFeed news={news} loading={loading} />
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { IndexKpiStrip } from "@/components/market-analyze/index-kpi-strip";
import { WorldHeatmap } from "@/components/market-analyze/world-heatmap";
import { SectorKpiGrid } from "@/components/market-analyze/sector-kpi-grid";
import { CommodityPanel } from "@/components/market-analyze/commodity-panel";
import { MarketNewsFeed } from "@/components/market-analyze/market-news-feed";
import { API_BASE } from "@/lib/api/client";

// TODO: BE β-sprint 완료 후 실 엔드포인트 연결 (현재 MSW stub 사용)

interface IndexKpi {
  code: string;
  name: string;
  value: number;
  change_pct: number;
  sparkline: number[];
}

interface SectorData {
  sector: string;
  change_pct: number;
  market_cap_b?: number;
}

interface CommodityData {
  code: string;
  name: string;
  value: number;
  unit: string;
  change_pct: number;
  sparkline: number[];
}

interface RegionData {
  region: string;
  countries: string[];
  avg_change_pct: number;
}

interface NewsItem {
  id: string;
  title: string;
  source: string;
  published_at: string;
  url: string;
  sentiment?: "positive" | "negative" | "neutral";
}

async function safeFetch<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url, { next: { revalidate: 60 } });
    if (!res.ok) return fallback;
    return res.json() as Promise<T>;
  } catch {
    return fallback;
  }
}

export default function MarketAnalyzePage() {
  const [indices, setIndices] = useState<IndexKpi[]>([]);
  const [sectors, setSectors] = useState<SectorData[]>([]);
  const [commodities, setCommodities] = useState<CommodityData[]>([]);
  const [heatmap, setHeatmap] = useState<RegionData[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      safeFetch<IndexKpi[]>(`${API_BASE}/market/indices`, []),
      safeFetch<SectorData[]>(`${API_BASE}/market/sectors`, []),
      safeFetch<CommodityData[]>(`${API_BASE}/market/commodities`, []),
      safeFetch<RegionData[]>(`${API_BASE}/market/world-heatmap`, []),
      safeFetch<NewsItem[]>(`${API_BASE}/market/news`, []),
    ]).then(([idx, sec, com, hm, n]) => {
      setIndices(idx);
      setSectors(sec);
      setCommodities(com);
      setHeatmap(hm);
      setNews(n);
      setLoading(false);
    });
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">시장 분석</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          글로벌 지수, 섹터, 원자재 및 세계 히트맵을 한눈에 확인합니다.
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

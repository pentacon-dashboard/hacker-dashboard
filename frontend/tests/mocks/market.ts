/**
 * market.ts — MSW handlers for /market/* endpoints
 *
 * C-4 시장분석 페이지 결정론적 픽스처.
 * BE β-sprint 완료 후 실 엔드포인트로 swap.
 */
import { http, HttpResponse } from "msw";

export const MARKET_INDICES = [
  {
    code: "KOSPI",
    name: "KOSPI",
    value: 2705.32,
    change_pct: 1.24,
    sparkline: [2645, 2658, 2672, 2680, 2668, 2690, 2705],
  },
  {
    code: "KOSDAQ",
    name: "KOSDAQ",
    value: 864.72,
    change_pct: -0.38,
    sparkline: [870, 875, 868, 872, 865, 862, 864],
  },
  {
    code: "SP500",
    name: "S&P 500",
    value: 5306.04,
    change_pct: 0.57,
    sparkline: [5260, 5275, 5288, 5270, 5295, 5300, 5306],
  },
  {
    code: "NASDAQ",
    name: "나스닥",
    value: 18720.02,
    change_pct: 0.84,
    sparkline: [18500, 18580, 18620, 18560, 18650, 18700, 18720],
  },
  {
    code: "DOW",
    name: "DOW",
    value: 38972.86,
    change_pct: -0.21,
    sparkline: [39100, 39050, 38980, 39020, 38950, 38940, 38972],
  },
  {
    code: "VIX",
    name: "VIX",
    value: 18.34,
    change_pct: 5.12,
    sparkline: [16.2, 16.8, 17.5, 18.1, 17.8, 18.0, 18.34],
  },
  {
    code: "USDKRW",
    name: "USD/KRW",
    value: 1389.63,
    change_pct: 0.32,
    sparkline: [1382, 1385, 1387, 1384, 1388, 1390, 1389],
  },
];

export const MARKET_SECTORS = [
  { sector: "Technology", change_pct: 1.85, market_cap_b: 12400 },
  { sector: "Healthcare", change_pct: 0.42, market_cap_b: 6800 },
  { sector: "Financials", change_pct: -0.31, market_cap_b: 8200 },
  { sector: "Consumer Disc.", change_pct: 0.95, market_cap_b: 5400 },
  { sector: "Industrials", change_pct: 0.18, market_cap_b: 4900 },
  { sector: "Communication", change_pct: 1.24, market_cap_b: 5800 },
  { sector: "Consumer Staples", change_pct: -0.55, market_cap_b: 4200 },
  { sector: "Energy", change_pct: -1.20, market_cap_b: 3800 },
  { sector: "Utilities", change_pct: 0.08, market_cap_b: 2100 },
  { sector: "Real Estate", change_pct: -0.72, market_cap_b: 2600 },
  { sector: "Materials", change_pct: 0.33, market_cap_b: 2900 },
];

export const MARKET_COMMODITIES = [
  {
    code: "OIL",
    name: "원유(WTI)",
    value: 78.42,
    unit: "USD/배럴",
    change_pct: -0.85,
    sparkline: [80.2, 79.5, 79.8, 79.1, 78.8, 78.6, 78.42],
  },
  {
    code: "GOLD",
    name: "금",
    value: 2342.10,
    unit: "USD/온스",
    change_pct: 0.54,
    sparkline: [2310, 2318, 2325, 2330, 2335, 2340, 2342],
  },
  {
    code: "SILVER",
    name: "은",
    value: 27.85,
    unit: "USD/온스",
    change_pct: 0.91,
    sparkline: [27.1, 27.3, 27.5, 27.4, 27.6, 27.8, 27.85],
  },
  {
    code: "COPPER",
    name: "구리",
    value: 4.56,
    unit: "USD/파운드",
    change_pct: -0.22,
    sparkline: [4.61, 4.59, 4.57, 4.58, 4.56, 4.55, 4.56],
  },
  {
    code: "NATGAS",
    name: "천연가스",
    value: 2.14,
    unit: "USD/MMBtu",
    change_pct: -1.38,
    sparkline: [2.22, 2.20, 2.18, 2.17, 2.16, 2.15, 2.14],
  },
];

export const MARKET_WORLD_HEATMAP = [
  { region: "동아시아", countries: ["한국", "일본", "중국", "대만"], avg_change_pct: 0.84 },
  { region: "동남아시아", countries: ["싱가포르", "태국", "인니"], avg_change_pct: 0.32 },
  { region: "북미", countries: ["미국", "캐나다"], avg_change_pct: 0.71 },
  { region: "유럽", countries: ["영국", "독일", "프랑스", "이탈리아"], avg_change_pct: -0.18 },
  { region: "남미", countries: ["브라질", "멕시코"], avg_change_pct: -0.95 },
  { region: "중동·아프리카", countries: ["UAE", "남아공"], avg_change_pct: 0.12 },
  { region: "오세아니아", countries: ["호주", "뉴질랜드"], avg_change_pct: 0.45 },
  { region: "인도·남아시아", countries: ["인도", "파키스탄"], avg_change_pct: 1.20 },
];

export const MARKET_NEWS = [
  {
    id: "mn1",
    title: "Fed, 금리 동결 유지…인플레이션 지표 주목",
    source: "Reuters",
    published_at: new Date(Date.now() - 3600000).toISOString(),
    url: "#",
    sentiment: "neutral",
  },
  {
    id: "mn2",
    title: "엔비디아 실적 어닝 서프라이즈…AI 반도체 수요 급증",
    source: "Bloomberg",
    published_at: new Date(Date.now() - 7200000).toISOString(),
    url: "#",
    sentiment: "positive",
  },
  {
    id: "mn3",
    title: "중국 PMI 예상 하회…글로벌 경기 둔화 우려",
    source: "Yonhap",
    published_at: new Date(Date.now() - 10800000).toISOString(),
    url: "#",
    sentiment: "negative",
  },
  {
    id: "mn4",
    title: "KOSPI, 외국인 순매수에 2700 돌파 시도",
    source: "Hankyung",
    published_at: new Date(Date.now() - 14400000).toISOString(),
    url: "#",
    sentiment: "positive",
  },
];

export const marketHandlers = [
  http.get("http://localhost:8000/market/indices", () =>
    HttpResponse.json(MARKET_INDICES),
  ),
  http.get("http://localhost:8000/market/sectors", () =>
    HttpResponse.json(MARKET_SECTORS),
  ),
  http.get("http://localhost:8000/market/commodities", () =>
    HttpResponse.json(MARKET_COMMODITIES),
  ),
  http.get("http://localhost:8000/market/world-heatmap", () =>
    HttpResponse.json(MARKET_WORLD_HEATMAP),
  ),
  http.get("http://localhost:8000/market/news", () =>
    HttpResponse.json(MARKET_NEWS),
  ),
];

"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  ComposedChart,
  Bar,
  CartesianGrid,
} from "recharts";
import { useLocale } from "@/lib/i18n/locale-provider";

export interface RsiPoint {
  t: string;
  v: number | null;
}

export interface MacdPoint {
  t: string;
  macd: number | null;
  signal: number | null;
  histogram: number | null;
}

export interface IndicatorSubchartsProps {
  rsi: RsiPoint[];
  macd: MacdPoint[];
  isLoading?: boolean;
}

/** ISO timestamp → MM/DD 또는 HH:MM */
function formatTick(t: string): string {
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return t.slice(5, 10);
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const da = String(d.getDate()).padStart(2, "0");
  return `${mo}/${da}`;
}

/** 표시할 x축 틱: 최대 5개만 균등 추출 */
function sampledTicks(data: { t: string }[], maxTicks = 5): string[] {
  if (data.length === 0) return [];
  if (data.length <= maxTicks) return data.map((d) => d.t);
  const step = Math.floor((data.length - 1) / (maxTicks - 1));
  return Array.from({ length: maxTicks }, (_, i) => {
    const idx = Math.min(i * step, data.length - 1);
    return data[idx]!.t;
  });
}

// ─── RSI 서브차트 ──────────────────────────────────────────────────────────

interface RsiSubchartProps {
  data: RsiPoint[];
}

function RsiSubchart({ data }: RsiSubchartProps) {
  const validData = data.filter((p) => p.v !== null) as Array<{ t: string; v: number }>;
  const latest = validData.at(-1)?.v;
  const ticks = sampledTicks(validData);

  return (
    <div
      className="rounded-lg border bg-card"
      data-testid="indicator-subchart-rsi"
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between px-3 py-2 border-b">
        <span className="text-xs font-semibold text-muted-foreground">RSI (14)</span>
        {latest !== undefined && (
          <span className="text-xs font-bold tabular-nums">
            RSI:{" "}
            <span
              className={
                latest >= 70
                  ? "text-red-500 dark:text-red-400"
                  : latest <= 30
                    ? "text-emerald-500 dark:text-emerald-400"
                    : "text-foreground"
              }
            >
              {latest.toFixed(2)}
            </span>
          </span>
        )}
      </div>

      {/* 차트 영역 */}
      <div className="h-[120px] w-full px-1 py-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={validData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
            {/* 과매도 영역: 0~30 녹색 */}
            <ReferenceArea y1={0} y2={30} fill="#10b981" fillOpacity={0.08} />
            {/* 과매수 영역: 70~100 빨강 */}
            <ReferenceArea y1={70} y2={100} fill="#ef4444" fillOpacity={0.08} />

            <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
            <XAxis
              dataKey="t"
              ticks={ticks}
              tickFormatter={formatTick}
              tick={{ fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 30, 70, 100]}
              tick={{ fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={28}
            />
            <Tooltip
              formatter={(value: number) => [value.toFixed(2), "RSI"]}
              labelFormatter={formatTick}
              contentStyle={{ fontSize: 11 }}
            />
            {/* 기준선 */}
            <ReferenceLine y={30} stroke="#10b981" strokeDasharray="4 3" strokeWidth={1} />
            <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="4 3" strokeWidth={1} />
            <Line
              type="monotone"
              dataKey="v"
              stroke="#6366f1"
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── MACD 서브차트 ─────────────────────────────────────────────────────────

interface MacdSubchartProps {
  data: MacdPoint[];
}

type ValidMacdPoint = {
  t: string;
  macd: number;
  signal: number;
  histogram: number;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isValidMacdPoint(point: MacdPoint): point is ValidMacdPoint {
  return (
    isFiniteNumber(point.macd) &&
    isFiniteNumber(point.signal) &&
    isFiniteNumber(point.histogram)
  );
}

function MacdSubchart({ data }: MacdSubchartProps) {
  const { t } = useLocale();
  const validData = data.filter(isValidMacdPoint);
  const latest = validData.at(-1);
  const ticks = sampledTicks(validData);

  // 양봉/음봉 색상을 각 막대에 적용하기 위해 포매팅 함수 활용
  const barFill = (value: number) => (value >= 0 ? "#10b981" : "#ef4444");

  return (
    <div
      className="rounded-lg border bg-card"
      data-testid="indicator-subchart-macd"
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between px-3 py-2 border-b">
        <span className="text-xs font-semibold text-muted-foreground">MACD</span>
        {latest !== undefined && (
          <span className="text-xs font-bold tabular-nums">
            MACD:{" "}
            <span
              className={
                latest.macd >= 0
                  ? "text-emerald-500 dark:text-emerald-400"
                  : "text-red-500 dark:text-red-400"
              }
            >
              {latest.macd.toFixed(2)}
            </span>
            ,{" "}
            <span className="font-medium text-muted-foreground">Signal:</span>{" "}
            {latest.signal.toFixed(2)}
          </span>
        )}
      </div>

      {/* 차트 영역 */}
      <div className="h-[120px] w-full px-1 py-1">
        {validData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            {t("symbol.noIndicator")}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={validData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis
                dataKey="t"
                ticks={ticks}
                tickFormatter={formatTick}
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={36}
                tickFormatter={(v: number) => v.toFixed(1)}
              />
              <Tooltip
                formatter={(value: unknown, name: string) => [
                  isFiniteNumber(value) ? value.toFixed(2) : "-",
                  name === "histogram" ? t("symbol.macd.histogram") : name === "macd" ? "MACD" : "Signal",
                ]}
                labelFormatter={formatTick}
                contentStyle={{ fontSize: 11 }}
              />
              {/* 0 기준선 */}
              <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />

              {/* 히스토그램 막대: Cell-level 색상은 ComposedChart 에서는 fill prop 으로 전달 */}
              <Bar
                dataKey="histogram"
                fill="#10b981"
                opacity={0.75}
                // recharts Bar 의 Cell-per-bar 색상: Cell 컴포넌트 대신 함수형 fill 사용
                // 음수 막대는 빨강으로 — recharts가 함수형 fill을 지원하므로 활용
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                shape={(props: any) => {
                  const { x, y, width, height, value } = props as {
                    x: number;
                    y: number;
                    width: number;
                    height: number;
                    value: number;
                  };
                  // SVG rect는 음수 height 불허. recharts가 음수 값에 음수 height를 줄 수 있으므로
                  // abs 변환 후 y 위치를 보정.
                  const absHeight = Math.abs(height);
                  const rectY = height < 0 ? y + height : y;
                  const color = barFill(value);
                  return (
                    <rect
                      x={x}
                      y={rectY}
                      width={width}
                      height={absHeight}
                      fill={color}
                      fillOpacity={0.75}
                    />
                  );
                }}
              />

              {/* MACD 라인 */}
              <Line
                type="monotone"
                dataKey="macd"
                stroke="#3b82f6"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
              />
              {/* Signal 라인 */}
              <Line
                type="monotone"
                dataKey="signal"
                stroke="#f59e0b"
                strokeWidth={1.5}
                dot={false}
                strokeDasharray="4 3"
                activeDot={{ r: 3 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

// ─── 메인 export ───────────────────────────────────────────────────────────

export function IndicatorSubcharts({
  rsi,
  macd,
  isLoading = false,
}: IndicatorSubchartsProps) {
  const { t } = useLocale();

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="indicator-subcharts-loading">
        <div className="h-[156px] animate-pulse rounded-lg bg-muted" />
        <div className="h-[156px] animate-pulse rounded-lg bg-muted" />
      </div>
    );
  }

  if (rsi.length === 0 && macd.length === 0) {
    return (
      <div
        className="flex h-24 items-center justify-center rounded-lg border bg-muted/30 text-sm text-muted-foreground"
        data-testid="indicator-subcharts-empty"
      >
        {t("symbol.noIndicator")}
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="indicator-subcharts">
      {rsi.length > 0 && <RsiSubchart data={rsi} />}
      {macd.length > 0 && <MacdSubchart data={macd} />}
    </div>
  );
}

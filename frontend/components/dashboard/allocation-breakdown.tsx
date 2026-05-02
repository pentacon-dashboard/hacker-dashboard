"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { formatKRWCompact } from "@/lib/utils/format";
import { useLocale } from "@/lib/i18n/locale-provider";
import { cn } from "@/lib/utils";

export interface AllocationSlice {
  key: string;
  name: string;
  ratio: number;
  value_krw: number;
  color: string;
}

interface AllocationBreakdownProps {
  data: AllocationSlice[];
  compact?: boolean;
}

export function AllocationBreakdown({ data, compact = false }: AllocationBreakdownProps) {
  const { t } = useLocale();
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        {t("dashboard.emptyHoldings")}
      </div>
    );
  }

  const pieData = data.map((d) => ({
    name: d.name,
    value: Number((d.ratio * 100).toFixed(2)),
    color: d.color,
  }));
  const largestSlice = data.reduce(
    (largest, item) => (item.ratio > largest.ratio ? item : largest),
    data[0]!,
  );
  const topThreeRatio = data
    .slice(0, 3)
    .reduce((sum, item) => sum + item.ratio, 0);
  const innerRadius = compact ? 40 : 48;
  const outerRadius = compact ? 62 : 76;

  return (
    <div
      className={cn(
        "gap-3",
        compact
          ? "flex h-full min-h-[260px] flex-col justify-between"
          : "grid grid-cols-1 md:grid-cols-2",
      )}
      data-testid="allocation-breakdown"
    >
      <div
        className={cn(
          "grid grid-cols-1 gap-3",
          compact
            ? "items-center xl:grid-cols-[minmax(132px,144px)_minmax(0,1fr)]"
            : "md:grid-cols-2",
        )}
      >
        <div
          className={cn(
            "min-w-0 overflow-visible",
            compact ? "mx-auto h-40 w-full max-w-[144px] xl:mx-0" : "h-48",
          )}
          data-testid="allocation-pie-frame"
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={innerRadius}
                outerRadius={outerRadius}
                dataKey="value"
                isAnimationActive={false}
              >
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number, _name: string, ctx) => [
                  `${value.toFixed(1)}%`,
                  ctx.payload?.name ?? "",
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <ul
          className={cn(
            "flex min-w-0 flex-col justify-center text-xs",
            compact ? "gap-2.5" : "gap-2",
          )}
          data-testid={compact ? "allocation-compact-legend" : undefined}
        >
          {data.map((d) => (
            <li
              key={d.key}
              className={cn(
                "gap-2",
                compact
                  ? "grid grid-cols-[minmax(0,1fr)_auto] items-center"
                  : "flex items-center justify-between",
              )}
            >
              <span className="flex min-w-0 items-center gap-2">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: d.color }}
                  aria-hidden="true"
                />
                <span
                  className={cn(
                    compact
                      ? "break-keep leading-tight"
                      : "truncate",
                  )}
                >
                  {d.name}
                </span>
              </span>
              <span
                className={cn(
                  "shrink-0 text-right tabular-nums",
                  compact ? "font-semibold" : "",
                )}
              >
                {compact ? (
                  `${(d.ratio * 100).toFixed(1)}%`
                ) : (
                  <>
                    <span className="font-semibold">
                      {formatKRWCompact(d.value_krw)}
                    </span>
                    <span className="ml-2 text-muted-foreground">
                      {(d.ratio * 100).toFixed(1)}%
                    </span>
                  </>
                )}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {compact ? (
        <div className="space-y-3 pt-1" data-testid="allocation-compact-summary">
          <div
            className="flex h-2.5 overflow-hidden rounded-full bg-muted"
            aria-label="자산 배분 누적 비중"
          >
            {data.map((slice) => (
              <span
                key={slice.key}
                className="h-full"
                style={{
                  width: `${Math.max(slice.ratio * 100, 1)}%`,
                  backgroundColor: slice.color,
                }}
              />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-2 text-[11px] leading-tight">
            <div className="rounded-md bg-muted/40 px-2 py-1.5">
              <p className="break-keep text-muted-foreground">최대 비중</p>
              <p className="mt-1 break-keep font-semibold tabular-nums">
                {(largestSlice.ratio * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-md bg-muted/40 px-2 py-1.5">
              <p className="break-keep text-muted-foreground">분류 수</p>
              <p className="mt-1 font-semibold tabular-nums">{data.length}</p>
            </div>
            <div className="rounded-md bg-muted/40 px-2 py-1.5">
              <p className="break-keep text-muted-foreground">상위 3</p>
              <p className="mt-1 font-semibold tabular-nums">
                {(topThreeRatio * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

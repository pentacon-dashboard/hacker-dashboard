"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { formatKRWCompact } from "@/lib/utils/format";

export interface AllocationSlice {
  key: string;
  name: string;
  ratio: number;
  value_krw: number;
  color: string;
}

interface AllocationBreakdownProps {
  data: AllocationSlice[];
}

export function AllocationBreakdown({ data }: AllocationBreakdownProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        보유 자산 없음
      </div>
    );
  }

  const pieData = data.map((d) => ({
    name: d.name,
    value: Number((d.ratio * 100).toFixed(2)),
    color: d.color,
  }));

  return (
    <div
      className="grid grid-cols-1 gap-3 md:grid-cols-2"
      data-testid="allocation-breakdown"
    >
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              innerRadius={48}
              outerRadius={76}
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

      <ul className="flex flex-col justify-center gap-2 text-xs">
        {data.map((d) => (
          <li
            key={d.key}
            className="flex items-center justify-between gap-2"
          >
            <span className="flex min-w-0 items-center gap-2">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: d.color }}
                aria-hidden="true"
              />
              <span className="truncate">{d.name}</span>
            </span>
            <span className="shrink-0 text-right tabular-nums">
              <span className="font-semibold">
                {formatKRWCompact(d.value_krw)}
              </span>
              <span className="ml-2 text-muted-foreground">
                {(d.ratio * 100).toFixed(1)}%
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

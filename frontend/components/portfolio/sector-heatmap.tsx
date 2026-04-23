"use client";

import { useState } from "react";

export interface SectorHeatmapTile {
  sector: string;
  weight_pct: string;
  pnl_pct: string;
  /** -0.5 ~ +1.0 로 정규화된 색 강도 */
  intensity: string;
}

interface SectorHeatmapProps {
  tiles: SectorHeatmapTile[];
}

/** intensity (-1~+1) → hsl 색상 계산 */
function intensityToColor(intensity: number): string {
  if (intensity >= 0) {
    // 0 → gray(#374151), +1 → 진녹색(#16a34a)
    const t = Math.min(intensity, 1);
    const r = Math.round(55 - 39 * t);
    const g = Math.round(65 + 95 * t);
    const b = Math.round(81 - 7 * t);
    return `rgb(${r},${g},${b})`;
  } else {
    // 0 → gray(#374151), -1 → 진빨강(#dc2626)
    const t = Math.min(Math.abs(intensity), 1);
    const r = Math.round(55 + 165 * t);
    const g = Math.round(65 - 40 * t);
    const b = Math.round(81 - 53 * t);
    return `rgb(${r},${g},${b})`;
  }
}

function textColorForIntensity(intensity: number): string {
  return Math.abs(intensity) > 0.4 ? "text-white" : "text-foreground";
}

interface TooltipState {
  tile: SectorHeatmapTile;
  x: number;
  y: number;
}

export function SectorHeatmap({ tiles }: SectorHeatmapProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  if (tiles.length === 0) {
    return (
      <div
        className="flex h-40 items-center justify-center text-sm text-muted-foreground"
        data-testid="sector-heatmap-empty"
      >
        섹터 데이터 없음
      </div>
    );
  }

  function handleMouseEnter(
    e: React.MouseEvent<HTMLButtonElement>,
    tile: SectorHeatmapTile,
  ) {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({ tile, x: rect.left + rect.width / 2, y: rect.top });
  }

  function handleMouseLeave() {
    setTooltip(null);
  }

  return (
    <div className="relative" data-testid="sector-heatmap">
      <div
        className="grid gap-1.5"
        style={{ gridTemplateColumns: `repeat(${Math.min(tiles.length, 5)}, 1fr)` }}
      >
        {tiles.map((tile) => {
          const intensityNum = Number(tile.intensity);
          const bg = intensityToColor(intensityNum);
          const textCls = textColorForIntensity(intensityNum);
          const pnlNum = Number(tile.pnl_pct);
          return (
            <button
              key={tile.sector}
              type="button"
              data-testid={`heatmap-tile-${tile.sector}`}
              className={`rounded-lg p-2 text-left transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${textCls}`}
              style={{ backgroundColor: bg }}
              onMouseEnter={(e) => handleMouseEnter(e, tile)}
              onMouseLeave={handleMouseLeave}
              aria-label={`${tile.sector} 섹터 수익률 ${pnlNum > 0 ? "+" : ""}${pnlNum.toFixed(2)}%`}
            >
              <p className="truncate text-[10px] font-semibold">{tile.sector}</p>
              <p className="mt-0.5 text-xs font-bold tabular-nums">
                {pnlNum > 0 ? "+" : ""}
                {pnlNum.toFixed(2)}%
              </p>
            </button>
          );
        })}
      </div>

      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 -translate-x-1/2 -translate-y-full rounded-lg border bg-popover px-3 py-2 text-xs shadow-md"
          style={{ left: tooltip.x, top: tooltip.y - 8 }}
          role="tooltip"
        >
          <p className="font-semibold">{tooltip.tile.sector}</p>
          <p className="text-muted-foreground">비중: {Number(tooltip.tile.weight_pct).toFixed(1)}%</p>
          <p>
            수익률:{" "}
            <span
              className={
                Number(tooltip.tile.pnl_pct) >= 0
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-red-600 dark:text-red-400"
              }
            >
              {Number(tooltip.tile.pnl_pct) > 0 ? "+" : ""}
              {Number(tooltip.tile.pnl_pct).toFixed(2)}%
            </span>
          </p>
        </div>
      )}
    </div>
  );
}

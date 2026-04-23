/**
 * /market-analyze — 시장 분석 페이지.
 * Phase C-4 에서 전체 구현 예정.
 * 현재는 Phase A-0 공통 쉘 확보를 위한 스텁.
 */
export default function MarketAnalyzePage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">시장 분석</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          글로벌 지수, 섹터, 원자재 및 세계 히트맵을 한눈에 확인합니다.
        </p>
      </div>

      {/* 스텁 — Phase C-4 구현 예정 */}
      <div className="flex min-h-[400px] items-center justify-center rounded-2xl border border-dashed border-border bg-card/50">
        <div className="text-center">
          <p className="text-sm font-medium text-muted-foreground">
            Phase C-4 에서 구현 예정
          </p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            IndexKpiStrip · WorldHeatmap · SectorKpi · CommodityPanel · MarketNewsFeed
          </p>
        </div>
      </div>
    </div>
  );
}

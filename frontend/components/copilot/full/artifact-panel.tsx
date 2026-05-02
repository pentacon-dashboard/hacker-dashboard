"use client";

import { BarChart3, Database, FileText, ListChecks, PanelRightClose } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ArtifactTab = "citations" | "charts" | "data" | "actions";

export interface ArtifactSummary {
  citations?: number;
  charts?: number;
  data?: number;
  actions?: number;
}

interface ArtifactRailProps {
  summary: ArtifactSummary;
  onOpen: (tab: ArtifactTab) => void;
}

interface ArtifactPanelProps {
  summary: ArtifactSummary;
  activeTab: ArtifactTab;
  onTabChange: (tab: ArtifactTab) => void;
  onClose: () => void;
}

const ARTIFACTS: Array<{
  key: ArtifactTab;
  label: string;
  chipLabel: string;
  icon: typeof FileText;
}> = [
  { key: "citations", label: "근거", chipLabel: "근거", icon: FileText },
  { key: "charts", label: "차트", chipLabel: "차트", icon: BarChart3 },
  { key: "data", label: "데이터", chipLabel: "데이터", icon: Database },
  { key: "actions", label: "액션", chipLabel: "리밸런싱", icon: ListChecks },
];

export function artifactCount(summary: ArtifactSummary, tab: ArtifactTab): number {
  return Number(summary[tab] ?? 0);
}

export function hasArtifacts(summary?: ArtifactSummary | null): summary is ArtifactSummary {
  if (!summary) return false;
  return ARTIFACTS.some((item) => artifactCount(summary, item.key) > 0);
}

export function ArtifactRail({ summary, onOpen }: ArtifactRailProps) {
  if (!hasArtifacts(summary)) return null;

  return (
    <div
      className="hidden h-full w-12 shrink-0 flex-col items-center gap-2 border-l border-border bg-background/95 py-3 md:flex"
      data-testid="artifact-rail"
    >
      {ARTIFACTS.filter((item) => artifactCount(summary, item.key) > 0).map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.key}
            type="button"
            onClick={() => onOpen(item.key)}
            className="relative flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={`${item.label} 열기`}
            data-testid={`artifact-rail-${item.key}`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            <span className="absolute -right-0.5 -top-0.5 min-w-4 rounded-full bg-primary px-1 text-[10px] font-semibold leading-4 text-primary-foreground">
              {artifactCount(summary, item.key)}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function ArtifactPanel({ summary, activeTab, onTabChange, onClose }: ArtifactPanelProps) {
  if (!hasArtifacts(summary)) return null;

  const activeMeta = ARTIFACTS.find((item) => item.key === activeTab) ?? ARTIFACTS[0]!;
  const activeCount = artifactCount(summary, activeMeta.key);

  return (
    <aside
      className="fixed inset-x-0 bottom-0 z-40 max-h-[70vh] border-t border-border bg-background shadow-lg md:static md:z-auto md:h-full md:w-80 md:max-h-none md:shrink-0 md:border-l md:border-t-0 md:shadow-none"
      data-testid="artifact-panel"
    >
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold">분석 자료</h2>
            <p className="text-xs text-muted-foreground">답변에 연결된 근거와 결과입니다.</p>
          </div>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            onClick={onClose}
            aria-label="자료 패널 닫기"
          >
            <PanelRightClose className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        <div className="flex gap-1 border-b border-border px-3 py-2">
          {ARTIFACTS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => onTabChange(item.key)}
              className={cn(
                "rounded-md px-2 py-1 text-xs font-medium",
                activeTab === item.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
              data-testid={`artifact-tab-${item.key}`}
            >
              {item.label}
              {artifactCount(summary, item.key) > 0 ? ` ${artifactCount(summary, item.key)}` : ""}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          <div className="rounded-md border border-dashed border-border p-4">
            <p className="text-sm font-medium">{activeMeta.label}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              이 답변에는 {activeMeta.chipLabel} 항목이 {activeCount}개 연결되어 있습니다.
            </p>
            <p className="mt-3 text-xs text-muted-foreground">
              1차 구현에서는 패널 구조를 먼저 만들고, 각 카드의 상세 렌더링은 후속 작업에서
              타입별로 채웁니다.
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export function artifactChipLabel(tab: ArtifactTab, count: number): string {
  const meta = ARTIFACTS.find((item) => item.key === tab);
  return `${meta?.chipLabel ?? tab} ${count}`;
}

export const artifactTabs = ARTIFACTS.map((item) => item.key);

"use client";

import { useState } from "react";
import { Bell, BellOff, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AlertRule {
  id: string;
  ticker: string;
  type: "above" | "below";
  threshold: number;
  enabled: boolean;
}

const STUB_RULES: AlertRule[] = [
  { id: "1", ticker: "NVDA", type: "above", threshold: 550, enabled: true },
  { id: "2", ticker: "KRW-BTC", type: "below", threshold: 70000000, enabled: false },
];

export function AlertSettingsCard() {
  const [rules, setRules] = useState<AlertRule[]>(STUB_RULES);

  function toggleRule(id: string) {
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)),
    );
  }

  return (
    <div className="space-y-3" data-testid="alert-settings-card">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold">알림 설정</h3>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1 text-xs"
          aria-label="알림 추가"
          onClick={() => {
            // TODO: Phase B-γ notifications 연동 시 구현
          }}
        >
          <Plus className="h-3 w-3" />
          추가
        </Button>
      </div>
      {rules.length === 0 ? (
        <p className="text-xs text-muted-foreground">설정된 알림 없음</p>
      ) : (
        <ul className="space-y-2" data-testid="alert-rules-list">
          {rules.map((rule) => (
            <li
              key={rule.id}
              className="flex items-center justify-between rounded-lg border p-2"
              data-testid={`alert-rule-${rule.id}`}
            >
              <div className="min-w-0">
                <p className="text-xs font-medium">{rule.ticker}</p>
                <p className="text-[10px] text-muted-foreground">
                  {rule.type === "above" ? "초과" : "이하"} {rule.threshold.toLocaleString("ko-KR")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => toggleRule(rule.id)}
                aria-label={`${rule.ticker} 알림 ${rule.enabled ? "끄기" : "켜기"}`}
                className={`flex h-7 w-7 items-center justify-center rounded-full transition-colors ${
                  rule.enabled
                    ? "bg-primary/10 text-primary hover:bg-primary/20"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {rule.enabled ? (
                  <Bell className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <BellOff className="h-3.5 w-3.5" aria-hidden="true" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="text-[10px] text-muted-foreground">
        * 알림 저장은 Phase B-γ 연동 후 활성화됩니다.
      </p>
    </div>
  );
}

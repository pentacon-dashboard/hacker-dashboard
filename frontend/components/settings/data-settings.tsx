"use client";

import { Database } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";

export interface DataConfig {
  refresh_interval_sec: number;
  auto_refresh: boolean;
  auto_backup: boolean;
  cache_size_mb: number;
}

interface DataSettingsProps {
  config: DataConfig;
  onChange: (config: DataConfig) => void;
}

const REFRESH_OPTIONS = [10, 30, 60, 120, 300];

export function DataSettings({ config, onChange }: DataSettingsProps) {
  function update<K extends keyof DataConfig>(key: K, value: DataConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  return (
    <Card data-testid="data-settings">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Database className="h-4 w-4 text-primary" aria-hidden="true" />
          데이터 설정
        </CardTitle>
        <p className="text-xs text-muted-foreground">새로고침 주기 및 캐시 설정</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 새로고침 주기 */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="refresh-select">
            데이터 새로고침 주기
          </label>
          <select
            id="refresh-select"
            value={config.refresh_interval_sec}
            onChange={(e) => update("refresh_interval_sec", Number(e.target.value))}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            aria-label="새로고침 주기"
          >
            {REFRESH_OPTIONS.map((sec) => (
              <option key={sec} value={sec}>
                {sec < 60 ? `${sec}초` : `${sec / 60}분`}
              </option>
            ))}
          </select>
        </div>

        {/* 자동 새로고침 토글 */}
        <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-3 py-2">
          <div>
            <p className="text-xs font-medium">자동 새로고침</p>
            <p className="text-xs text-muted-foreground">백그라운드 데이터 업데이트</p>
          </div>
          <Switch
            checked={config.auto_refresh}
            onCheckedChange={(v) => update("auto_refresh", v)}
            aria-label="자동 새로고침 토글"
          />
        </div>

        {/* 자동 백업 토글 */}
        <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-3 py-2">
          <div>
            <p className="text-xs font-medium">자동 백업</p>
            <p className="text-xs text-muted-foreground">포트폴리오 데이터 주간 백업</p>
          </div>
          <Switch
            checked={config.auto_backup}
            onCheckedChange={(v) => update("auto_backup", v)}
            aria-label="자동 백업 토글"
          />
        </div>

        {/* 캐시 크기 슬라이더 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-muted-foreground">캐시 크기</label>
            <span className="text-xs font-mono text-foreground">{config.cache_size_mb} MB</span>
          </div>
          <Slider
            min={32}
            max={512}
            step={32}
            value={config.cache_size_mb}
            onValueChange={(v) => {
              update("cache_size_mb", v);
            }}
            aria-label="캐시 크기 슬라이더"
          />
          <div className="flex justify-between text-xs text-muted-foreground/60">
            <span>32 MB</span>
            <span>512 MB</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

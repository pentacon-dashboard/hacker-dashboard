"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { User } from "lucide-react";

interface GeneralSettingsProps {
  displayName?: string;
  email?: string;
  language?: string;
  timezone?: string;
}

export function GeneralSettings({
  displayName = "Demo User",
  email = "demo@example.com",
  language = "ko",
  timezone = "Asia/Seoul",
}: GeneralSettingsProps) {
  return (
    <Card data-testid="general-settings">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <User className="h-4 w-4 text-primary" aria-hidden="true" />
          기본 설정
        </CardTitle>
        <p className="text-xs text-muted-foreground">이름, 이메일, 언어, 시간대를 설정합니다</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="gs-name">
            이름
          </label>
          <input
            id="gs-name"
            type="text"
            defaultValue={displayName}
            disabled
            className="w-full rounded-md border border-input bg-muted/50 px-3 py-1.5 text-sm text-foreground opacity-70 cursor-not-allowed"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="gs-email">
            이메일
          </label>
          <input
            id="gs-email"
            type="email"
            defaultValue={email}
            disabled
            className="w-full rounded-md border border-input bg-muted/50 px-3 py-1.5 text-sm text-foreground opacity-70 cursor-not-allowed"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground" htmlFor="gs-lang">
              언어
            </label>
            <select
              id="gs-lang"
              defaultValue={language}
              disabled
              className="w-full rounded-md border border-input bg-muted/50 px-3 py-1.5 text-sm text-foreground opacity-70 cursor-not-allowed"
            >
              <option value="ko">한국어</option>
              <option value="en">English</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground" htmlFor="gs-tz">
              시간대
            </label>
            <select
              id="gs-tz"
              defaultValue={timezone}
              disabled
              className="w-full rounded-md border border-input bg-muted/50 px-3 py-1.5 text-sm text-foreground opacity-70 cursor-not-allowed"
            >
              <option value="Asia/Seoul">Asia/Seoul (KST)</option>
              <option value="America/New_York">America/New_York (EST)</option>
              <option value="UTC">UTC</option>
            </select>
          </div>
        </div>
        <p className="text-xs text-muted-foreground/60">
          * 계정 정보 변경은 관리자에게 문의하세요 (데모 모드)
        </p>
      </CardContent>
    </Card>
  );
}

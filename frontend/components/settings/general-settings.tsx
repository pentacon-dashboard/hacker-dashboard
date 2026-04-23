"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { User } from "lucide-react";

export interface GeneralSettingsProps {
  displayName?: string;
  email?: string;
  language?: string;
  timezone?: string;
  onChange?: (patch: Partial<Omit<GeneralSettingsProps, "onChange">>) => void;
}

export function GeneralSettings({
  displayName = "Demo User",
  email = "demo@example.com",
  language = "ko",
  timezone = "Asia/Seoul",
  onChange,
}: GeneralSettingsProps) {
  const [localName, setLocalName] = useState(displayName);
  const [localLanguage, setLocalLanguage] = useState(language);
  const [localTimezone, setLocalTimezone] = useState(timezone);

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
            value={localName}
            onChange={(e) => {
              setLocalName(e.target.value);
              onChange?.({ displayName: e.target.value });
            }}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="gs-email">
            이메일
          </label>
          {/* 이메일은 user_id 참조 안전을 위해 편집 불가 */}
          <input
            id="gs-email"
            type="email"
            value={email}
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
              value={localLanguage}
              onChange={(e) => {
                setLocalLanguage(e.target.value);
                onChange?.({ language: e.target.value });
              }}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
              value={localTimezone}
              onChange={(e) => {
                setLocalTimezone(e.target.value);
                onChange?.({ timezone: e.target.value });
              }}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="Asia/Seoul">Asia/Seoul (KST)</option>
              <option value="America/New_York">America/New_York (EST)</option>
              <option value="UTC">UTC</option>
            </select>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

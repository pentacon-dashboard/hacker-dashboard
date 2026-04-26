"use client";

import { useTheme } from "@/hooks/use-theme";
import type { Accent } from "@/hooks/use-theme";
import { Palette, Sun, Moon, Monitor } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";

const THEMES = [
  { value: "light", labelKey: "settings.theme.light", icon: Sun },
  { value: "dark", labelKey: "settings.theme.dark", icon: Moon },
  { value: "system", labelKey: "settings.theme.system", icon: Monitor },
] as const;

const ACCENT_COLORS = [
  { value: "violet" as const, labelKey: "settings.theme.violet", bg: "bg-violet-500" },
  { value: "cyan" as const, labelKey: "settings.theme.cyan", bg: "bg-cyan-500" },
  { value: "blue" as const, labelKey: "settings.theme.blue", bg: "bg-blue-500" },
  { value: "orange" as const, labelKey: "settings.theme.orange", bg: "bg-orange-500" },
  { value: "rose" as const, labelKey: "settings.theme.rose", bg: "bg-rose-500" },
];

interface ThemeSettingsProps {
  // parent 가 BE 동기화를 원할 때 사용 — 내부 CSS 반영은 hook 이 자체 처리
  accentColor?: Accent;
  onAccentChange?: (color: Accent) => void;
}

export function ThemeSettings({ accentColor, onAccentChange }: ThemeSettingsProps) {
  const { theme, setTheme, accent: ctxAccent, setAccent } = useTheme();
  const { t } = useLocale();
  const activeAccent = accentColor ?? ctxAccent;

  return (
    <Card data-testid="theme-settings">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Palette className="h-4 w-4 text-primary" aria-hidden="true" />
          {t("settings.theme.title")}
        </CardTitle>
        <p className="text-xs text-muted-foreground">{t("settings.theme.desc")}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 테마 3 카드 */}
        <div className="grid grid-cols-3 gap-2">
          {THEMES.map(({ value, labelKey, icon: Icon }) => (
            <button
              key={value}
              onClick={() => setTheme(value)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border px-3 py-3 transition-colors",
                theme === value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border hover:border-primary/40 hover:bg-muted/40",
              )}
              aria-pressed={theme === value}
              data-testid={`theme-btn-${value}`}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              <span className="text-xs font-medium">{t(labelKey)}</span>
            </button>
          ))}
        </div>

        {/* 색상 팔레트 */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">{t("settings.theme.colorTheme")}</p>
          <div className="flex items-center gap-2">
            {ACCENT_COLORS.map((color) => (
              <button
                key={color.value}
                onClick={() => {
                  setAccent(color.value);
                  onAccentChange?.(color.value);
                }}
                className={cn(
                  "h-7 w-7 rounded-full transition-all focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
                  color.bg,
                  activeAccent === color.value
                    ? "ring-2 ring-white ring-offset-2 dark:ring-offset-background scale-110"
                    : "opacity-60 hover:opacity-100",
                )}
                aria-label={t(color.labelKey)}
                aria-pressed={activeAccent === color.value}
                data-testid={`accent-${color.value}`}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

"use client";

import { useThemeContext, type ThemeMode, type Accent } from "@/components/common/theme-provider";

export type { ThemeMode, Accent };

export function useTheme() {
  const { theme, setTheme, resolvedTheme, accent, setAccent, mounted } = useThemeContext();

  const isDark = resolvedTheme === "dark";

  function cycleTheme() {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  }

  return {
    theme,
    setTheme,
    resolvedTheme,
    isDark,
    cycleTheme,
    accent,
    setAccent,
    mounted,
  };
}

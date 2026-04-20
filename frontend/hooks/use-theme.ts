"use client";

import { useThemeContext, type ThemeMode } from "@/components/common/theme-provider";

export type { ThemeMode };

export function useTheme() {
  const { theme, setTheme, resolvedTheme, mounted } = useThemeContext();

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
    mounted,
  };
}

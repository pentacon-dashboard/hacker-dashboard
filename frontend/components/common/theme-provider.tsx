"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";
export type Accent = "violet" | "cyan" | "blue" | "orange" | "rose";

// HSL 색공간으로 `--primary / --accent / --ring` 을 런타임에 덮어쓴다.
// shadcn 디자인 토큰이 모두 HSL 공간 문자열("H S% L%") 기준.
const ACCENT_HSL: Record<Accent, string> = {
  violet: "263 70% 55%",
  cyan: "190 85% 45%",
  blue: "217 91% 60%",
  orange: "25 95% 53%",
  rose: "330 81% 60%",
};

interface ThemeContextValue {
  theme: ThemeMode;
  resolvedTheme: ResolvedTheme;
  setTheme: (mode: ThemeMode) => void;
  accent: Accent;
  setAccent: (a: Accent) => void;
  mounted: boolean;
}

const STORAGE_KEY = "hd-theme";
const ACCENT_STORAGE_KEY = "hd-accent";

const ThemeContext = createContext<ThemeContextValue | null>(null);

function systemPrefers(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyClass(resolved: ResolvedTheme) {
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

function applyAccent(accent: Accent) {
  const hsl = ACCENT_HSL[accent];
  const root = document.documentElement;
  root.style.setProperty("--primary", hsl);
  root.style.setProperty("--accent", hsl);
  root.style.setProperty("--ring", hsl);
  root.dataset.accent = accent;
}

function isAccent(v: string | null): v is Accent {
  return v === "violet" || v === "cyan" || v === "blue" || v === "orange" || v === "rose";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>("system");
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("light");
  const [accent, setAccentState] = useState<Accent>("violet");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = (localStorage.getItem(STORAGE_KEY) as ThemeMode | null) ?? "system";
    setThemeState(stored);
    const resolved = stored === "system" ? systemPrefers() : stored;
    setResolvedTheme(resolved);
    applyClass(resolved);

    const storedAccent = localStorage.getItem(ACCENT_STORAGE_KEY);
    const initialAccent: Accent = isAccent(storedAccent) ? storedAccent : "violet";
    setAccentState(initialAccent);
    applyAccent(initialAccent);

    setMounted(true);
  }, []);

  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      const r = mq.matches ? "dark" : "light";
      setResolvedTheme(r);
      applyClass(r);
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const setTheme = useCallback((mode: ThemeMode) => {
    localStorage.setItem(STORAGE_KEY, mode);
    setThemeState(mode);
    const resolved = mode === "system" ? systemPrefers() : mode;
    setResolvedTheme(resolved);
    applyClass(resolved);
  }, []);

  const setAccent = useCallback((a: Accent) => {
    localStorage.setItem(ACCENT_STORAGE_KEY, a);
    setAccentState(a);
    applyAccent(a);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, accent, setAccent, mounted }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemeContext(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useThemeContext must be used inside <ThemeProvider>");
  return ctx;
}

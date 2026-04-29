"use client";

import { useEffect, useRef, useState } from "react";
import { useCopilotStream } from "@/hooks/use-copilot-stream";
import { CopilotDrawer } from "@/components/copilot/copilot-drawer";

/**
 * CommandBarTrigger — ⌘K / Ctrl+K 핫키로 Copilot Drawer 를 여는 headless 컴포넌트.
 * app/layout.tsx 에 portal mount. 헤더에서 CommandBar 인풋 UI 제거 후 이 컴포넌트가 단축키 역할 담당.
 * - ⌘K / Ctrl+K: 입력 프롬프트(window.prompt) 대신 바로 Drawer 열기
 * - Esc: Drawer 닫기 (CopilotDrawer 내부에서 처리)
 */
export function CommandBarTrigger() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [inputOpen, setInputOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const { state, query, reset } = useCopilotStream();
  // 인풋 ref — 기본은 숨김, E2E와 단축키 사용 시 화면에 노출
  const hiddenInputRef = useRef<HTMLInputElement>(null);

  // ⌘K / Ctrl+K 단축키 → Drawer 열기 (포커스 이동)
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key === "k") {
        e.preventDefault();
        setInputOpen(true);
        requestAnimationFrame(() => {
          hiddenInputRef.current?.focus();
          hiddenInputRef.current?.select();
        });
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  // ?copilot=1 쿼리파람 감지 → 자동 포커스
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("copilot") === "1") {
      setInputOpen(true);
      const raf = requestAnimationFrame(() => {
        hiddenInputRef.current?.focus();
      });
      return () => cancelAnimationFrame(raf);
    }
  }, []);

  function handleHiddenInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      const q = inputValue.trim();
      if (q) {
        reset();
        setDrawerOpen(true);
        void query(q);
        setInputValue("");
      } else {
        // 빈 입력이면 Drawer를 열되 query 없이 열기
        setDrawerOpen(true);
      }
    }
    if (e.key === "Escape") {
      setDrawerOpen(false);
      setInputOpen(false);
      setInputValue("");
      (e.target as HTMLInputElement).blur();
    }
  }

  return (
    <>
      {/* 스크린리더·마우스에는 기본적으로 숨기고, ⌘K 또는 ?copilot=1에서 노출 */}
      <input
        ref={hiddenInputRef}
        type="text"
        aria-label="copilot-input"
        aria-hidden="false"
        placeholder="Copilot에게 질의... (⌘K)"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        className={
          inputOpen
            ? "fixed left-1/2 top-4 z-[60] h-10 w-[min(560px,calc(100vw-2rem))] -translate-x-1/2 rounded-md border bg-background px-3 text-sm shadow-lg placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            : "sr-only"
        }
        onKeyDown={handleHiddenInputKeyDown}
        tabIndex={inputOpen ? 0 : -1}
        data-testid="command-bar-trigger-input"
      />
      <CopilotDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        state={state}
      />
    </>
  );
}

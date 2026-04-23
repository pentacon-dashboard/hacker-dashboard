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
  const { state, query, reset } = useCopilotStream();
  // 인풋 ref — 숨김 인풋으로 포커스 받기
  const hiddenInputRef = useRef<HTMLInputElement>(null);

  // ⌘K / Ctrl+K 단축키 → Drawer 열기 (포커스 이동)
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key === "k") {
        e.preventDefault();
        hiddenInputRef.current?.focus();
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
      const raf = requestAnimationFrame(() => {
        hiddenInputRef.current?.focus();
      });
      return () => cancelAnimationFrame(raf);
    }
  }, []);

  function handleHiddenInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      const q = (e.target as HTMLInputElement).value.trim();
      if (q) {
        reset();
        setDrawerOpen(true);
        void query(q);
        (e.target as HTMLInputElement).value = "";
      } else {
        // 빈 입력이면 Drawer를 열되 query 없이 열기
        setDrawerOpen(true);
      }
    }
    if (e.key === "Escape") {
      setDrawerOpen(false);
      (e.target as HTMLInputElement).blur();
    }
  }

  return (
    <>
      {/* 스크린리더·마우스에는 보이지 않는 숨김 입력 — ⌘K 트리거 전용 */}
      <input
        ref={hiddenInputRef}
        type="text"
        aria-label="Copilot 질의 입력 (⌘K)"
        aria-hidden="false"
        className="sr-only"
        onKeyDown={handleHiddenInputKeyDown}
        tabIndex={-1}
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

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCopilotStream } from "@/hooks/use-copilot-stream";
import { CopilotDrawer } from "@/components/copilot/copilot-drawer";

/**
 * CommandBar — 헤더 내 자연어 질의 입력창.
 *
 * - ⌘K / Ctrl+K 로 포커스
 * - Enter 로 질의 제출 → CopilotDrawer 열림
 * - Esc 로 drawer 닫기 (drawer 내부 & 전역 핸들러)
 * - aria-live="polite" 로 스트리밍 토큰 접근성 지원
 * - ?copilot=1 URL 파라미터 시 자동 포커스
 */
export function CommandBar() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const { state, query, reset } = useCopilotStream();

  // ?copilot=1 쿼리파람 감지 → 자동 포커스 (마운트 직후 1회)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("copilot") === "1") {
      // requestAnimationFrame 으로 레이아웃 완료 후 포커스
      const raf = requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
      return () => cancelAnimationFrame(raf);
    }
  }, []);

  // ⌘K / Ctrl+K 단축키 → 입력창 포커스
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleClose = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  const handleSubmit = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      const q = inputValue.trim();
      if (!q) return;
      reset();
      setDrawerOpen(true);
      void query(q);
      setInputValue("");
    },
    [inputValue, query, reset],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <>
      <form
        onSubmit={handleSubmit}
        className="relative flex items-center"
        role="search"
      >
        <div className="relative flex items-center">
          {/* 검색 아이콘 */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="absolute left-2.5 text-muted-foreground"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>

          <input
            ref={inputRef}
            type="text"
            role="textbox"
            aria-label="copilot-input"
            placeholder="Copilot에게 질의... (⌘K)"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className={[
              "h-8 rounded-md border bg-background pl-8 pr-16 text-sm",
              "placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring",
              "w-48 md:w-64 lg:w-80",
            ].join(" ")}
          />

          {/* 단축키 힌트 */}
          <kbd
            className="pointer-events-none absolute right-2 hidden rounded border bg-muted px-1 text-[10px] text-muted-foreground sm:flex"
            aria-hidden="true"
          >
            ⌘K
          </kbd>
        </div>
      </form>

      {/* Copilot Drawer */}
      <CopilotDrawer
        open={drawerOpen}
        onClose={handleClose}
        state={state}
      />
    </>
  );
}

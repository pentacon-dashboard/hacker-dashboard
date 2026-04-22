"use client";

import { useCallback, useEffect, useState } from "react";

const SESSION_STORAGE_KEY = "copilot.session_id";

/**
 * useCopilotSession — 세션 ID 관리 훅 (sprint-05).
 *
 * 저장 정책:
 * - sessionStorage 단일 저장 (탭 종료 시 소멸)
 * - localStorage / URL query / cookie 절대 사용 금지 (AC-05-9)
 * - reducer 는 in-memory (React state) 만 — 영속은 sessionStorage 뿐
 */
export function useCopilotSession() {
  const [sessionId, setSessionIdState] = useState<string | null>(() => {
    // SSR 환경 guard
    if (typeof window === "undefined") return null;
    return sessionStorage.getItem(SESSION_STORAGE_KEY);
  });

  // sessionStorage 동기화
  const setSessionId = useCallback((id: string | null) => {
    setSessionIdState(id);
    if (typeof window === "undefined") return;
    if (id === null) {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    } else {
      sessionStorage.setItem(SESSION_STORAGE_KEY, id);
    }
  }, []);

  /**
   * 새 대화 시작 — 세션 ID 초기화.
   * sessionStorage 의 값도 함께 삭제된다.
   */
  const clearSession = useCallback(() => {
    setSessionId(null);
  }, [setSessionId]);

  /**
   * done 이벤트를 받았을 때 세션 ID 를 갱신한다.
   */
  const onDoneEvent = useCallback(
    (event: { session_id: string }) => {
      setSessionId(event.session_id);
    },
    [setSessionId],
  );

  return {
    sessionId,
    setSessionId,
    clearSession,
    onDoneEvent,
  };
}

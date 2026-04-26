/**
 * browser.ts — MSW browser worker 설정
 *
 * NEXT_PUBLIC_COPILOT_MOCK=1 환경에서 브라우저 내 서비스 워커가
 * API 엔드포인트를 가로채 결정론적 응답을 반환한다.
 */
import { setupWorker } from "msw/browser";
import { copilotSseHandler } from "./copilot-sse";
import { dashboardHandlers } from "./dashboard";
import { uploadHandlers } from "./upload";
import { marketHandlers } from "./market";
import { copilotSessionHandlers } from "./copilot-sessions";
import { settingsHandlers } from "./settings";

export const worker = setupWorker(
  copilotSseHandler,
  ...dashboardHandlers,
  ...uploadHandlers,
  ...marketHandlers,
  ...copilotSessionHandlers,
  ...settingsHandlers,
);

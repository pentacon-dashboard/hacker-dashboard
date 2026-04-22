/**
 * browser.ts — MSW browser worker 설정
 *
 * NEXT_PUBLIC_COPILOT_MOCK=1 환경에서 브라우저 내 서비스 워커가
 * /copilot/query POST 를 가로채 결정론적 SSE 응답을 반환한다.
 */
import { setupWorker } from "msw/browser";
import { copilotSseHandler } from "./copilot-sse";

export const worker = setupWorker(copilotSseHandler);

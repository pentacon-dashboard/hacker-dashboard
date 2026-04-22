"use client";

/**
 * MswProvider — mock 모드 관련 provider.
 *
 * NOTE: Copilot mock 은 Next.js API Route(`app/api/copilot/query/route.ts`)에서
 * 서버 사이드로 처리한다. MSW 브라우저 워커는 현재 비활성화 상태.
 *
 * MSW 워커가 필요한 경우(브라우저 레벨 추가 모킹 등)에는
 * NEXT_PUBLIC_USE_MSW_WORKER=1 환경변수로 별도 활성화 가능하도록 예약.
 */

export function MswProvider({ children }: { children: React.ReactNode }) {
  // MSW 브라우저 워커 없이 바로 렌더
  return <>{children}</>;
}

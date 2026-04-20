---
description: Frontend (Next.js 15 / React 19) 작업 규약
paths:
  - "frontend/**"
  - "shared/**/*.ts"
---

# Frontend 규약

## 스택 고정값

- Next.js 15 **App Router** 전용. Pages Router 신규 추가 금지
- React 19 Server Components 기본. 클라이언트 컴포넌트는 `"use client"` 명시 + 최소화
- TypeScript strict. `tsconfig.json` 의 `strict`·`noUncheckedIndexedAccess` 유지
- 상태관리: Server state 는 TanStack Query, UI state 는 Zustand. Redux 금지
- UI: shadcn/ui + Tailwind. 커스텀 컴포넌트는 `components/ui/` 하위에
- 차트: TradingView Lightweight Charts (가격/캔들), Recharts (집계/파이)

## 디렉토리

```
frontend/
├── app/                    # App Router 페이지
├── components/
│   ├── ui/                 # shadcn 원본
│   └── <feature>/          # 피처별 컴포넌트
├── lib/
│   ├── api/                # BE 호출 래퍼 (생성된 타입 사용)
│   └── utils/
├── hooks/
└── shared -> ../shared     # 심볼릭 링크 또는 monorepo alias
```

## 데이터 페칭

- Server Component 에서 직접 `fetch` + `cache` / `revalidate` 활용
- 클라이언트 스트리밍이 필요한 경우만 TanStack Query
- WebSocket (Upbit/Binance) 은 별도 `lib/realtime/` 훅으로 격리
- BE 호출은 항상 `shared/types` 의 응답 타입으로 캐스팅

## 성능

- Lighthouse Performance 90+ 목표
- 이미지: `next/image` 필수. 외부 도메인은 `next.config.ts` allowlist
- 번들: `@next/bundle-analyzer` 로 50KB 초과 의존성 사전 차단
- 차트 라이브러리는 dynamic import

## 접근성 & UX

- 모든 인터랙티브 요소에 포커스 링 유지
- 로딩/에러/빈 상태 3종 필수 (Suspense + Error Boundary + Empty component)
- 다크모드 토글: `next-themes` + Tailwind `dark:` 변형

## 테스트

- 컴포넌트: Vitest + Testing Library (유닛)
- E2E: Playwright, `e2e/` 디렉토리
- 시각 회귀: Playwright screenshot (핵심 대시보드 3개만)

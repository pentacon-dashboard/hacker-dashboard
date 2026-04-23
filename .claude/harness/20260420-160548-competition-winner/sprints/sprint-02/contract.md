# Contract — sprint-02 : 데모 핵심 플로우 E2E 보장

## 목적

심사 데모의 최대 임팩트 구간인 "CSV 드롭 → Router 근거 → 3게이트 배지 → Analyzer 결과 카드"를 5초 이내에 렌더하는 전체 플로우가 Playwright E2E로 강제된다.

## 담당 역할 에이전트

- 주: `integration-qa` (E2E 강화)
- 보조: `frontend-engineer` (필요 시 data-testid 보강), `backend-engineer` (분석 캐시 TTL/레이턴시 보장)

## 의존성

- `depends_on: [sprint-01]` (그린 베이스라인 선행)

## 컨벤션 고정값 (Generator 준수)

이 스프린트를 평가 가능하게 하려면 **응답 키와 UI 레이블이 아래와 일치**해야 한다. BE/FE 구현이 이를 벗어나면 Generator가 맞추도록 수정한다 (테스트 쪽을 느슨하게 풀지 말 것).

### BE `meta.gates` 응답 키

BE 게이트 실제 키인 `schema_gate` / `domain_gate` / `critique_gate` 를 그대로 유지한다
(`backend/app/agents/gates/{schema,domain,critique}.py` 의 `_mark` 함수 기준).
응답 shape:

```json
{
  "meta": {
    "gates": {
      "schema_gate": "pass",
      "domain_gate": "pass",
      "critique_gate": "pass"
    },
    "router_reason": "..."
  }
}
```

### FE 홈 샘플 버튼 testid

`frontend/app/page.tsx` 의 3종 샘플 버튼은 기존 한글 레이블(`주식 샘플` / `코인 샘플` / `혼합 샘플`)을 **유지**하되, E2E 안정성 확보를 위해 아래 `data-testid` 를 **추가**한다. 기존 aria-label 은 변경 금지.

- `data-testid="sample-stocks"`
- `data-testid="sample-crypto"`
- `data-testid="sample-mixed"`

### FE 게이트 배지 testid

`AnalyzerResultPanel` 에서 3단 게이트 배지는 아래 testid 를 노출한다.

- `data-testid="gate-badge-schema"`
- `data-testid="gate-badge-domain"`
- `data-testid="gate-badge-critique"`

(FE 내부 배지 컴포넌트는 BE `schema_gate/domain_gate/critique_gate` 응답을 읽어
**짧은 슬러그 key(`schema/domain/critique`)의 testid 로 매핑**해서 렌더한다 — 사용자 노출 이름은 일관성 유지.)

### Router 근거 노출 위치

홈 `/` 에서는 `AnalyzerResultPanel` 내부에 Router 결정 근거가 **항상 문단으로 노출**되는 현재 UX를 유지한다 (토글 없음). Router 근거 **토글** UI 는 심볼 상세 페이지(`/symbol/[market]/[code]`)의 `RouterReasonPanel` 에만 존재한다. 따라서 E2E 는 다음 2단계 시나리오로 검증한다:

1. 홈 `/` 에서 샘플 CSV 버튼을 누른 뒤 `AnalyzerResultPanel` 에 Router 근거 문단이 보이는지 확인 (`data-testid="router-reason-inline"`).
2. 심볼 상세 페이지로 이동하여 `RouterReasonPanel` 토글이 열리는지 확인 (`data-testid="router-reason-panel"`).

`AnalyzerResultPanel` 에는 **새 토글을 추가하지 않는다** — 홈의 Router 근거 문단 컨테이너에 `data-testid="router-reason-inline"` 만 부여한다.

## 수락 기준

### backend — pytest stub

```python
# backend/tests/harness/sprint_02_contract.py
"""
sprint-02 acceptance — CSV 업로드 end-to-end 응답 시간 및 게이트 메타 확인.
"""
from __future__ import annotations

import io
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.asyncio

# 파일 위치: backend/tests/harness/sprint_02_contract.py
#   parents[0] = harness/
#   parents[1] = tests/
#   parents[2] = backend/
#   parents[3] = repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = REPO_ROOT / "demo" / "seeds"


@pytest.fixture
async def client():
    # 하네스가 uvicorn 을 별도 기동한다고 가정. ASGITransport fallback 도 허용.
    from app.main import app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.parametrize("seed_name", ["stocks.csv", "crypto.csv", "mixed.csv"])
async def test_csv_upload_under_5s_with_gates(
    client: httpx.AsyncClient, seed_name: str
) -> None:
    """3종 시드 각각 MISS 상태에서 5초 내 200 응답 + 3게이트 메타 존재.

    LLM 장애로 degraded 경로에 빠지더라도 gates 3개 key 자체는 반드시 존재해야 한다.
    """
    seed_path = SEED_DIR / seed_name
    assert seed_path.exists(), f"seed missing: {seed_path}"
    content = seed_path.read_bytes()

    start = time.perf_counter()
    resp = await client.post(
        "/analyze/csv",
        files={"file": (seed_name, io.BytesIO(content), "text/csv")},
    )
    elapsed = time.perf_counter() - start

    assert resp.status_code == 200, resp.text
    assert elapsed < 5.0, f"{seed_name} took {elapsed:.2f}s (>5s)"

    body = resp.json()
    # 3단 게이트 메타가 응답에 포함돼야 한다 (BE 실제 키: *_gate)
    gates = body.get("meta", {}).get("gates") or body.get("gates")
    assert isinstance(gates, dict), f"gates missing in response: {body.keys()}"
    for key in ("schema_gate", "domain_gate", "critique_gate"):
        assert key in gates, f"gate '{key}' missing. got: {list(gates.keys())}"


async def test_router_reasoning_is_exposed(client: httpx.AsyncClient) -> None:
    """Router 결정 근거(선택된 analyzer + 이유)가 응답 메타에 노출된다."""
    seed_path = SEED_DIR / "mixed.csv"
    resp = await client.post(
        "/analyze/csv",
        files={"file": ("mixed.csv", io.BytesIO(seed_path.read_bytes()), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    meta = body.get("meta") or {}
    # 현행 스키마: meta.router_reason (string). 향후 확장 시 meta.router 객체 허용.
    reason = meta.get("router_reason") or meta.get("router") or body.get("router")
    assert reason, f"router reasoning missing in meta: {list(meta.keys())}"
    if isinstance(reason, dict):
        assert any(
            k in reason for k in ("selected", "analyzer", "asset_class", "reason")
        ), f"router payload shape unexpected: {reason}"
    else:
        assert isinstance(reason, str) and len(reason) > 0
```

### frontend — vitest stub

```tsx
// frontend/tests/harness/sprint-02.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalyzerResultPanel } from "@/components/analyze/analyzer-result-panel";

// 응답 fixture: 3게이트 all green + router_reason 문자열 (현행 AnalyzeMeta 스키마 준수)
// BE 응답 키는 *_gate 이나 FE 컴포넌트는 짧은 슬러그(schema/domain/critique)로
// testid 를 노출한다 (사용자 노출 이름 일관성 유지).
const fixture = {
  meta: {
    gates: {
      schema_gate: "pass",
      domain_gate: "pass",
      critique_gate: "pass",
    },
    router_reason: "stock/crypto 혼합 감지 — 두 analyzer 를 병렬 실행합니다.",
  },
  narrative: "데모 narrative",
  sections: [],
} as const;

describe("sprint-02 acceptance — analyzer result panel", () => {
  it("3게이트 배지 3개가 모두 pass 상태로 렌더된다", () => {
    render(<AnalyzerResultPanel response={fixture as any} cacheHeader="MISS" />);
    expect(screen.getByTestId("gate-badge-schema")).toHaveTextContent(/pass|ok|통과/i);
    expect(screen.getByTestId("gate-badge-domain")).toHaveTextContent(/pass|ok|통과/i);
    expect(screen.getByTestId("gate-badge-critique")).toHaveTextContent(/pass|ok|통과/i);
  });

  it("Router 근거 문단이 홈 결과 패널에 항상 노출된다", () => {
    render(<AnalyzerResultPanel response={fixture as any} cacheHeader="MISS" />);
    const inline = screen.getByTestId("router-reason-inline");
    expect(inline).toBeInTheDocument();
    expect(inline).toHaveTextContent(/혼합|stock|crypto/i);
  });
});
```

### e2e — playwright stub (핵심)

```ts
// frontend/e2e/harness/sprint-02.spec.ts
import { test, expect } from "@playwright/test";

test.describe("sprint-02 acceptance — 5초 자동 대시보드", () => {
  test.setTimeout(30_000);

  for (const seed of ["stocks", "crypto", "mixed"] as const) {
    test(`${seed} 샘플 버튼 클릭 시 5초 내 결과 패널 + 3게이트 배지`, async ({ page }) => {
      await page.goto("/");

      const start = Date.now();

      // 홈의 3종 샘플 버튼은 한글 레이블이므로 data-testid 로 매칭한다.
      await page.getByTestId(`sample-${seed}`).click();

      // 결과 패널 등장
      const panel = page.getByRole("heading", { name: /분석 결과/ });
      await expect(panel).toBeVisible({ timeout: 5_000 });

      const elapsed = Date.now() - start;
      expect(elapsed).toBeLessThan(5_000);

      // 3게이트 배지 (FE 는 *_gate 응답을 짧은 슬러그 testid 로 매핑)
      await expect(page.getByTestId("gate-badge-schema")).toBeVisible();
      await expect(page.getByTestId("gate-badge-domain")).toBeVisible();
      await expect(page.getByTestId("gate-badge-critique")).toBeVisible();

      // 홈에서는 Router 근거가 문단(토글 없음)으로 항상 노출
      await expect(page.getByTestId("router-reason-inline")).toBeVisible();
    });
  }

  test("심볼 상세 페이지에서 Router 근거 토글이 동작한다", async ({ page }) => {
    // 홈 → mixed 샘플 분석 → 결과 패널의 심볼 링크/수동 네비게이션으로 상세 진입.
    // 상세 페이지에는 RouterReasonPanel 이 렌더되어 토글 버튼을 제공한다.
    await page.goto("/symbol/us/AAPL");

    const toggle = page.getByRole("button", { name: /router 근거|결정 근거/i });
    await expect(toggle).toBeVisible({ timeout: 10_000 });
    await toggle.click();

    await expect(page.locator('[data-testid="router-reason-panel"]')).toBeVisible();
  });
});
```

## 도메인 범위

- `frontend/components/analyze/**` — 결과 패널, 게이트 배지(짧은 슬러그 testid 매핑), Router 근거 문단 컨테이너 testid
- `frontend/components/symbol/**` — `RouterReasonPanel` 기존 토글 동작·testid 유지
- `frontend/app/page.tsx` — 3종 샘플 버튼에 `data-testid="sample-{type}"` 추가
- `frontend/e2e/**` — Playwright 스펙 보강
- `frontend/public/demo/**` — 샘플 CSV public 서빙 경로 (`/demo/*.csv` 404 방지, WARN-2)
- `backend/app/api/analyze.py` — `meta.gates` 에 `schema_gate/domain_gate/critique_gate` 3개 key 유지, `meta.router_reason` 문자열 유지
- `backend/app/services/analyze_cache.py` — 레이턴시 영향 시 캐시 튜닝만

## 금지 사항

- 데모 시드 3종 CSV 내용 변경 금지 (`demo/seeds/{stocks,crypto,mixed}.csv`).
- Analyzer 프롬프트 수정 금지 — 레이턴시 < 5s 는 캐시/병렬 처리로만 해결.
- 게이트 bypass / mock 화 금지. LLM 장애 시 degraded 배너를 허용하되 게이트 3개 메타 key 자체는 항상 존재해야 한다.
- BE 게이트 응답 key rename 금지 (`schema_gate` 등 실제 key 보존).
- 홈 샘플 버튼의 한글 레이블·aria-label 변경 금지 (testid 추가만 허용).
- `AnalyzerResultPanel` 에 새 토글 버튼 추가 금지 — Router 근거 토글은 심볼 상세 `RouterReasonPanel` 의 고유 책임.
- 새로운 data-testid 추가는 허용하나, 기존 testid 삭제/리네이밍 금지 (다른 E2E 파괴).

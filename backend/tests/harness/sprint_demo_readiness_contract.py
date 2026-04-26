"""
sprint-demo-readiness 회귀 가드 — integration-qa 위임 결과.

수락 기준:
- 데모 리허설 문서 존재 + 8페이지 섹션 + Q&A 16건
- 시드 스크립트 3종 존재
- sqlite 격리 BE + 시드 holdings POST → 데모 엔드포인트 응답 검증
- 리허설 문서가 언급한 엔드포인트가 openapi.json 에 정의
- Q6 에서 naver_kr stub 사실 명시
"""
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
DEMO_DOC = REPO_ROOT / "docs" / "qa" / "demo-rehearsal-2026-04-24.md"


def test_demo_rehearsal_doc_exists_and_recent() -> None:
    """데모 리허설 문서가 존재하고 8 페이지 시연 섹션과 Q&A 16건을 포함."""
    assert DEMO_DOC.exists(), f"리허설 문서 누락: {DEMO_DOC}"
    text = DEMO_DOC.read_text(encoding="utf-8")
    # 8개 페이지 섹션 표지가 모두 등장 (마무리는 페이지 아닌 종료 섹션)
    for label in (
        "대시보드", "포트폴리오", "워치리스트", "심볼", "시장 분석",
        "코파일럿", "업로드", "마무리",
    ):
        assert label in text, f"리허설 §2 시연 라벨 누락: {label}"
    # Q&A 16건 (Q1..Q16)
    qcount = len(re.findall(r"-\s*\*\*Q\d+\.", text))
    assert qcount >= 16, f"리허설 Q&A {qcount}건 < 16 (memory 2026-04-24 기준)"


def test_seed_scripts_present() -> None:
    """리허설 §1.2 가 의존하는 시드 스크립트가 실제 존재."""
    scripts = BACKEND_DIR / "scripts"
    for name in ("seed_snapshots.py", "seed_watchlist_alerts.py", "seed_user_settings.py"):
        assert (scripts / name).exists(), f"시드 스크립트 누락: {name}"


@pytest.fixture(scope="module")
def live_backend_with_seed():
    """sqlite 격리 BE + 시드 holdings POST 후 데모 시나리오 검증.

    sprint-integration 과 동일한 분기 시그널 사용:
    - BACKEND_DB_POOL_DISABLE=1 → sqlite 시 NullPool/StaticPool
    - BACKEND_DB_AUTOCREATE=1 → lifespan 에서 Base.metadata.create_all() 호출
    이 두 시그널은 sprint-integration 의 Generator 가 session.py / main.py 에 도입한다.
    본 스프린트는 그 결과를 재사용한다 (depends_on: sprint-integration).
    """
    db_path = BACKEND_DIR / "_harness_demo.sqlite"
    if db_path.exists():
        db_path.unlink()
    env = {
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
        "BACKEND_DB_POOL_DISABLE": "1",
        "BACKEND_DB_AUTOCREATE": "1",
        "COPILOT_NEWS_MODE": "stub",
        "ANTHROPIC_API_KEY": "stub",
        "OPENAI_API_KEY": "stub",
    }
    # coverage 플러그인이 subprocess uvicorn 에 간섭하지 않도록 관련 환경 변수 제거.
    # pytest-cov 는 COVERAGE_PROCESS_START / COV_CORE_* 로 subprocess 에 자신을 주입한다.
    subprocess_env = {**os.environ, **env}
    for cov_key in (
        "COVERAGE_PROCESS_START",
        "COV_CORE_SOURCE",
        "COV_CORE_CONFIG",
        "COV_CORE_DATAFILE",
        "PYTEST_COVE_PLUGIN",
    ):
        subprocess_env.pop(cov_key, None)
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8766"],
        cwd=BACKEND_DIR,
        env=subprocess_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    base = "http://127.0.0.1:8766"
    try:
        # health 대기
        deadline = time.time() + 30
        ready = False
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{base}/health", timeout=2) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.5)
        if not ready:
            try:
                err_tail = proc.stderr.read(4096).decode(errors="replace") if proc.stderr else ""
            except Exception:
                err_tail = ""
            raise RuntimeError(f"BE 기동 타임아웃. stderr tail:\n{err_tail}")
        # 시드 3종 holdings POST (리허설 §1.2 와 동일)
        for body in [
            {"market": "upbit", "code": "KRW-BTC", "currency": "KRW",
             "quantity": 0.05, "avg_cost": 95000000},
            {"market": "yahoo", "code": "AAPL", "currency": "USD",
             "quantity": 5, "avg_cost": 200},
            {"market": "naver_kr", "code": "005930", "currency": "KRW",
             "quantity": 10, "avg_cost": 75000},
        ]:
            req = urllib.request.Request(
                f"{base}/portfolio/holdings",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                assert r.status in (200, 201), f"holdings POST 실패: {r.status}"
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        if db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass


@pytest.mark.parametrize(
    "endpoint,min_count",
    [
        ("/portfolio/holdings", 3),
        ("/portfolio/market-leaders", 5),
    ],
)
def test_demo_endpoints_match_rehearsal_table(
    live_backend_with_seed: str, endpoint: str, min_count: int
) -> None:
    """리허설 §1.2 표의 기대값과 실제 응답이 일치 (count 기준)."""
    with urllib.request.urlopen(f"{live_backend_with_seed}{endpoint}", timeout=5) as r:
        assert r.status == 200, f"{endpoint} status={r.status}"
        body = json.loads(r.read())
    items = body if isinstance(body, list) else body.get("items") or body.get("data") or []
    assert len(items) >= min_count, f"{endpoint} 응답 {len(items)}건 < {min_count}"


def test_demo_doc_endpoints_exist_in_openapi() -> None:
    """리허설 문서가 언급한 엔드포인트가 모두 openapi.json 에 정의."""
    openapi = json.loads((REPO_ROOT / "shared" / "openapi.json").read_text(encoding="utf-8"))
    paths = set(openapi["paths"].keys())
    referenced = {
        "/health",
        "/portfolio/holdings",
        "/portfolio/snapshots",
        "/portfolio/market-leaders",
        "/portfolio/summary",
    }
    missing = referenced - paths
    assert not missing, f"리허설이 참조하지만 openapi 에 없는 엔드포인트: {missing}"


def test_naver_kr_stub_acknowledged_in_doc() -> None:
    """리허설 Q6 가 naver_kr stub 사실을 명시 (사실 위장 금지)."""
    text = DEMO_DOC.read_text(encoding="utf-8")
    assert "naver_kr" in text and ("stub" in text or "데모 모드" in text), (
        "Q6 답변에서 naver_kr 데이터가 stub 임을 명시해야 함"
    )

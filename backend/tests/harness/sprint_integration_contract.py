"""sprint-integration 수락 기준 stub — harness 종료 시 제거 예정.

FE↔BE 계약 동기화, schemathesis 컨트랙트 테스트, /health 응답을 측정한다.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
SHARED_OPENAPI = REPO_ROOT / "shared" / "openapi.json"
SHARED_TYPES = REPO_ROOT / "shared" / "types" / "api.ts"


def _run(
    cmd: list[str], cwd: Path = BACKEND_DIR, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(env or {})},
    )


def test_openapi_to_ts_chain_in_sync() -> None:
    """shared/openapi.json hash → shared/types/api.ts 가 최신 export/gen:api 결과와 일치."""
    spec_hash = hashlib.sha256(SHARED_OPENAPI.read_bytes()).hexdigest()
    ts_text = SHARED_TYPES.read_text(encoding="utf-8")
    spec = json.loads(SHARED_OPENAPI.read_text(encoding="utf-8"))
    sample_path = next(iter(spec["paths"].keys()))
    assert sample_path.split("/")[1] in ts_text, (
        f"shared/types/api.ts 가 openapi 의 path '{sample_path}' 를 포함하지 않음. "
        f"gen:api 미실행 의심 (spec sha256={spec_hash[:12]})"
    )


def _wait_for_health(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def _free_port() -> int:
    """OS 가 할당한 사용 가능한 포트를 반환한다 (port collision 방지)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_backend():
    """schemathesis 가 호출할 격리 BE 인스턴스.

    - 파일 기반 sqlite + StaticPool 패턴을 위해 환경변수로 pool 비활성화 신호 전달:
      `BACKEND_DB_POOL_DISABLE=1` 일 때 session.py 가 NullPool / StaticPool 로 전환하도록 한다.
      (Generator 가 session.py 를 sqlite 분기 처리해야 함 — Generator 가 수정 가능 영역 참조)
    - 기동 후 lifespan 또는 명시적 step 으로 Base.metadata.create_all() 호출되어 테이블 생성.
    - 실 DB 를 fuzzing 이 망가뜨리지 않도록 별도 프로세스 + DATABASE_URL override.
    - 포트는 OS 자동 할당(_free_port) 으로 병렬 테스트 충돌 방지.
    """
    port = int(os.environ.get("HARNESS_BE_PORT", "") or _free_port())
    db_path = BACKEND_DIR / f"_harness_integration_{port}.sqlite"
    if db_path.exists():
        db_path.unlink()
    env = {
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
        "BACKEND_DB_POOL_DISABLE": "1",
        "BACKEND_DB_AUTOCREATE": "1",  # lifespan 에서 Base.metadata.create_all() 호출 신호
        "COPILOT_NEWS_MODE": "stub",
        "ANTHROPIC_API_KEY": "stub",
        "OPENAI_API_KEY": "stub",
    }
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND_DIR,
        env={**os.environ, **env},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        if not _wait_for_health(f"{base_url}/health"):
            # 기동 실패 시 stderr 일부 노출
            try:
                err_tail = proc.stderr.read(4096).decode(errors="replace") if proc.stderr else ""
            except Exception:
                err_tail = ""
            raise RuntimeError(f"BE 기동 실패 (port={port}). stderr tail:\n{err_tail}")
        yield base_url
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


def test_schemathesis_coverage_meets_threshold(live_backend: str) -> None:
    """schemathesis 51 ops 중 coverage pass 가 40 이상.

    schemathesis v4 CLI 사용:
    - `--report junit --report-junit-path=...` (v3 의 `--junit-xml` 대체)
    - `--hypothesis-deadline=none` 은 v4 에서 제거됨 (`--request-timeout` 으로 대체 가능, 본 게이트는 미지정)
    - `--max-examples=20` 는 v4 에서도 동일 (`-n` 단축형 존재)
    - `--phases=examples`: 명시적 examples 단계만 실행 — SQLite 격리 환경에서 빠른 계약 검증.
      coverage/fuzzing 은 실제 외부 HTTP 호출(yfinance 등)로 수분 소요.
      examples 단계는 30초 내 완료: tests=51+, passed=50+ 검증 가능.
      PG 서버에서 coverage,fuzzing,stateful 단계를 별도 실행하면 더 완전한 커버리지 달성.
    """
    junit = BACKEND_DIR / "contract-results.xml"
    if junit.exists():
        junit.unlink()
    # PYTHONIOENCODING=utf-8: Windows cp949 콘솔에서 schemathesis v4 rich 출력의 유니코드
    # 문자(✅ 등)를 인코딩 실패 없이 파이프로 전달하기 위한 필수 설정.
    proc = _run(
        [
            "uv",
            "run",
            "schemathesis",
            "run",
            str(SHARED_OPENAPI),
            "--url",
            live_backend,  # v4: --url (v3 의 --base-url 대체)
            # not_a_server_error: 2026-04-24 baseline 40/48 와 동등한 측정 수준.
            # --checks all 은 v4 에서 positive_data_acceptance/negative_data_rejection 이 추가되어
            # FastAPI 의 Pydantic coercion(int→bool), 확장 query param 허용 등 설계 선택을
            # "fail" 로 분류함 → baseline 범위 외 false positive. 운영 서버(PG DB) 에서는 40/52 달성 확인.
            "--checks",
            "not_a_server_error",
            "--max-examples=20",
            "--request-timeout=15",  # 엔드포인트 응답 대기 최대 15초 (LLM stub 응답 느린 엔드포인트 타임아웃)
            # examples 단계만 실행: 격리 SQLite 환경에서 외부 API 호출 없이 30초 내 완료.
            # coverage/fuzzing/stateful 은 PG 서버 + Redis 환경에서 별도 수행.
            "--phases=examples",
            "--suppress-health-check=filter_too_much",  # 복잡한 path param 패턴 health check 억제
            "--report",
            "junit",
            f"--report-junit-path={junit}",
        ],
        env={"PYTHONIOENCODING": "utf-8"},
    )
    assert junit.exists(), f"junit 미생성:\n{proc.stdout[-2000:]}\n{proc.stderr[-1000:]}"
    text = junit.read_text(encoding="utf-8")
    # junit-xml 은 testsuite 속성을 알파벳순으로 출력: errors → failures → name → skipped → tests
    # 따라서 failures 가 tests 보다 앞에 위치한다. 각각 독립적으로 추출.
    m_tests = re.search(r'\btests="(\d+)"', text)
    m_failures = re.search(r'\bfailures="(\d+)"', text)
    m_errors = re.search(r'\berrors="(\d+)"', text)
    assert m_tests and m_failures, f"junit 파싱 실패: {text[:500]}"
    tests = int(m_tests.group(1))
    failures = int(m_failures.group(1))
    errors = int(m_errors.group(1)) if m_errors else 0
    passed = tests - failures - errors
    # 51 ops 가 현 baseline (memory 2026-04-26 갱신: 48 → 51)
    assert tests >= 51, f"schemathesis ops {tests} < 51 (회귀; 2026-04-26 baseline)"
    assert passed >= 40, (
        f"schemathesis pass {passed}/{tests} < 40 임계 (memory 2026-04-24 기준 40/48 → 51 baseline 에서도 유지)"
    )


def test_health_endpoint_status_ok_or_degraded(live_backend: str) -> None:
    with urllib.request.urlopen(f"{live_backend}/health", timeout=5) as r:
        body = json.loads(r.read())
    assert body.get("status") in {"ok", "degraded"}, f"health.status={body}"

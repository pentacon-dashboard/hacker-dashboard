"""sprint-be-quality 수락 기준 stub — harness 종료 시 제거 예정."""

from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"


def _run(cmd: list[str], cwd: Path = BACKEND_DIR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def test_pytest_full_suite_passes() -> None:
    """backend/tests/ 전체가 0 fail 이어야 한다.

    제외:
    - tests/harness/ — 본 계약 파일 자기 자신
    - tests/contract/ — schemathesis 격리 환경이 필요. sprint-integration 영역으로 이관.
    - tests/integration/ — asyncpg event loop teardown race (알려진 flaky).
      별도 단독 실행으로만 검증. 본 회귀 게이트에서는 제외하여 false positive 방지.
    """
    proc = _run(
        [
            "uv",
            "run",
            "pytest",
            "-x",
            "--ignore=tests/harness",
            "--ignore=tests/contract",
            "--ignore=tests/integration",
            "-p",
            "no:cacheprovider",
            "-q",
            "--tb=short",
        ]
    )
    assert proc.returncode == 0, (
        f"pytest non-zero exit. stderr tail:\n{proc.stderr[-2000:]}\n"
        f"stdout tail:\n{proc.stdout[-2000:]}"
    )
    # 회귀 가드: pytest 가 수집한 테스트 수가 425 이상이어야 함 (memory 2026-04-24 기준)
    assert " passed" in proc.stdout
    last_summary_line = [ln for ln in proc.stdout.splitlines() if " passed" in ln][-1]
    # 예: "425 passed in 12.34s" 또는 "425 passed, 2 warnings in 12.34s"
    passed_count = int(last_summary_line.split(" passed")[0].split()[-1])
    assert passed_count >= 425, f"pytest passed={passed_count} < 425 회귀 의심"


def test_ruff_check_zero_error() -> None:
    """ruff check (lint) 0 error."""
    proc = _run(["uv", "run", "ruff", "check", "app", "tests"])
    assert proc.returncode == 0, f"ruff check 실패:\n{proc.stdout}\n{proc.stderr}"


def test_ruff_format_clean() -> None:
    """ruff format --check 0 diff."""
    proc = _run(["uv", "run", "ruff", "format", "--check", "app", "tests"])
    assert proc.returncode == 0, f"ruff format diff 존재:\n{proc.stdout}\n{proc.stderr}"


def test_alembic_history_linear() -> None:
    """Alembic 리비전 그래프가 단일 head 여야 한다 (브랜치 충돌 금지)."""
    proc = _run(["uv", "run", "alembic", "heads"])
    assert proc.returncode == 0, f"alembic heads 실패: {proc.stderr}"
    head_lines = [ln for ln in proc.stdout.splitlines() if "(head)" in ln]
    assert len(head_lines) == 1, f"단일 head 가 아님 ({len(head_lines)}):\n{proc.stdout}"


def test_openapi_export_idempotent() -> None:
    """app.export_openapi 재실행 결과가 shared/openapi.json 과 path/schema 키 동등."""
    shared_path = REPO_ROOT / "shared" / "openapi.json"
    on_disk = json.loads(shared_path.read_text(encoding="utf-8"))
    proc = _run(["uv", "run", "python", "-m", "app.export_openapi"])
    assert proc.returncode == 0, f"export_openapi 실패: {proc.stderr}"
    # stdout 은 ensure_ascii=True 로 출력될 수 있으나 json.loads 는 동일 dict 를 반환
    fresh = json.loads(proc.stdout)
    # paths 키 집합 + components.schemas 키 집합이 정확히 일치해야 함
    assert set(on_disk["paths"].keys()) == set(fresh["paths"].keys()), (
        "OpenAPI paths drift: "
        f"+{set(fresh['paths']) - set(on_disk['paths'])} "
        f"-{set(on_disk['paths']) - set(fresh['paths'])}"
    )
    assert set(on_disk["components"]["schemas"].keys()) == set(
        fresh["components"]["schemas"].keys()
    ), "OpenAPI components.schemas drift"


@pytest.mark.parametrize(
    "route_module",
    [
        "app.api.health",
        "app.api.market",
        "app.api.portfolio",
        "app.api.watchlist",
        "app.api.copilot",
        "app.api.notifications",
        "app.api.search",
        "app.api.upload",
        "app.api.user",
        "app.api.analyze",
        "app.api.ws",
    ],
)
def test_api_modules_importable(route_module: str) -> None:
    """모든 라우터 모듈이 import-time 부작용 없이 로드되어야 한다."""
    mod = importlib.import_module(route_module)
    assert hasattr(mod, "router"), f"{route_module} 에 router 객체 없음"

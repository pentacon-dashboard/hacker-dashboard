"""sprint-06 acceptance — integration / goldens / ADR / README / harness-green."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

ADR_REQUIRED_KEYWORDS: dict[str, tuple[str, ...]] = {
    "0011-copilot-sse-and-multistep-orchestration.md": (
        r"step_id.*final|final.*step_id",
        r"\bSSE\b",
        r"router",
    ),
    "0012-news-rag-vector-store.md": (
        r"\b1024\b",
        r"ivfflat",
        r"stub",
    ),
}


def test_adr_files_present_and_nonempty() -> None:
    for name in ADR_REQUIRED_KEYWORDS:
        p = REPO_ROOT / "docs/adr" / name
        assert p.exists(), f"missing {name}"
        txt = p.read_text("utf-8")
        for section in ("## 맥락", "## 결정", "## 결과"):
            assert section in txt, f"{name} missing {section}"
            m = re.search(rf"{section}\s*(.*?)(?=\n## |\Z)", txt, flags=re.S)
            assert m and len(m.group(1).strip()) >= 80, f"{name} {section} too short"


def test_adr_content_covers_required_decisions() -> None:
    for name, patterns in ADR_REQUIRED_KEYWORDS.items():
        txt = (REPO_ROOT / "docs/adr" / name).read_text("utf-8")
        for pat in patterns:
            assert re.search(pat, txt, flags=re.I), f"{name}: required decision {pat!r} not covered"


def test_demo_script_merged_into_rehearsal() -> None:
    rehearsal = REPO_ROOT / "docs/qa/demo-rehearsal-2026-04-22.md"
    assert rehearsal.exists(), "rehearsal doc must already exist"
    txt = rehearsal.read_text("utf-8")
    assert "## Copilot 시나리오" in txt
    assert "8분" in txt or "480" in txt
    # bullet 최소 6개 (비트 시간표 + 관전 포인트)
    section = re.search(r"## Copilot 시나리오(.*?)(?=\n## |\Z)", txt, flags=re.S)
    assert section and section.group(1).count("- ") >= 6
    # 기존 copilot-demo.md 새 파일 생성 금지
    assert not (REPO_ROOT / "docs/demo/copilot-demo.md").exists(), \
        "use rehearsal doc merge, not a new copilot-demo.md"


def test_readme_has_copilot_section_and_links() -> None:
    readme = (REPO_ROOT / "README.md").read_text("utf-8")
    assert "## Copilot" in readme or "## 자연어 Copilot" in readme
    for shot in ("copilot-query.png", "copilot-final-card.png"):
        path = REPO_ROOT / "docs/screenshots" / shot
        assert path.exists(), f"screenshot missing: {shot}"
        assert path.stat().st_size >= 5_000, f"{shot} looks like placeholder (<5KB)"
        assert shot in readme, f"README missing link to {shot}"


def test_golden_end_to_end_suite_passes() -> None:
    """ASGI in-process 실행: subprocess 는 fake fixture 상속 목적상 허용."""
    result = subprocess.run(
        ["uv", "run", "pytest", "-q",
         "tests/golden/test_copilot_end_to_end.py", "--tb=short"],
        cwd=REPO_ROOT / "backend",
        capture_output=True, text=True, timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_golden_coverage_is_ten() -> None:
    samples = list((REPO_ROOT / "backend/tests/golden/samples/copilot").glob("*.json"))
    ids = {p.stem for p in samples}
    # sprint-03 의 9건 + follow_up_2turn 1건
    required = {
        "comparison_01", "comparison_02", "comparison_03",
        "simulator_01", "simulator_02", "simulator_03",
        "news_rag_01", "news_rag_02", "news_rag_03",
        "follow_up_2turn",
    }
    missing = required - ids
    assert not missing, f"missing goldens: {missing}"


def test_harness_contracts_still_green() -> None:
    """AC-06-8: sprint-01~06 harness 전체가 sprint-06 통합 브랜치에서 green."""
    result = subprocess.run(
        ["uv", "run", "pytest", "-q",
         "tests/harness/", "--lf", "--ff", "--tb=short"],
        cwd=REPO_ROOT / "backend",
        capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fake_fixtures_available_for_inheritance() -> None:
    """AC-06-9: conftest 의 fake_* fixture 가 전역 autouse 로 선언돼 있어야 한다."""
    conftest = (REPO_ROOT / "backend/tests/harness/conftest.py").read_text("utf-8")
    assert "fake_orchestrator_llm" in conftest
    assert "fake_planner_llm" in conftest
    assert "autouse=True" in conftest


def test_makefile_targets_present() -> None:
    mk = (REPO_ROOT / "Makefile").read_text("utf-8")
    assert re.search(r"^copilot-demo:", mk, flags=re.M), "Makefile: copilot-demo target missing"
    assert re.search(r"^ci-local:", mk, flags=re.M), "Makefile: ci-local target missing"


def test_e2e_npm_script_registered() -> None:
    pkg = json.loads((REPO_ROOT / "frontend/package.json").read_text("utf-8"))
    assert pkg.get("scripts", {}).get("test:e2e", "").startswith("playwright test")

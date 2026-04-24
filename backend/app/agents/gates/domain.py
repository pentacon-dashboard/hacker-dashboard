"""
Domain Gate — 도메인 sanity check.

규칙:
  1. 가격(price/close/open/high/low/rate) > 0
  2. 변동률 |%| < 1000
  3. 날짜 단조 증가 (정렬 허용 — 시퀀스가 있다면 내림차순이어도 단조면 OK)
  4. 자산군 일관성 — analyzer_output.asset_class 와 state.asset_class 가 일치
  5. 미래 날짜는 금지 (현재 시간 이후)

실패 시 재시도 금지 — 즉시 'fail: <reason>' 기록 후 상위로 전파.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.agents.state import AgentState

_PRICE_KEYS = ("price", "close", "open", "high", "low", "rate", "latest_close", "latest_price", "latest_rate")
_DATE_KEYS = ("date", "timestamp", "datetime", "time")
_RETURN_KEYS = ("period_return_pct", "period_change_pct", "change_pct", "return_pct")

# 포트폴리오/holdings 행에는 가격·날짜 검증을 일부 우회한다. 대신 _check_holdings 가 커버.
_HOLDING_HINT_KEYS = {"quantity", "avg_cost", "market", "code"}
# 포트폴리오 스냅샷 행
_SNAPSHOT_HINT_KEYS = {"snapshot_date", "total_value_krw", "total_pnl_krw"}


def _to_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_date(v: Any) -> datetime | None:
    if not isinstance(v, str):
        return None
    s = v.strip()
    # fromisoformat 은 'Z' 를 처리하지 못하므로 보정
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _is_holding_row(row: dict[str, Any]) -> bool:
    return bool(_HOLDING_HINT_KEYS & set(row.keys()))


def _is_snapshot_row(row: dict[str, Any]) -> bool:
    return bool(_SNAPSHOT_HINT_KEYS & set(row.keys()))


def _check_prices(rows: list[dict[str, Any]]) -> str | None:
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        # holdings / snapshots 행은 가격 체크를 건너뛴다 (스키마가 다름)
        if _is_holding_row(row) or _is_snapshot_row(row):
            continue
        for k in _PRICE_KEYS:
            if k in row:
                v = _to_float(row[k])
                if v is None:
                    continue
                if v <= 0:
                    return f"row {i}: {k}={v} is not positive"
    return None


def _check_holdings(rows: list[dict[str, Any]]) -> str | None:
    """포트폴리오 holdings 에 대한 sanity check — quantity > 0, avg_cost > 0."""
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if not _is_holding_row(row):
            continue
        for k in ("quantity", "avg_cost"):
            if k in row:
                v = _to_float(row[k])
                if v is None:
                    continue
                if v <= 0:
                    return f"row {i}: holding {k}={v} is not positive"
    return None


def _check_dates(rows: list[dict[str, Any]]) -> str | None:
    dates: list[tuple[int, datetime]] = []
    now = datetime.now(UTC)
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        for k in _DATE_KEYS:
            if k in row:
                dt = _to_date(row[k])
                if dt is not None:
                    if dt > now:
                        return f"row {i}: future date {row[k]!r}"
                    dates.append((i, dt))
                break

    if len(dates) < 2:
        return None

    # 단조(오름차순 또는 내림차순)인지 확인. 섞여있으면 fail.
    asc = all(dates[j][1] >= dates[j - 1][1] for j in range(1, len(dates)))
    desc = all(dates[j][1] <= dates[j - 1][1] for j in range(1, len(dates)))
    if not (asc or desc):
        return "dates are not monotonic"
    return None


def _check_returns(analyzer_output: dict[str, Any]) -> str | None:
    metrics = analyzer_output.get("metrics") or {}
    for k in _RETURN_KEYS:
        if k in metrics:
            v = _to_float(metrics[k])
            if v is None:
                continue
            if abs(v) >= 1000:
                return f"metrics.{k}={v}% exceeds absolute 1000%"
    return None


def _check_consistency(state: AgentState) -> str | None:
    expected = state.get("asset_class")
    output = state.get("analyzer_output") or {}
    got = output.get("asset_class")
    # mixed/portfolio 는 router 결정이 그대로 분석기 자산군이 되므로 mismatch 허용
    if got and expected and got != expected and expected not in {"mixed", "portfolio"}:
        return f"asset_class mismatch: router={expected}, analyzer={got}"
    return None


async def domain_gate(state: AgentState) -> AgentState:
    """
    도메인 sanity check 노드. 검증 순서대로 첫 실패에서 중단.
    """
    rows = state.get("input_data") or []
    output = state.get("analyzer_output") or {}

    checks = [
        _check_prices(rows),
        _check_holdings(rows),
        _check_dates(rows),
        _check_returns(output) if isinstance(output, dict) else None,
        _check_consistency(state),
    ]
    for reason in checks:
        if reason:
            return _mark(state, f"fail: {reason}")

    return _mark(state, "pass")


def _mark(state: AgentState, status: str) -> AgentState:
    return {**state, "gates": {**state["gates"], "domain_gate": status}}

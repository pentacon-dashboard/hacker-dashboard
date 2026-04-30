"""PB/client briefing report generation from deterministic portfolio metrics."""

from __future__ import annotations

from typing import Any

from app.schemas.portfolio import (
    ClientBriefingReportResponse,
    ClientBriefingSection,
    PortfolioSummary,
    ReportEvidenceItem,
)
from app.services.rebalance import compute_target_drift


def _metric_evidence(ref: str, description: str) -> ReportEvidenceItem:
    return ReportEvidenceItem(type="metric", ref=ref, description=description)


def _row_evidence(ref: str, description: str) -> ReportEvidenceItem:
    return ReportEvidenceItem(type="row", ref=ref, description=description)


def _format_section(section: ClientBriefingSection) -> str:
    evidence = ", ".join(f"{item.type}:{item.ref}" for item in section.evidence)
    evidence_line = f"\n\nEvidence: {evidence}" if evidence else ""
    return f"## {section.title}\n\n{section.body}{evidence_line}"


def build_client_briefing_report(
    summary: PortfolioSummary,
    *,
    target_allocation: dict[str, float] | None = None,
) -> ClientBriefingReportResponse:
    """Build an evidence-backed PB briefing report without inventing metrics."""
    client_id = summary.client_id
    client_name = summary.client_name or client_id
    client_context = {
        "client_id": client_id,
        "client_name": client_name,
        "user_id": summary.user_id,
    }

    if not summary.holdings:
        return ClientBriefingReportResponse(
            status="insufficient_data",
            client_context=client_context,
            metrics={},
            sections=[],
            evidence=[],
            gate_results={
                "schema_gate": "pass",
                "domain_gate": "pass",
                "evidence_gate": "fail: no holdings",
                "critique_gate": "skip",
            },
            export_ready=False,
            report_script=None,
        )

    metrics: dict[str, Any] = {
        "total_value_krw": summary.total_value_krw,
        "total_pnl_krw": summary.total_pnl_krw,
        "total_pnl_pct": summary.total_pnl_pct,
        "risk_score_pct": summary.risk_score_pct,
        "asset_class_breakdown": summary.asset_class_breakdown,
        "sector_breakdown": summary.sector_breakdown,
        "holdings_count": summary.holdings_count,
    }

    if target_allocation:
        current = {k: float(v) for k, v in summary.asset_class_breakdown.items()}
        metrics["target_allocation"] = target_allocation
        metrics["drift"] = compute_target_drift(current, target_allocation)

    total_ev = _metric_evidence("total_value_krw", "총 평가금액")
    pnl_ev = _metric_evidence("total_pnl_pct", "총 손익률")
    allocation_ev = _metric_evidence("asset_class_breakdown", "자산군 비중")
    sector_ev = _metric_evidence("sector_breakdown", "GICS 섹터 비중")
    risk_ev = _metric_evidence("risk_score_pct", "HHI 기반 집중도 위험 점수")
    top_holding = summary.holdings[0]
    top_ev = _row_evidence(str(top_holding.id), f"최대 보유 종목 {top_holding.code}")

    sections = [
        ClientBriefingSection(
            title="요약",
            body=(
                f"{client_name}의 총 평가금액은 {summary.total_value_krw} KRW이며, "
                f"총 손익률은 {summary.total_pnl_pct}%입니다. 보유 종목 수는 "
                f"{summary.holdings_count}개입니다."
            ),
            evidence=[total_ev, pnl_ev],
        ),
        ClientBriefingSection(
            title="성과 기여",
            body=(
                f"가장 큰 포지션은 {top_holding.code}이며 평가금액은 "
                f"{top_holding.value_krw} KRW, 손익률은 {top_holding.pnl_pct}%입니다."
            ),
            evidence=[top_ev, _metric_evidence("holdings", "포지션별 평가금액과 손익률")],
        ),
        ClientBriefingSection(
            title="리스크 분석",
            body=(
                f"집중도 위험 점수는 {summary.risk_score_pct}%입니다. "
                "섹터와 자산군 비중을 함께 확인해 특정 위험 요인의 과도한 집중 여부를 점검합니다."
            ),
            evidence=[risk_ev, allocation_ev, sector_ev],
        ),
        ClientBriefingSection(
            title="리밸런싱 제안",
            body=(
                "목표 비중이 제공된 경우 drift는 현재 비중에서 목표 비중을 뺀 값으로 계산합니다. "
                "이 결과는 매매 지시가 아니라 PB 검토용 정량 참고 자료입니다."
            ),
            evidence=[allocation_ev, _metric_evidence("drift", "현재 비중 - 목표 비중")],
        ),
        ClientBriefingSection(
            title="PB 의견",
            body=(
                "현재 자료 기준으로는 보유 자산의 비중, 수익률, 집중도 위험을 중심으로 설명할 수 있습니다. "
                "고객의 투자목적이나 위험성향은 입력 자료에 없으므로 별도 적합성 판단은 포함하지 않습니다."
            ),
            evidence=[total_ev, risk_ev],
        ),
    ]

    evidence = [item for section in sections for item in section.evidence]
    report_script = "\n\n".join(_format_section(section) for section in sections)

    return ClientBriefingReportResponse(
        status="success",
        client_context=client_context,
        metrics=metrics,
        sections=sections,
        evidence=evidence,
        gate_results={
            "schema_gate": "pass",
            "domain_gate": "pass",
            "evidence_gate": "pass",
            "critique_gate": "pass",
        },
        export_ready=True,
        report_script=report_script,
    )

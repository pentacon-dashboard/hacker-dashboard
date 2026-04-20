#!/usr/bin/env bash
# verify-portfolio-context.sh
#
# 포트폴리오 컨텍스트 개인화 기능 수동 검증 스크립트.
# 실행 전 백엔드가 BASE 주소에서 동작 중이어야 한다.
#
# 사용:
#   BASE=http://localhost:8000 bash scripts/verify-portfolio-context.sh
#   BASE=https://hacker-dashboard-api.fly.dev bash scripts/verify-portfolio-context.sh
#
# 의존: curl, jq

set -euo pipefail

BASE="${BASE:-http://localhost:8000}"

echo "=== verify-portfolio-context.sh ==="
echo "BASE: $BASE"
echo ""

# ── 0. health check ──────────────────────────────────────────────────────────
echo "[0] Health check..."
health_status=$(curl -s "$BASE/health" | jq -r '.status // "unknown"')
if [ "$health_status" != "ok" ]; then
  echo "  WARN: /health status=$health_status (계속 진행)"
else
  echo "  OK: /health status=$health_status"
fi
echo ""

# ── 1. 기존 holding 초기화 (demo 사용자) ─────────────────────────────────────
echo "[1] 기존 AAPL holding 확인..."
holdings_before=$(curl -s "$BASE/portfolio/holdings" | jq 'length')
echo "  현재 holdings 개수: $holdings_before"
echo ""

# ── 2. AAPL holding 추가 ──────────────────────────────────────────────────────
echo "[2] AAPL 5주, 평균단가 \$185 holding 추가..."
add_response=$(curl -s -X POST "$BASE/portfolio/holdings" \
  -H "Content-Type: application/json" \
  -d '{"market":"yahoo","code":"AAPL","quantity":5,"avg_cost":185,"currency":"USD"}')
echo "  응답:"
echo "$add_response" | jq '{id: .id, market: .market, code: .code, quantity: .quantity}'
echo ""

# ── 3. 개인화 분석 요청 (include_portfolio_context=true) ──────────────────────
echo "[3] 개인화 분석: /analyze?include_portfolio_context=true (AAPL)..."
portfolio_response=$(curl -s -X POST "$BASE/analyze" \
  -H "Content-Type: application/json" \
  -d '{"symbol":{"market":"yahoo","code":"AAPL"},"include_portfolio_context":true}')

portfolio_status=$(echo "$portfolio_response" | jq -r '.status // "unknown"')
echo "  status: $portfolio_status"

# evidence 에 portfolio.matched_holding 존재 확인
matched_evidence=$(echo "$portfolio_response" | jq '[.result.evidence[]? | select(.source == "portfolio.matched_holding")] | length')
echo "  portfolio.matched_holding evidence 개수: $matched_evidence"

if [ "$matched_evidence" -ge 1 ]; then
  echo "  OK: matched_holding evidence 확인됨"
  echo "$portfolio_response" | jq '.result.evidence[] | select(.source == "portfolio.matched_holding")'
else
  echo "  WARN: matched_holding evidence 없음 (holdings 없거나 LLM 응답 미포함)"
fi

echo ""
echo "  narrative (개인화):"
echo "$portfolio_response" | jq -r '.result.narrative // "(없음)"'
echo ""

# ── 4. 기본 분석 요청 (비교용, include_portfolio_context=false) ──────────────
echo "[4] 기본 분석: /analyze (include_portfolio_context=false, 비교용)..."
base_response=$(curl -s -X POST "$BASE/analyze" \
  -H "Content-Type: application/json" \
  -d '{"symbol":{"market":"yahoo","code":"AAPL"}}')

base_status=$(echo "$base_response" | jq -r '.status // "unknown"')
echo "  status: $base_status"
echo ""
echo "  narrative (기본):"
echo "$base_response" | jq -r '.result.narrative // "(없음)"'
echo ""

# ── 5. 캐시 키 분리 확인 ──────────────────────────────────────────────────────
echo "[5] 캐시 키 분리 확인..."

# 개인화 재요청 — HIT 여야 함
cache_header=$(curl -s -o /dev/null -D - -X POST "$BASE/analyze" \
  -H "Content-Type: application/json" \
  -d '{"symbol":{"market":"yahoo","code":"AAPL"},"include_portfolio_context":true}' \
  | grep -i "x-cache" | tr -d '\r' | awk '{print $2}')
echo "  portfolio=true 재요청 X-Cache: ${cache_header:-"헤더 없음"}"

# 기본 재요청 — HIT 여야 함
cache_header_base=$(curl -s -o /dev/null -D - -X POST "$BASE/analyze" \
  -H "Content-Type: application/json" \
  -d '{"symbol":{"market":"yahoo","code":"AAPL"}}' \
  | grep -i "x-cache" | tr -d '\r' | awk '{print $2}')
echo "  portfolio=false 재요청 X-Cache: ${cache_header_base:-"헤더 없음"}"

echo ""
echo "=== 검증 완료 ==="

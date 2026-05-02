"""
schemathesis state machine 기반 계약 테스트 진입점.

CI 에서는 cli 직접 실행 (ci.yml / contract.yml 참고). 이 파일은 로컬 pytest 연동용.

실행:
    pytest backend/tests/contract/test_openapi.py -v
    (백엔드 서버가 localhost:8000 에서 실행 중이어야 함)

CLI 동등 명령 (shared/openapi.json 1583라인 기준):
    schemathesis run shared/openapi.json \
        --base-url http://localhost:8000 \
        --checks all \
        --hypothesis-deadline=none \
        --max-examples=50 \
        --show-errors-tracebacks \
        --junit-xml=contract-results.xml

검증 대상 엔드포인트 (week-3 신규 포함):
    GET  /health
    GET  /market/symbols
    GET  /market/symbols/search?q=BTC
    GET  /market/quotes/{symbol}
    GET  /market/quotes/{market}/{code}
    GET  /market/ohlc/{market}/{code}
    GET  /market/watchlist/items
    POST /market/watchlist/items
    DELETE /market/watchlist/items/{item_id}
    POST /analyze
    GET  /portfolio/holdings
    POST /portfolio/holdings
    PATCH /portfolio/holdings/{holding_id}
    DELETE /portfolio/holdings/{holding_id}
    GET  /portfolio/summary
    GET  /portfolio/snapshots
"""

import os

import pytest
import schemathesis
from hypothesis import settings
from schemathesis.config import ProjectConfig, ProjectsConfig, SchemathesisConfig

# 환경변수로 base URL 오버라이드 가능. 기본값은 로컬 개발 서버
BASE_URL = os.getenv("CONTRACT_BASE_URL", "http://127.0.0.1:8000")
MAX_EXAMPLES = int(os.getenv("CONTRACT_MAX_EXAMPLES", "1"))
REQUEST_TIMEOUT_SEC = float(os.getenv("CONTRACT_REQUEST_TIMEOUT_SEC", "5"))
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "openapi.json")
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_CONTRACT_TESTS") != "1",
    reason="external OpenAPI contract fuzzing is opt-in; set RUN_CONTRACT_TESTS=1",
)

# openapi.json 이 아직 없으면 테스트 스킵 (스켈레톤 단계)
if not os.path.exists(SCHEMA_PATH):
    pytest.skip(
        reason=f"shared/openapi.json 없음 — BE 팀에서 export 후 재실행: {SCHEMA_PATH}",
        allow_module_level=True,
    )

# schemathesis v4: config 객체로 base_url 주입
_config = SchemathesisConfig(
    projects=ProjectsConfig(
        default=ProjectConfig(base_url=BASE_URL),
    )
)
schema = schemathesis.openapi.from_path(SCHEMA_PATH, config=_config)


@schema.parametrize()
@settings(max_examples=MAX_EXAMPLES, deadline=None)
def test_api_contracts(case: schemathesis.Case) -> None:
    """모든 엔드포인트에 대해 schemathesis 가 생성한 요청을 실행하고 응답 스키마를 검증."""
    response = case.call(timeout=REQUEST_TIMEOUT_SEC)
    case.validate_response(response)

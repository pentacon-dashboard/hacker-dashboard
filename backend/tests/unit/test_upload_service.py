"""업로드 서비스 단위 테스트 — sprint-08 Phase B-5."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.upload import (
    build_validation_result,
    detect_portfolio_schema,
    get_cached_df,
    normalize_holdings_from_csv,
    parse_csv,
)

_GOLDEN_DIR = Path(__file__).parent.parent / "golden" / "upload_samples"

# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────


def _csv(
    rows: list[str], header: str = "date,market,code,quantity,avg_cost,currency,note"
) -> bytes:
    lines = [header] + rows
    return "\n".join(lines).encode("utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# parse_csv — 정상 케이스
# ──────────────────────────────────────────────────────────────────────────────


class TestParseCsvNormal:
    def test_normal_file_no_errors(self):
        """정상 CSV → 오류 없음."""
        content = _csv(
            [
                "2024-01-15,yahoo,AAPL,10,182.50,USD,note",
                "2024-03-22,upbit,KRW-BTC,0.05,85000000,KRW,note",
            ]
        )
        df, errors = parse_csv(content)
        assert len(errors) == 0
        assert len(df) == 2

    def test_column_normalization(self):
        """헤더 대소문자 정규화."""
        content = b"Date,Market,Code,Quantity,Avg_Cost,Currency,Note\n2024-01-01,yahoo,AAPL,10,150.00,USD,test\n"
        df, errors = parse_csv(content)
        assert "date" in df.columns
        assert "market" in df.columns

    def test_bom_utf8(self):
        """BOM 포함 UTF-8 파싱."""
        content = b"\xef\xbb\xbfdate,market,code,quantity,avg_cost,currency,note\n2024-01-01,yahoo,AAPL,10,150.00,USD,\n"
        df, errors = parse_csv(content)
        # BOM 제거 후 정상 파싱
        bom_errors = [e for e in errors if e.code == "missing_columns"]
        assert len(bom_errors) == 0

    def test_unicode_content(self):
        """한국어 note 파싱."""
        content = "date,market,code,quantity,avg_cost,currency,note\n2024-01-15,naver_kr,005930,100,72000,KRW,삼성전자 한국어 메모\n".encode()
        df, errors = parse_csv(content)
        assert len(errors) == 0

    def test_preview_columns_lowercase(self):
        """파싱 후 컬럼명 모두 소문자."""
        content = _csv(["2024-01-01,yahoo,AAPL,10,150.00,USD,"])
        df, _ = parse_csv(content)
        for col in df.columns:
            assert col == col.lower()


# ──────────────────────────────────────────────────────────────────────────────
# parse_csv — 오류 케이스
# ──────────────────────────────────────────────────────────────────────────────


class TestParseCsvErrors:
    def test_empty_file(self):
        """빈 파일 → empty_file 오류."""
        df, errors = parse_csv(b"")
        codes = [e.code for e in errors]
        assert "empty_file" in codes

    def test_missing_required_columns(self):
        """필수 컬럼 누락 → missing_columns 오류."""
        content = b"date,market,code\n2024-01-01,yahoo,AAPL\n"
        df, errors = parse_csv(content)
        codes = [e.code for e in errors]
        assert "missing_columns" in codes

    def test_invalid_date_format(self):
        """날짜 형식 오류 → invalid_date."""
        content = _csv(["2024-13-45,yahoo,AAPL,10,150.00,USD,note"])
        df, errors = parse_csv(content)
        codes = [e.code for e in errors]
        assert "invalid_date" in codes

    def test_invalid_date_not_iso(self):
        """YYYY/MM/DD 형식 → invalid_date."""
        content = _csv(["2024/01/15,yahoo,AAPL,10,150.00,USD,note"])
        df, errors = parse_csv(content)
        codes = [e.code for e in errors]
        assert "invalid_date" in codes

    def test_negative_quantity(self):
        """수량 음수 → negative_quantity."""
        content = _csv(["2024-01-15,yahoo,AAPL,-10,150.00,USD,note"])
        df, errors = parse_csv(content)
        codes = [e.code for e in errors]
        assert "negative_quantity" in codes

    def test_zero_quantity(self):
        """수량 0 → negative_quantity (0 초과 필요)."""
        content = _csv(["2024-01-15,yahoo,AAPL,0,150.00,USD,note"])
        df, errors = parse_csv(content)
        codes = [e.code for e in errors]
        assert "negative_quantity" in codes

    def test_unknown_currency(self):
        """미지원 통화 → unknown_currency."""
        content = _csv(["2024-01-15,yahoo,AAPL,10,150.00,BTC,note"])
        df, errors = parse_csv(content)
        codes = [e.code for e in errors]
        assert "unknown_currency" in codes

    def test_multiple_errors_in_one_file(self):
        """여러 오류 동시 감지."""
        content = _csv(
            [
                "2024-01-15,yahoo,AAPL,10,182.50,USD,정상",
                "bad-date,yahoo,AAPL,-5,150.00,BTC,다중오류",
            ]
        )
        df, errors = parse_csv(content)
        codes = [e.code for e in errors]
        assert "invalid_date" in codes
        assert "negative_quantity" in codes
        assert "unknown_currency" in codes

    def test_error_has_row_number(self):
        """오류에 row 번호 포함."""
        content = _csv(["2024-13-45,yahoo,AAPL,10,150.00,USD,note"])
        df, errors = parse_csv(content)
        date_errors = [e for e in errors if e.code == "invalid_date"]
        assert len(date_errors) > 0
        assert date_errors[0].row == 2  # 헤더=1, 첫 데이터=2

    def test_error_has_column_name(self):
        """오류에 컬럼명 포함."""
        content = _csv(["2024-01-15,yahoo,AAPL,10,150.00,BTC,note"])
        df, errors = parse_csv(content)
        currency_errors = [e for e in errors if e.code == "unknown_currency"]
        assert currency_errors[0].column == "currency"


# ──────────────────────────────────────────────────────────────────────────────
# build_validation_result
# ──────────────────────────────────────────────────────────────────────────────


class TestBuildValidationResult:
    def test_upload_id_is_uuid(self):
        """upload_id 는 UUID 형식."""
        import uuid

        content = _csv(["2024-01-15,yahoo,AAPL,10,150.00,USD,note"])
        df, errors = parse_csv(content)
        result = build_validation_result(df, errors)
        # UUID 파싱 가능해야 함
        parsed = uuid.UUID(result.upload_id)
        assert str(parsed) == result.upload_id

    def test_preview_max_5_rows(self):
        """preview 최대 5행."""
        rows = [f"2024-01-{i:02d},yahoo,AAPL,10,150.00,USD,note" for i in range(1, 11)]
        content = _csv(rows)
        df, errors = parse_csv(content)
        result = build_validation_result(df, errors)
        assert len(result.preview) <= 5

    def test_total_rows_correct(self):
        """total_rows 계산."""
        content = _csv(
            [
                "2024-01-15,yahoo,AAPL,10,150.00,USD,note",
                "2024-02-15,yahoo,MSFT,5,300.00,USD,note",
            ]
        )
        df, errors = parse_csv(content)
        result = build_validation_result(df, errors)
        assert result.total_rows == 2

    def test_cache_stores_df(self):
        """build 후 get_cached_df 로 조회 가능."""
        content = _csv(["2024-01-15,yahoo,AAPL,10,150.00,USD,note"])
        df, errors = parse_csv(content)
        result = build_validation_result(df, errors)
        cached = get_cached_df(result.upload_id)
        assert cached is not None
        assert len(cached) == 1

    def test_unknown_upload_id_returns_none(self):
        """존재하지 않는 upload_id → None."""
        result = get_cached_df("not-a-real-id-12345")
        assert result is None

    def test_schema_fingerprint_is_hex(self):
        """schema_fingerprint 는 16진수 8자리."""
        content = _csv(["2024-01-15,yahoo,AAPL,10,150.00,USD,note"])
        df, errors = parse_csv(content)
        result = build_validation_result(df, errors)
        fp = result.schema_fingerprint
        assert len(fp) == 8
        int(fp, 16)  # 16진수 파싱 가능해야 함

    def test_created_at_is_iso(self):
        """created_at 은 ISO 형식."""
        from datetime import datetime

        content = _csv(["2024-01-15,yahoo,AAPL,10,150.00,USD,note"])
        df, errors = parse_csv(content)
        result = build_validation_result(df, errors)
        dt = datetime.fromisoformat(result.created_at)
        assert dt.year >= 2024


# ──────────────────────────────────────────────────────────────────────────────
# 임의 broker CSV schema detection / normalization
# ──────────────────────────────────────────────────────────────────────────────


class TestBrokerCsvIntake:
    def test_korean_broker_columns_normalize_to_holdings(self):
        """한국어 broker CSV 컬럼을 표준 holdings 로 정규화한다."""
        content = (
            "고객ID,계좌번호,종목코드,종목명,보유수량,평균단가,통화\n"
            "client-777,123-45,005930,삼성전자,10,72000,KRW\n"
        ).encode()

        df, errors = parse_csv(content)
        result = build_validation_result(df, errors)

        assert result.import_status == "imported"
        assert result.error_rows == 0
        assert len(result.normalized_holdings) == 1

        holding = result.normalized_holdings[0]
        assert holding.client_id == "client-777"
        assert holding.account == "123-45"
        assert holding.code == "005930"
        assert holding.name == "삼성전자"
        assert holding.quantity == "10"
        assert holding.avg_cost == "72000"
        assert holding.currency == "KRW"
        assert holding.market == "naver_kr"
        assert holding.source_row == 2

        symbol_mapping = next(m for m in result.field_mappings if m.standard_field == "symbol")
        assert symbol_mapping.source_column == "종목코드"
        assert symbol_mapping.confidence >= 0.95
        assert symbol_mapping.needs_review is False

    def test_missing_core_fields_returns_insufficient_data(self):
        """보유자산 핵심 필드를 매핑하지 못하면 holdings 를 만들지 않는다."""
        content = "종목명,메모\n삼성전자,관심종목\n".encode()

        df, errors = parse_csv(content)
        result = build_validation_result(df, errors)

        assert result.import_status == "insufficient_data"
        assert result.normalized_holdings == []
        assert any(error.code == "missing_columns" for error in result.errors)

    def test_duplicate_symbol_candidates_need_review(self):
        """중복 symbol 후보는 자동 매핑하지 않고 PB 확인 대상으로 둔다."""
        content = (
            b"symbol,ticker,quantity,avg_cost,currency\n"
            b"AAPL,MSFT,3,180,USD\n"
        )

        df, errors = parse_csv(content)
        schema = detect_portfolio_schema(df)

        symbol_mapping = next(m for m in schema.field_mappings if m.standard_field == "symbol")
        assert symbol_mapping.needs_review is True
        assert symbol_mapping.confidence < 0.95

        normalized = normalize_holdings_from_csv(df, schema)
        assert normalized.status == "needs_confirmation"
        assert normalized.holdings == []


# ──────────────────────────────────────────────────────────────────────────────
# 골든 샘플 기반 테스트
# ──────────────────────────────────────────────────────────────────────────────


def test_golden_normal_01():
    """골든: normal_01.csv → 오류 없음."""
    path = _GOLDEN_DIR / "normal_01.csv"
    if not path.exists():
        pytest.skip("골든 파일 없음")
    content = path.read_bytes()
    df, errors = parse_csv(content)
    assert len(errors) == 0
    assert len(df) == 5


def test_golden_normal_02():
    """골든: normal_02.csv → 오류 없음."""
    path = _GOLDEN_DIR / "normal_02.csv"
    if not path.exists():
        pytest.skip("골든 파일 없음")
    content = path.read_bytes()
    df, errors = parse_csv(content)
    assert len(errors) == 0
    assert len(df) == 2


def test_golden_partial_error_01():
    """골든: partial_error_01.csv → 오류 3개 이상."""
    path = _GOLDEN_DIR / "partial_error_01.csv"
    if not path.exists():
        pytest.skip("골든 파일 없음")
    content = path.read_bytes()
    df, errors = parse_csv(content)
    assert len(errors) >= 3


def test_golden_empty_file():
    """골든: empty_file.csv → empty_file 오류."""
    path = _GOLDEN_DIR / "empty_file.csv"
    if not path.exists():
        pytest.skip("골든 파일 없음")
    content = path.read_bytes()
    df, errors = parse_csv(content)
    codes = [e.code for e in errors]
    assert "empty_file" in codes


def test_golden_header_only():
    """골든: header_only.csv → 오류 없음, 0행."""
    path = _GOLDEN_DIR / "header_only.csv"
    if not path.exists():
        pytest.skip("골든 파일 없음")
    content = path.read_bytes()
    df, errors = parse_csv(content)
    # 헤더만 있으면 오류 없고 0행
    assert len(df) == 0


def test_golden_unicode_01():
    """골든: unicode_01.csv → 오류 없음 (한국어 + 이모지)."""
    path = _GOLDEN_DIR / "unicode_01.csv"
    if not path.exists():
        pytest.skip("골든 파일 없음")
    content = path.read_bytes()
    df, errors = parse_csv(content)
    assert len(errors) == 0

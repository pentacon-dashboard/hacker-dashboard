-- scripts/neon-setup.sql — 데모 시드 데이터 (현재 스키마)
-- 실행: psql "$DATABASE_URL" -f scripts/neon-setup.sql
--
-- 주의: 이 파일은 데모 전용입니다. 실거래 데이터가 아닙니다.
-- DDL(테이블 생성)은 Alembic 마이그레이션으로 처리합니다:
--   cd backend && uv run alembic upgrade head

-- ── holdings 시드 (user_id='demo' 고정) ──────────────────────────────────────
-- DELETE + INSERT 방식으로 idempotent 보장 (유니크 제약 없이도 안전)
BEGIN;

DELETE FROM holdings WHERE user_id = 'demo';

INSERT INTO holdings (user_id, market, code, quantity, avg_cost, currency, created_at, updated_at)
VALUES
  ('demo', 'naver_kr', '005930',   10,        75000,     'KRW', NOW(), NOW()),
  ('demo', 'yahoo',    'AAPL',      5,        185.0,     'USD', NOW(), NOW()),
  ('demo', 'yahoo',    'TSLA',      3,        250.0,     'USD', NOW(), NOW()),
  ('demo', 'upbit',    'KRW-BTC',   0.05, 85000000,     'KRW', NOW(), NOW()),
  ('demo', 'upbit',    'KRW-ETH',   1.2,   4500000,     'KRW', NOW(), NOW());

COMMIT;

-- 삽입 확인
SELECT user_id, market, code, quantity, avg_cost, currency
FROM holdings
WHERE user_id = 'demo'
ORDER BY id;

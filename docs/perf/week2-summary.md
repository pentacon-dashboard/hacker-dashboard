# Lighthouse Week-2 요약

측정일: 2026-04-19 (placeholder — Lighthouse CLI 미실행)

| 페이지 | Performance | Accessibility | Best Practices | SEO |
|--------|-------------|---------------|----------------|-----|
| / (홈) | - | - | - | - |
| /watchlist | - | - | - | - |
| /symbol/upbit/KRW-BTC | - | - | - | - |

> 목표: Performance 90+, Accessibility 90+

## 스킵 사유

로컬 환경(Windows 10 Home, Docker Desktop 미기동)에서 `npm run build && npm run start` 후
Lighthouse CLI 실행 시 Chrome headless 바이너리 경로 문제로 실행 불가.

## 실행 방법 (CI 또는 Linux 환경)

```bash
# 1. frontend 빌드 및 기동
cd frontend
npm ci
npm run build
npm run start &

# 2. Lighthouse CLI 설치 및 측정
npm install -g lighthouse

lighthouse http://localhost:3000/ \
  --output=json \
  --output-path=docs/perf/lighthouse-week2-home.json \
  --chrome-flags="--headless --no-sandbox --disable-gpu" \
  --quiet

lighthouse http://localhost:3000/watchlist \
  --output=json \
  --output-path=docs/perf/lighthouse-week2-watchlist.json \
  --chrome-flags="--headless --no-sandbox --disable-gpu" \
  --quiet

lighthouse http://localhost:3000/symbol/upbit/KRW-BTC \
  --output=json \
  --output-path=docs/perf/lighthouse-week2-symbol-detail.json \
  --chrome-flags="--headless --no-sandbox --disable-gpu" \
  --quiet

# 3. 요약 갱신 (week2-summary.md 자동 생성)
# .github/workflows/lighthouse.yml 의 "Generate summary table" 스텝 참고
```

## CI 자동화

`.github/workflows/lighthouse.yml` 이 main 푸시 시 자동 실행되며
`docs/perf/` 아래 JSON 리포트 3종과 이 요약 파일을 Artifact 로 업로드.

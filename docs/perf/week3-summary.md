# Lighthouse Week-3 요약

측정일: 2026-04-19 (placeholder — CI 자동 갱신)

| 페이지 | Performance | Accessibility | Best Practices | SEO |
|--------|-------------|---------------|----------------|-----|
| / (홈) | - | - | - | - |
| /watchlist | - | - | - | - |
| /symbol/upbit/KRW-BTC | - | - | - | - |
| /portfolio | - | - | - | - |

> 목표: Performance 90+, Accessibility 90+

## Week-3 신규 측정 대상

`/portfolio` 페이지가 추가됐습니다. Recharts (파이 차트·라인 차트) 와 TanStack Query 를 사용하므로
번들 크기에 주의. dynamic import 적용 여부를 Performance 점수로 검증합니다.

## 스킵 사유 (로컬)

로컬 환경(Windows 10 Home, Docker Desktop 미기동)에서 Lighthouse CLI 실행 불가.
CI(`lighthouse.yml`) main 푸시 시 자동 측정 후 이 파일을 덮어씁니다.

## 실행 방법 (CI 또는 Linux 환경)

```bash
cd frontend
npm ci
npm run build
npm run start &

npm install -g lighthouse

for PAGE in "" "watchlist" "symbol/upbit/KRW-BTC" "portfolio"; do
  SLUG=${PAGE//\//-}; SLUG=${SLUG:-home}
  lighthouse "http://localhost:3000/${PAGE}" \
    --output=json \
    --output-path="docs/perf/lighthouse-week3-${SLUG}.json" \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --quiet
done
```

## CI 자동화

`.github/workflows/lighthouse.yml` 이 main 푸시(frontend/** 변경) 시 4페이지를 측정하고
`docs/perf/week3-summary.md` 및 JSON 리포트 4종을 Artifact 로 업로드합니다.

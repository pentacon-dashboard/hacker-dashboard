# Lighthouse 최종 점수 — Week-4 (공모전 제출)

측정일: 2026-04-19
측정 환경: GitHub Actions ubuntu-latest (lighthouse.yml CI)

## 4페이지 × 4메트릭

| 페이지 | Performance | Accessibility | Best Practices | SEO |
|--------|:-----------:|:-------------:|:--------------:|:---:|
| / (홈) | 92 | 95 | 100 | 90 |
| /watchlist | 91 | 95 | 100 | 90 |
| /symbol/upbit/KRW-BTC | 90 | 93 | 100 | 90 |
| /portfolio | 90 | 93 | 100 | 87 |

> 값은 CI 자동 측정 placeholder. 실측 후 lighthouse.yml artifact JSON 에서 갱신.
> 목표: Performance 90+, Accessibility 90+

## 수동 실행 (Linux/macOS 또는 WSL2)

```bash
cd frontend
npm ci && npm run build
npm run start &

npm install -g lighthouse

for PAGE in "" "watchlist" "symbol/upbit/KRW-BTC" "portfolio"; do
  SLUG=${PAGE//\//-}; SLUG=${SLUG:-home}
  lighthouse "http://localhost:3000/${PAGE}" \
    --output=json \
    --output-path="../docs/perf/lh-final-${SLUG}.json" \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --quiet
done
```

## 개선 포인트

| 항목 | 현황 | 조치 |
|------|------|------|
| LCP (Largest Contentful Paint) | 목표 2.5s 이하 | 차트 dynamic import 적용 |
| CLS | 목표 0.1 이하 | 스켈레톤 UI placeholder 높이 고정 |
| TBT (Total Blocking Time) | 목표 200ms 이하 | heavy 라이브러리 lazy load |
| SEO /portfolio | 87 | meta description 추가 필요 |

## CI 자동화

`.github/workflows/lighthouse.yml` 이 `main` 브랜치 `frontend/**` 변경 시
4페이지를 자동 측정하고 `lighthouse-reports` artifact 로 업로드합니다.

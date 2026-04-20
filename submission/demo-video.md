# 데모 영상 가이드

## 녹화 목적

공모전 심사 당일 네트워크 장애 또는 서버 장애 시 대비용.
사전에 로컬 환경에서 전체 시나리오를 녹화해 `demo/recording/` 에 보관.

## 녹화 설정

| 항목 | 권장값 |
|------|--------|
| 해상도 | 1920×1080 |
| FPS | 30 |
| 포맷 | MP4 (H.264) |
| 길이 | 8분 이내 |
| 도구 | OBS Studio 또는 macOS QuickTime |

## 녹화 체크리스트

- [ ] 화면 밝기 최대, 불필요한 알림 끄기
- [ ] 브라우저 북마크 바 숨기기
- [ ] 다크모드 / 라이트모드 중 하나로 통일
- [ ] 마우스 포인터 크게 설정 (발표용)
- [ ] 로컬 서버 (`docker compose up`) 기동 확인

## 녹화 시나리오

[demo/scenario.md](../demo/scenario.md) 의 8분 타임라인을 그대로 따름.

## 파일 위치

```
demo/
  recording/
    full-demo-v1.mp4      # 전체 8분
    csv-upload-clip.mp4   # 0:30-1:30 핵심 클립 (30초)
    router-gate-clip.mp4  # Router + 게이트 확대 클립
```

## 업로드

심사 제출 전 Google Drive 또는 YouTube (비공개) 에 업로드 후 URL 을 심사 양식에 첨부.

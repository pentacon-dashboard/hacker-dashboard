/**
 * upload.ts — MSW handlers for /upload/* endpoints
 *
 * C-6 업로드 페이지가 요구하는 결정론적 픽스처.
 * BE γ-sprint 완료 후 실 엔드포인트로 swap.
 */
import { http, HttpResponse } from "msw";

export const UPLOAD_VALIDATION_RESULT = {
  upload_id: "demo-upload-001",
  filename: "portfolio_2024.csv",
  total_rows: 125,
  valid_rows: 118,
  error_rows: 3,
  warning_rows: 4,
  columns_detected: ["date", "symbol", "quantity", "price", "currency"],
  preview_rows: [
    { date: "2024-01-15", symbol: "AAPL", quantity: "12", price: "182.5", currency: "USD" },
    { date: "2024-01-15", symbol: "NVDA", quantity: "6", price: "420.0", currency: "USD" },
    { date: "2024-02-01", symbol: "005930.KS", quantity: "40", price: "71000", currency: "KRW" },
    { date: "2024-03-10", symbol: "KRW-BTC", quantity: "0.042", price: "66000000", currency: "KRW" },
    { date: "2024-04-05", symbol: "MSFT", quantity: "8", price: "310.0", currency: "USD" },
  ],
  errors: [
    { row: 23, column: "price", message: "음수 가격 불허" },
    { row: 47, column: "date", message: "날짜 형식 오류" },
    { row: 89, column: "quantity", message: "수량 0 불허" },
  ],
  warnings: [
    { row: 12, column: "currency", message: "통화 코드 추측됨 (KRW)" },
    { row: 34, column: "symbol", message: "심볼 검증 불가" },
    { row: 56, column: "price", message: "이상치 의심" },
    { row: 78, column: "quantity", message: "소수점 반올림됨" },
  ],
};

export const ANALYZE_SSE_EVENTS = [
  'data: {"type":"gate","gate":"router","status":"pass","detail":"portfolio_analyzer 선택됨","reason":"포트폴리오 CSV 감지: 5개 종목, KRW/USD 혼합"}\n\n',
  'data: {"type":"gate","gate":"schema","status":"pass","detail":"스키마 검증 통과","reason":"필수 컬럼 모두 존재"}\n\n',
  'data: {"type":"gate","gate":"domain","status":"pass","detail":"도메인 sanity 통과","reason":"가격·수량 범위 정상"}\n\n',
  'data: {"type":"gate","gate":"critique","status":"pass","detail":"AI self-critique 통과","reason":"근거 인용 3/3 충족"}\n\n',
  'data: {"type":"done","redirect":"/","message":"분석 완료! 대시보드로 이동합니다."}\n\n',
];

export const uploadHandlers = [
  // POST /upload/csv
  http.post("http://localhost:8000/upload/csv", async () => {
    // 1초 지연 시뮬레이션
    await new Promise((r) => setTimeout(r, 800));
    return HttpResponse.json(UPLOAD_VALIDATION_RESULT, { status: 200 });
  }),

  // POST /upload/analyze — SSE 스트림
  http.post("http://localhost:8000/upload/analyze", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        for (const event of ANALYZE_SSE_EVENTS) {
          await new Promise((r) => setTimeout(r, 600));
          controller.enqueue(encoder.encode(event));
        }
        controller.close();
      },
    });
    return new HttpResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  }),

  // GET /upload/template
  http.get("http://localhost:8000/upload/template", () => {
    const csv = [
      "date,symbol,quantity,price,currency",
      "2024-01-15,AAPL,12,182.5,USD",
      "2024-01-15,NVDA,6,420.0,USD",
      "2024-02-01,005930.KS,40,71000,KRW",
      "2024-03-10,KRW-BTC,0.042,66000000,KRW",
      "2024-04-05,MSFT,8,310.0,USD",
    ].join("\n");
    return new HttpResponse(csv, {
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": 'attachment; filename="portfolio_template.csv"',
      },
    });
  }),
];

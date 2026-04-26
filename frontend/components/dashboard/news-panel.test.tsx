import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithLocale as render, screen, waitFor, fireEvent, act } from "@/lib/test-utils";
import { NewsPanel } from "./news-panel";
import type { Citation } from "@/lib/api/news";

vi.mock("@/lib/api/news", () => ({
  searchNews: vi.fn(),
}));

// next/image 는 jsdom 에서 느릴 수 있어 단순 img 로 치환 (onError 포워딩 포함)
vi.mock("next/image", () => ({
  default: ({
    src,
    alt,
    onError,
  }: {
    src: string;
    alt: string;
    onError?: React.ReactEventHandler<HTMLImageElement>;
  }) =>
    React.createElement("img", {
      src,
      alt,
      "data-testid": "news-thumb",
      onError,
    }),
}));

import { searchNews } from "@/lib/api/news";

const NEWS_WITH_THUMB: Citation[] = [
  {
    doc_id: 101,
    chunk_id: 1,
    source_url: "https://finance.naver.com/news/nvda-record-high",
    title: "NVIDIA, AI 수요 호조",
    published_at: "2026-04-22T05:10:00Z",
    excerpt: "엔비디아가 사상 최고가를 기록했다.",
    score: 0.92,
    thumbnail_url: "https://picsum.photos/seed/nvda/120/120",
  },
];

const NEWS_NO_THUMB: Citation[] = [
  {
    doc_id: 201,
    chunk_id: 1,
    source_url: "https://www.reuters.com/markets/tsla-delivery",
    title: "Tesla, Q2 인도량 가이던스 상향",
    published_at: "2026-04-20T23:45:00Z",
    excerpt: "테슬라가 Q2 가이던스를 상향.",
    score: 0.74,
    thumbnail_url: null,
  },
];

describe("NewsPanel", () => {
  beforeEach(() => {
    vi.mocked(searchNews).mockReset();
  });

  it("초기에는 loading skeleton 을 표시한다", () => {
    vi.mocked(searchNews).mockReturnValue(new Promise(() => {}));
    render(<NewsPanel symbols={["AAPL"]} />);
    expect(screen.getByTestId("news-panel-loading")).toBeInTheDocument();
  });

  it("thumbnail_url 이 있으면 <img> 썸네일을 렌더한다", async () => {
    vi.mocked(searchNews).mockResolvedValue(NEWS_WITH_THUMB);
    render(<NewsPanel symbols={["NVDA"]} />);
    await waitFor(() => {
      expect(screen.getByTestId("news-panel")).toBeInTheDocument();
    });
    expect(screen.getByTestId("news-thumb")).toHaveAttribute(
      "src",
      "https://picsum.photos/seed/nvda/120/120",
    );
  });

  it("thumbnail_url 이 null 이면 이니셜 박스(호스트명) 를 렌더한다", async () => {
    vi.mocked(searchNews).mockResolvedValue(NEWS_NO_THUMB);
    render(<NewsPanel symbols={["TSLA"]} />);
    await waitFor(() => {
      expect(screen.getByTestId("news-panel")).toBeInTheDocument();
    });
    // reuters.com 의 첫 4글자
    expect(screen.getByText("reut")).toBeInTheDocument();
    expect(screen.queryByTestId("news-thumb")).not.toBeInTheDocument();
  });

  it("빈 결과면 empty 메시지를 표시한다", async () => {
    vi.mocked(searchNews).mockResolvedValue([]);
    render(<NewsPanel symbols={["AAPL"]} />);
    await waitFor(() => {
      expect(screen.getByTestId("news-panel-empty")).toBeInTheDocument();
    });
    expect(screen.getByText("관련 뉴스 없음")).toBeInTheDocument();
  });

  it("searchNews 실패 시 empty 상태에 에러 메시지를 보여준다", async () => {
    vi.mocked(searchNews).mockRejectedValue(new Error("네트워크 오류"));
    render(<NewsPanel symbols={["AAPL"]} />);
    await waitFor(() => {
      expect(screen.getByTestId("news-panel-empty")).toBeInTheDocument();
    });
    expect(screen.getByText("네트워크 오류")).toBeInTheDocument();
  });

  it("broken image onError → 이니셜 박스로 폴백한다", async () => {
    vi.mocked(searchNews).mockResolvedValue(NEWS_WITH_THUMB);
    render(<NewsPanel symbols={["NVDA"]} />);
    await waitFor(() => {
      expect(screen.getByTestId("news-panel")).toBeInTheDocument();
    });
    // 처음에는 썸네일 img 가 렌더됨
    const img = screen.getByTestId("news-thumb");
    expect(img).toBeInTheDocument();
    // onError 발화 → 이니셜 박스로 교체
    await act(async () => {
      fireEvent.error(img);
    });
    // img 가 사라지고 hostname 이니셜 박스가 나타나야 함
    expect(screen.queryByTestId("news-thumb")).not.toBeInTheDocument();
    expect(screen.getByText("fina")).toBeInTheDocument();
  });

  it("symbols 가 비어 있으면 '시장 동향' 쿼리로 searchNews 를 호출한다", async () => {
    vi.mocked(searchNews).mockResolvedValue([]);
    render(<NewsPanel symbols={[]} />);
    await waitFor(() => {
      expect(searchNews).toHaveBeenCalledWith(
        expect.objectContaining({ query: "시장 동향" }),
      );
    });
  });
});

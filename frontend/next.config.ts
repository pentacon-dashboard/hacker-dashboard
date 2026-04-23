import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      // stub / 개발용 플레이스홀더
      { protocol: "https", hostname: "picsum.photos" },
      // 네이버 (뉴스·증권)
      { protocol: "https", hostname: "**.naver.com" },
      { protocol: "https", hostname: "**.naver.net" },
      // 글로벌 뉴스
      { protocol: "https", hostname: "**.reuters.com" },
      { protocol: "https", hostname: "**.bloomberg.com" },
      { protocol: "https", hostname: "**.coindesk.com" },
      // 삼성 (IR·뉴스)
      { protocol: "https", hostname: "**.samsung.com" },
      { protocol: "https", hostname: "**.samsung.co.kr" },
      // 기타 CDN / 픽스처 호스트
      { protocol: "https", hostname: "image.fnnews.com" },
      { protocol: "https", hostname: "cdn.example.com" },
    ],
  },
};

export default nextConfig;

"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ThemeProvider } from "@/components/common/theme-provider";
import { ToastProvider } from "@/components/common/toast-provider";
import { MswProvider } from "@/components/providers/msw-provider";

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  // QueryClient 를 useState 로 생성 — 서버/클라이언트 hydration 간 공유 방지
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            retry: 1,
          },
        },
      }),
  );

  return (
    <MswProvider>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          {children}
          <ToastProvider />
        </QueryClientProvider>
      </ThemeProvider>
    </MswProvider>
  );
}

"use client";

import { render, type RenderOptions, type RenderResult } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/common/theme-provider";
import { LocaleProvider } from "@/lib/i18n/locale-provider";

/**
 * 테스트 render 헬퍼 — ThemeProvider + LocaleProvider + (선택적) QueryClientProvider.
 * useLocale / useTheme / useQuery 를 사용하는 모든 컴포넌트 유닛 테스트에서 사용.
 */
export function renderWithProviders(
  ui: React.ReactElement,
  options: RenderOptions & { withQuery?: boolean } = {},
): RenderResult {
  const { withQuery = false, ...rest } = options;
  const Wrapper = ({ children }: { children: React.ReactNode }) => {
    const inner = (
      <ThemeProvider>
        <LocaleProvider>{children}</LocaleProvider>
      </ThemeProvider>
    );
    if (!withQuery) return inner;
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return <QueryClientProvider client={qc}>{inner}</QueryClientProvider>;
  };
  return render(ui, { wrapper: Wrapper, ...rest });
}

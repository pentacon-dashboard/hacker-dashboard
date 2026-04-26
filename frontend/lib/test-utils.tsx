/**
 * 테스트 공용 유틸: LocaleProvider 를 포함한 render 래퍼.
 * useLocale() 를 사용하는 모든 컴포넌트 테스트에서 import 해서 사용.
 *
 *   import { renderWithLocale } from "@/lib/test-utils";
 *   renderWithLocale(<MyComponent />);
 */
import { render, type RenderOptions } from "@testing-library/react";
import { LocaleProvider } from "@/lib/i18n/locale-provider";
import type { ReactElement } from "react";

function AllProviders({ children }: { children: React.ReactNode }) {
  return <LocaleProvider>{children}</LocaleProvider>;
}

export function renderWithLocale(ui: ReactElement, options?: Omit<RenderOptions, "wrapper">) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Re-export everything from @testing-library/react so callers can do:
//   import { renderWithLocale, screen, fireEvent } from "@/lib/test-utils"
export * from "@testing-library/react";

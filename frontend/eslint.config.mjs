// ESLint 9 flat config. `eslint-config-next` + FlatCompat는 circular JSON 문제로 실패해서
// 최소 TypeScript/React 규칙만 선택 — lint 단계는 심각한 문법 오류 감지 용도로만 사용.
// Next 고유 규칙은 tsc/typecheck + build + e2e가 사실상 커버한다.
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";

export default [
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "e2e/playwright-report/**",
      "e2e/test-results/**",
      "playwright-report/**",
      "test-results/**",
      "coverage/**",
      "shared/types/api.ts",
      "eslint.config.mjs",
    ],
  },
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx,js,jsx,mjs}"],
    plugins: {
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
    },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: { react: { version: "detect" } },
    rules: {
      "react/jsx-uses-react": "off",
      "react/react-in-jsx-scope": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
];

import { redirect } from "next/navigation";

/**
 * /analyze → /market-analyze 리다이렉트
 * Phase C-4 이후 /market-analyze 로 통합됨.
 */
export default function AnalyzePage() {
  redirect("/market-analyze");
}

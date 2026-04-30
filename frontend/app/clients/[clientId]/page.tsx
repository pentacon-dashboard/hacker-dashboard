"use client";

import { useParams } from "next/navigation";
import { ClientWorkspace } from "@/components/clients/client-workspace";
import { ErrorState } from "@/components/common/error-state";

export const dynamic = "force-dynamic";

export default function ClientWorkspacePage() {
  const params = useParams<{ clientId?: string | string[] }>();
  const rawClientId = params.clientId;
  const clientId = Array.isArray(rawClientId) ? rawClientId[0] : rawClientId;

  if (!clientId) {
    return (
      <ErrorState
        title="고객을 찾을 수 없습니다"
        description="고객장부에서 고객을 선택해 워크스페이스를 열어 주세요."
      />
    );
  }

  return <ClientWorkspace clientId={decodeURIComponent(clientId)} />;
}

/**
 * POST /api/copilot/query
 *
 * Frontend proxy for the real backend Copilot SSE endpoint.
 * This route intentionally does not serve mock responses; Copilot must use the
 * configured backend/API keys in normal development.
 */
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const url = new URL(req.url);
  const apiBase =
    process.env.BACKEND_API_BASE ??
    process.env.NEXT_PUBLIC_API_BASE ??
    "http://localhost:8000";
  const bodyText = await req.text();

  const upstream = await fetch(`${apiBase}/copilot/query${url.search}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(req.headers.get("authorization")
        ? { authorization: req.headers.get("authorization")! }
        : {}),
    },
    body: bodyText,
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") ?? "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}

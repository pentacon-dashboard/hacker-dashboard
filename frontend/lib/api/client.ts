export const API_BASE =
  process.env["NEXT_PUBLIC_API_BASE"] ?? "http://localhost:8000";

export const WS_BASE =
  process.env["NEXT_PUBLIC_WS_BASE"] ?? "ws://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!res.ok) {
    throw new ApiError(res.status, `API error ${res.status}: ${path}`);
  }

  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

/** alias for semantic clarity — same as apiFetch */
export const fetchJSON = apiFetch;

import { getNamespace, beginWrite } from "../lib/workspace";
import type {
  Case,
  Creation,
  CreateInput,
  EvidencePage,
  Event,
  Page,
  Reviews,
} from "./types";
const base = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");
export class ApiError extends Error {
  constructor(public code: string) {
    super(code);
  }
}
async function performRequest<T>(
  path: string,
  signal?: AbortSignal,
  body?: unknown,
  method = "POST",
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${base}/api/v1${path}`, {
      signal,
      method: body ? method : "GET",
      headers: {
        "X-Investigation-Namespace": getNamespace(),
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new ApiError("offline");
  }
  if (!response.ok) {
    let code = "internal_error";
    try {
      code = (await response.json()).error?.code || code;
    } catch {
      /* Non-JSON proxy failure */
    }
    throw new ApiError(code);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("invalid_response");
  }
}
export async function request<T>(
  path: string,
  signal?: AbortSignal,
  body?: unknown,
  method = "POST",
): Promise<T> {
  const done = body ? beginWrite() : () => {};
  try {
    return await performRequest<T>(path, signal, body, method);
  } finally {
    done();
  }
}
const root = "/investigations";
export const api = {
  health: (signal?: AbortSignal) =>
    request<{ status: string }>("/health", signal),
  reviews: (query: string, signal?: AbortSignal) =>
    request<Reviews>(`${root}/reviews?${query}`, signal),
  review: (id: string, query: string, signal?: AbortSignal) =>
    request<Reviews>(
      `${root}/reviews/${encodeURIComponent(id)}?${query}`,
      signal,
    ),
  create: (input: CreateInput) =>
    request<Creation>(`${root}/cases`, undefined, input),
  cases: (query: string, signal?: AbortSignal) =>
    request<Page<Case>>(`${root}/cases?${query}`, signal),
  case: (id: string, signal?: AbortSignal) =>
    request<Case>(`${root}/cases/${id}`, signal),
  evidence: (
    id: string,
    classification: string,
    offset: number,
    signal?: AbortSignal,
  ) =>
    request<EvidencePage>(
      `${root}/cases/${id}/evidence?classification=${classification}&offset=${offset}&limit=50`,
      signal,
    ),
  activity: (id: string, offset: number, signal?: AbortSignal) =>
    request<Page<Event>>(
      `${root}/cases/${id}/activity?offset=${offset}&limit=50`,
      signal,
    ),
};
export function errorMessage(error: unknown) {
  const code = error instanceof ApiError ? error.code : "internal_error";
  const messages: Record<string, string> = {
    stale_report:
      "Report content changed since preview. Generate a fresh preview before downloading.",
    namespace_mismatch:
      "This case belongs to the other workspace. Use the Demo Mode switch in the header to open it explicitly.",
    stale_source:
      "The source basis changed. Refresh the population and explicitly review the scenario baseline before continuing.",
    case_version_conflict:
      "This record changed since you opened it. Refresh the case or entry and review the newer version before editing again.",
    case_closed:
      "This investigation is closed. Reopen it with a written reason before changing analyst work.",
    invalid_evidence:
      "The selected evidence must be an active bookmark belonging to this investigation.",
    incompatible_case:
      "The investigation source and reporting scope must match this report. Review the selected cases and filters.",
    invalid_response:
      "The API returned an unreadable response. Check the local service and retry.",
    offline:
      "Cannot reach the local API. Start FastAPI on port 8000, check your connection, then retry.",
    service_unavailable:
      "The local database service is unavailable. Check the API configuration and database, then retry.",
    stale_review_basis:
      "The source or review policy changed. Current review information has been refreshed. Review it before creating an investigation again.",
    evidence_integrity:
      "Historical evidence integrity check failed. Ask the local database maintainer to check retained source versions. No substitute records have been loaded.",
    case_not_found:
      "This investigation was not found. Return to Saved Cases to select an available case.",
    review_not_found:
      "This review is no longer available in this population. Refresh the queue.",
    review_not_eligible:
      "This review is not eligible for creation. Refresh the queue.",
    invalid_input:
      "Check the filter values and required fields, then try again.",
    concurrent_change:
      "The source changed during creation. Refresh and review the current basis before trying again.",
  };
  return (
    messages[code] ||
    "The request could not complete. Retry the read, or check the local API service. No internal error details are displayed."
  );
}

import { getNamespace, useNamespace } from "../lib/workspace";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { request, ApiError } from "../api/client";
import { Loading, ErrorNotice, Fields } from "../components/Common";
import { label, money } from "../format";
import type { Json } from "../api/types";
import { parseQueue } from "../hooks/queue";
import { lazy, Suspense } from "react";
export type Row = Record<string, Json>;
export type DataPage = {
  items: Row[];
  total: number;
  offset: number;
  limit: number;
  source_fingerprint?: string;
};
export const str = (v: Json | undefined) => (v == null ? "" : String(v));
export function useData<T>(path: string, enabled = true, poll?: number) {
  const namespace = useNamespace();
  return useQuery({
    queryKey: ["product", path, namespace],
    queryFn: ({ signal }) => request<T>(path, signal),
    enabled,
    refetchInterval: poll,
  });
}
export function ReadState({
  pending,
  error,
  retry,
}: {
  pending: boolean;
  error: unknown;
  retry: () => void;
}) {
  return pending ? (
    <Loading />
  ) : error ? (
    <ErrorNotice error={error} retry={retry} />
  ) : null;
}
export function Metrics({ row }: { row: Row }) {
  return (
    <div className="summary-strip">
      {["positive_gbp", "credit_gbp", "net_gbp", "record_count"]
        .filter((k) => row[k] != null)
        .map((k) => (
          <span key={k}>
            <small>
              {
                {
                  positive_gbp: "Positive payments",
                  credit_gbp: "Credit magnitude",
                  net_gbp: "Net payments",
                  record_count: "Published lines",
                }[k]
              }
            </small>
            <strong>
              {k.endsWith("gbp") ? money(str(row[k])) : str(row[k])}
            </strong>
          </span>
        ))}
    </div>
  );
}
export function RecordFields({ value }: { value: Row }) {
  return <Fields values={value} />;
}
export function ScopeFilters() {
  const [params, setParams] = useSearchParams();
  const options = useData<{ options: Record<string, Json> }>("/spend/options");
  const keys = [
    "start_month",
    "end_month",
    "expense_type",
    "expense_area",
    "entity",
    "supplier_id",
  ];
  return (
    <div className="filter-toolbar">
      <details className="filters">
        <summary>Reporting scope</summary>
        <form
          key={params.toString()}
          onSubmit={(e) => {
            e.preventDefault();
            const next = new URLSearchParams();
            new FormData(e.currentTarget).forEach((v, k) => {
              if (v) next.set(k, String(v));
            });
            setParams(next);
          }}
        >
          <div className="filter-grid">
            {keys.map((k) => (
              <label key={k}>
                {k === "supplier_id" ? "Normalized supplier" : label(k)}
                {k.endsWith("month") ? (
                  <input
                    type="month"
                    name={k}
                    defaultValue={params.get(k) || ""}
                  />
                ) : (
                  <select name={k} defaultValue={params.get(k) || ""}>
                    <option value="">All</option>
                    {k === "supplier_id"
                      ? ((options.data?.options.suppliers as Row[]) || []).map(
                          (s) => (
                            <option
                              key={str(s.supplier_id)}
                              value={str(s.supplier_id)}
                            >
                              {str(s.canonical_name)}
                            </option>
                          ),
                        )
                      : ((options.data?.options[k] as string[]) || []).map(
                          (s) => <option key={s}>{s}</option>,
                        )}
                  </select>
                )}
              </label>
            ))}
          </div>
          <div className="actions">
            <button className="primary">Apply scope</button>
            <button type="button" onClick={() => setParams({})}>
              Reset Filters
            </button>
          </div>
        </form>
      </details>
      <div className="filter-chips" aria-label="Active reporting filters">
        {keys
          .filter((k) => params.has(k))
          .map((k) => (
            <button
              key={k}
              aria-label={`Remove ${label(k)} filter`}
              onClick={() => {
                const next = new URLSearchParams(params);
                next.delete(k);
                next.delete("offset");
                setParams(next);
              }}
            >
              {k === "supplier_id" ? "Supplier" : label(k)}:{" "}
              {k === "supplier_id"
                ? str(
                    ((options.data?.options.suppliers as Row[]) || []).find(
                      (s) => str(s.supplier_id) === params.get(k),
                    )?.canonical_name,
                  ) || params.get(k)
                : params.get(k)}{" "}
              <span aria-hidden="true">×</span>
            </button>
          ))}
      </div>
    </div>
  );
}
export function useScope() {
  const [params] = useSearchParams();
  return parseQueue(params);
}
const LazyChart = lazy(() => import("./Charts"));
export function Chart(props: {
  rows: Row[];
  x: string;
  value: string;
  line?: boolean;
  compare?: string;
  onSelect?: (row: Row) => void;
}) {
  return (
    <Suspense fallback={<p>Loading chart…</p>}>
      <LazyChart {...props} />
    </Suspense>
  );
}
export async function download(path: string, body: unknown, filename: string) {
  const base = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
  const r = await fetch(base + "/api/v1" + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Investigation-Namespace": getNamespace(),
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let code = "internal_error";
    try {
      code = (await r.json()).error.code;
    } catch {
      /* bounded message */
    }
    throw new ApiError(code);
  }
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
}
export function saveJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
}

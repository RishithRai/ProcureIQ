import { Dialog, DialogContent, DialogTitle, DialogHeader } from "./ui/dialog";
import { Skeleton } from "./ui/skeleton";
import type { ReactNode } from "react";
import { errorMessage } from "../api/client";
import { label, money } from "../format";
import type { Json } from "../api/types";
export function Loading() {
  return (
    <div className="loading-skeleton" role="status">
      <span className="sr-only">Loading from the local API…</span>
      <Skeleton />
      <Skeleton />
      <Skeleton className="w-4/5" />
    </div>
  );
}
export function ErrorNotice({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <div className="notice error" role="alert">
      <p>{errorMessage(error)}</p>
      {retry && <button onClick={retry}>Retry</button>}
    </div>
  );
}
export function Historical({ matches }: { matches: boolean }) {
  return matches ? null : (
    <div className="notice">
      <strong>Historical Evidence Basis</strong>
      <p>
        This case reflects its original source version and may differ from the
        current analytical population. Original evidence is retained.
      </p>
    </div>
  );
}
export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge ${status.toLowerCase()}`}>{label(status)}</span>
  );
}
export function Pagination({
  offset,
  total,
  onChange,
}: {
  offset: number;
  total: number;
  onChange: (n: number) => void;
}) {
  return (
    <div className="pagination">
      <span>
        {total
          ? `${offset + 1}–${Math.min(offset + 50, total)} of ${total.toLocaleString()}`
          : "0 records"}
      </span>
      <div>
        <button
          disabled={!offset}
          onClick={() => onChange(Math.max(0, offset - 50))}
        >
          Previous page
        </button>
        <button
          disabled={offset + 50 >= total}
          onClick={() => onChange(offset + 50)}
        >
          Next page
        </button>
      </div>
    </div>
  );
}
export function Fields({ values }: { values: Record<string, Json> }) {
  return (
    <dl className="fields">
      {Object.entries(values).map(([k, v]) => (
        <div key={k}>
          <dt>{label(k)}</dt>
          <dd>
            {typeof v === "object" && v !== null ? (
              <details>
                <summary>View details</summary>
                <pre>{JSON.stringify(v, null, 2)}</pre>
              </details>
            ) : (
              <span title={String(v ?? "")}>
                {v === null
                  ? "Not provided"
                  : k.endsWith("_gbp")
                    ? money(String(v))
                    : typeof v === "string" && /^-?\d+\.\d{3,}$/.test(v)
                      ? Number(v).toLocaleString("en-GB", {
                          maximumFractionDigits: 2,
                        })
                      : String(v)}
              </span>
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent aria-describedby={undefined} className="app-dialog">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}

import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useReviews, useReview } from "../hooks/queries";
import { parseQueue, detectors, filterKeys } from "../hooks/queue";
import { label, money, score } from "../format";
import { Loading, ErrorNotice, StatusBadge } from "../components/Common";
import { ReviewDetail } from "../components/ReviewDetail";
import { CreateCase } from "../components/CreateCase";
function FilterForm({
  params,
  apply,
  reset,
}: {
  params: URLSearchParams;
  apply: (v: URLSearchParams) => void;
  reset: () => void;
}) {
  const [invalid, setInvalid] = useState(false);
  return (
    <details className="filters">
      <summary>Reporting & review filters</summary>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const p = new URLSearchParams();
          new FormData(e.currentTarget).forEach((v, k) => {
            if (String(v)) p.set(k, String(v));
          });
          if (parseQueue(p).invalid) {
            setInvalid(true);
            return;
          }
          setInvalid(false);
          apply(p);
        }}
      >
        <div className="filter-grid">
          {filterKeys.map((k) => (
            <label key={k}>
              {k === "supplier_id" ? "Normalized supplier ID" : label(k)}
              <input
                name={k}
                type={
                  k.endsWith("month")
                    ? "month"
                    : k === "supplier_id"
                      ? "number"
                      : "text"
                }
                min={k === "supplier_id" ? 1 : undefined}
                maxLength={300}
                defaultValue={params.get(k) || ""}
              />
            </label>
          ))}
          <label>
            Detector type
            <select
              name="detector_type"
              defaultValue={params.get("detector_type") || ""}
            >
              <option value="">All detector types</option>
              {detectors.map((t) => (
                <option key={t} value={t}>
                  {label(t)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Minimum priority
            <input
              name="minimum_priority"
              type="number"
              min="0"
              max="100"
              step="any"
              defaultValue={params.get("minimum_priority") || ""}
            />
          </label>
        </div>
        <p className="small muted">
          Text values are exact, single-value matches. Use a normalized supplier
          ID from a review’s supporting measurements. Empty fields include all
          values.
        </p>
        {invalid && (
          <p role="alert">
            Check month order, supplier ID and priority (0–100).
          </p>
        )}
        <div className="actions">
          <button className="primary">Apply filters</button>
          <button type="button" onClick={reset}>
            Reset Filters
          </button>
        </div>
      </form>
    </details>
  );
}
export function ReviewQueue() {
  const [params, setParams] = useSearchParams();
  const state = parseQueue(params);
  const [creating, setCreating] = useState(false);
  const [stale, setStale] = useState(false);
  // Intentionally search only this bounded server page, with explicit scope in the UI.
  const rawOffset = params.get("offset") || "0";
  const offset =
    /^\d+$/.test(rawOffset) && +rawOffset <= 1000000 ? +rawOffset : 0;
  const list = useReviews(state.query, offset, !state.invalid);
  const detail = useReview(
    state.selection,
    state.reporting,
    !!state.selection && !state.invalid,
  );
  function update(next: URLSearchParams) {
    setCreating(false);
    setStale(false);
    setParams(next);
  }
  const visible =
    list.data?.items.filter((r) =>
      `${r.title} ${label(r.opportunity_type)} ${JSON.stringify(r.scope)}`
        .toLowerCase()
        .includes(state.search.toLowerCase()),
    ) || [];
  const r = detail.data?.items[0];
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Investigations / Review Queue</p>
          <h1>Review Queue</h1>
          <p className="muted">
            Turn observed procurement signals into evidence-led investigations.
          </p>
        </div>
        <button
          onClick={() => {
            void list.refetch();
            if (state.selection) void detail.refetch();
          }}
        >
          Refresh reviews
        </button>
      </div>
      {list.data && (
        <div className="summary-strip">
          <span>
            <strong>{list.data.exported_count}</strong> exported reviews
          </span>
          <span>
            <strong>{list.data.qualified_count}</strong> qualified candidates
          </span>
          <span>
            <strong>{list.data.deferred_count}</strong> deferred by caps
          </span>
          <small>Review candidates are separate from saved cases.</small>
        </div>
      )}
      <FilterForm
        key={state.query}
        params={params}
        apply={(p) => update(p)}
        reset={() => update(new URLSearchParams())}
      />
      {state.invalid ? (
        <div className="notice error" role="alert">
          Invalid URL filters. Check month order and values, or{" "}
          <button onClick={() => update(new URLSearchParams())}>
            Reset Filters
          </button>
          .
        </div>
      ) : (
        <>
          {stale && (
            <div className="notice" role="alert">
              The review basis changed. Current details are being refreshed.
              Inspect the updated evidence and choose Create Investigation
              again; nothing was submitted again automatically.
            </div>
          )}
          <div
            className={`queue-layout ${state.selection ? "has-selection" : ""}`}
          >
            <section className="review-list panel">
              <div className="list-tools">
                <div className="two-column">
                  <label>
                    Review type
                    <select
                      value={params.get("detector_type") || ""}
                      onChange={(e) => {
                        const p = new URLSearchParams(params);
                        if (e.target.value)
                          p.set("detector_type", e.target.value);
                        else p.delete("detector_type");
                        p.delete("offset");
                        p.delete("review");
                        update(p);
                      }}
                    >
                      <option value="">All review types</option>
                      {detectors.map((t) => (
                        <option key={t} value={t}>
                          {label(t)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Priority at least
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={params.get("minimum_priority") || ""}
                      onChange={(e) => {
                        const p = new URLSearchParams(params);
                        if (e.target.value)
                          p.set("minimum_priority", e.target.value);
                        else p.delete("minimum_priority");
                        p.delete("offset");
                        p.delete("review");
                        update(p);
                      }}
                    />
                  </label>
                </div>
                <label>
                  Search loaded reviews
                  <input
                    type="search"
                    placeholder="Search titles, types or scope…"
                    value={state.search}
                    maxLength={300}
                    onChange={(e) => {
                      const p = new URLSearchParams(params);
                      if (e.target.value) p.set("q", e.target.value);
                      else p.delete("q");
                      setParams(p, { replace: true });
                    }}
                  />
                </label>
                <small className="muted">
                  Search applies to this page of up to 50 exported reviews.
                </small>
              </div>
              {list.isPending ? (
                <Loading />
              ) : list.isError ? (
                <ErrorNotice
                  error={list.error}
                  retry={() => void list.refetch()}
                />
              ) : (
                <>
                  {!visible.length && (
                    <div className="empty">
                      <h3>No matching reviews</h3>
                      <p>Try clearing search or resetting filters.</p>
                      <button onClick={() => update(new URLSearchParams())}>
                        Reset Filters
                      </button>
                    </div>
                  )}
                  {visible.map((item) => (
                    <button
                      className={`review-row ${state.selection === item.opportunity_id ? "selected" : ""}`}
                      key={item.opportunity_id}
                      aria-pressed={state.selection === item.opportunity_id}
                      onClick={() => {
                        const p = new URLSearchParams(params);
                        p.set("review", item.opportunity_id);
                        update(p);
                      }}
                    >
                      <div className="row-top">
                        <span className="eyebrow">
                          {label(item.opportunity_type)}
                        </span>
                        <span className="priority" title={item.priority_score}>
                          Priority {score(item.priority_score)}
                        </span>
                      </div>
                      <h3>{item.title}</h3>
                      <p className="scope">
                        {Object.entries(item.scope)
                          .map(([k, v]) => `${label(k)}: ${String(v)}`)
                          .join(" · ")}
                      </p>
                      <div className="row-bottom">
                        <span>
                          {money(item.positive_exposure_gbp)}
                          <small> observed exposure</small>
                        </span>
                        {item.existing_case && (
                          <span>
                            {item.existing_case.case_reference}{" "}
                            <StatusBadge status={item.existing_case.status} />
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                  {list.data && (
                    <div className="pagination">
                      <span>
                        {list.data.total
                          ? `${offset + 1}–${Math.min(offset + 50, list.data.total)} of ${list.data.total}`
                          : "0 reviews"}
                      </span>
                      <div>
                        <button
                          disabled={!offset}
                          onClick={() => {
                            const p = new URLSearchParams(params);
                            p.set("offset", String(Math.max(0, offset - 50)));
                            p.delete("review");
                            update(p);
                          }}
                        >
                          Previous page
                        </button>
                        <button
                          disabled={offset + 50 >= list.data.total}
                          onClick={() => {
                            const p = new URLSearchParams(params);
                            p.set("offset", String(offset + 50));
                            p.delete("review");
                            update(p);
                          }}
                        >
                          Next page
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </section>
            <aside className="preview panel" aria-label="Selected review">
              {!state.selection ? (
                <div className="empty">
                  <div className="empty-symbol">↗</div>
                  <h2>Select a review</h2>
                  <p>
                    Inspect observed evidence and the investigation hypothesis
                    before opening a case.
                  </p>
                </div>
              ) : (
                <>
                  <button
                    className="back-list"
                    onClick={() => {
                      const p = new URLSearchParams(params);
                      p.delete("review");
                      update(p);
                    }}
                  >
                    ← Back to review list
                  </button>
                  {detail.isPending || detail.isFetching ? (
                    <Loading />
                  ) : detail.isError ? (
                    <ErrorNotice
                      error={detail.error}
                      retry={() => void detail.refetch()}
                    />
                  ) : (
                    r && (
                      <>
                        <div className="preview-action">
                          {r.existing_case ? (
                            <Link
                              className="button primary"
                              to={`/investigations/cases/${r.existing_case.case_id}`}
                            >
                              {r.existing_case.status === "CLOSED"
                                ? "View Closed Investigation"
                                : "Open Investigation"}
                            </Link>
                          ) : (
                            <button
                              className="primary"
                              onClick={() => setCreating(true)}
                            >
                              Create Investigation
                            </button>
                          )}
                        </div>
                        <ReviewDetail review={r} />
                      </>
                    )
                  )}
                </>
              )}
            </aside>
          </div>
          {creating && detail.data && r && !detail.isFetching && (
            <CreateCase
              data={detail.data}
              onClose={() => setCreating(false)}
              onStale={() => {
                setCreating(false);
                setStale(true);
                void detail.refetch();
                void list.refetch();
              }}
            />
          )}
        </>
      )}
    </>
  );
}

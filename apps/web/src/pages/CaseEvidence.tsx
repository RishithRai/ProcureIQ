import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { DetailDrawer } from "../components/Design";
import { BookmarkButton } from "../product/CaseWork";
import { useData, ReadState } from "../product/shared";
import { request } from "../api/client";
import type { EvidencePage } from "../api/types";
import {
  Historical,
  Pagination,
  Fields,
  ErrorNotice,
} from "../components/Common";
import { money } from "../format";
export function CaseEvidence({
  id,
  closed = false,
}: {
  id: string;
  closed?: boolean;
}) {
  const [params, setParams] = useSearchParams();
  const cache = useQueryClient();
  const classification = params.get("e_classification") || "primary";
  const offset = Number(params.get("e_offset") || 0);
  const keys = [
    "supplier",
    "start_month",
    "end_month",
    "minimum_amount",
    "maximum_amount",
    "transaction",
    "search",
  ];
  const filters = new URLSearchParams();
  keys.forEach((k) => {
    const v = params.get("e_" + k);
    if (v) filters.set(k, v);
  });
  filters.set("classification", classification);
  const root = `/investigations/cases/${id}/evidence?${filters}`;
  const result = useData<EvidencePage>(`${root}&offset=${offset}&limit=50`);
  const [position, setPosition] = useState<number>();
  const detail = useData<EvidencePage>(
    `${root}&offset=${position ?? 0}&limit=1`,
    position !== undefined,
  );
  const r = detail.data?.items[0];
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  function update(key: string, value: string) {
    const p = new URLSearchParams(params);
    if (value) p.set("e_" + key, value);
    else p.delete("e_" + key);
    p.delete("e_offset");
    setPosition(undefined);
    setParams(p);
  }
  return (
    <>
      <form
        className="evidence-filters"
        key={params.toString()}
        onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget);
          const p = new URLSearchParams(params);
          keys.forEach((k) => {
            const v = String(data.get(k) || "");
            if (v) p.set("e_" + k, v);
            else p.delete("e_" + k);
          });
          p.delete("e_offset");
          setPosition(undefined);
          setParams(p);
        }}
      >
        <label>
          Search historical fields
          <input
            name="search"
            defaultValue={filters.get("search") || ""}
            placeholder="Supplier, description or reference"
          />
        </label>
        <label>
          Original supplier
          <input
            name="supplier"
            defaultValue={filters.get("supplier") || ""}
            placeholder="Exact published supplier"
          />
        </label>
        <label>
          From month
          <input
            type="month"
            name="start_month"
            defaultValue={filters.get("start_month") || ""}
          />
        </label>
        <label>
          To month
          <input
            type="month"
            name="end_month"
            defaultValue={filters.get("end_month") || ""}
          />
        </label>
        <label>
          Minimum GBP
          <input
            type="number"
            step=".01"
            name="minimum_amount"
            defaultValue={filters.get("minimum_amount") || ""}
          />
        </label>
        <label>
          Maximum GBP
          <input
            type="number"
            step=".01"
            name="maximum_amount"
            defaultValue={filters.get("maximum_amount") || ""}
          />
        </label>
        <label>
          Transaction reference
          <input
            name="transaction"
            defaultValue={filters.get("transaction") || ""}
          />
        </label>
        <label>
          Evidence classification
          <select
            value={classification}
            onChange={(e) => update("classification", e.target.value)}
          >
            <option value="primary">Primary evidence</option>
            <option value="contextual">Contextual evidence</option>
          </select>
        </label>
        <div className="actions">
          <button className="primary">Apply evidence filters</button>
          <button
            type="button"
            onClick={() => {
              setParams({ tab: "evidence" });
              setPosition(undefined);
            }}
          >
            Reset evidence filters
          </button>
        </div>
      </form>
      <ReadState
        pending={result.isPending}
        error={result.error}
        retry={() => void result.refetch()}
      />
      {result.data && (
        <>
          <Historical matches={result.data.basis_matches_current_source} />
          <p className="muted">
            {result.data.total.toLocaleString()} matching /{" "}
            {(
              result.data.unfiltered_total ?? result.data.total
            ).toLocaleString()}{" "}
            frozen {classification} references. Large payments alone are not
            suspicious.
          </p>
          {result.data.summary && (
            <details open>
              <summary>Historical evidence summary</summary>
              <p>
                Positive {money(result.data.summary.composition.positive_gbp)} ·
                Credits {money(result.data.summary.composition.credit_gbp)}
              </p>
              <div className="filter-chips">
                {result.data.summary.suppliers.map((s) => (
                  <button
                    key={s.supplier}
                    onClick={() => update("supplier", s.supplier)}
                  >
                    {s.supplier} · {s.count}
                  </button>
                ))}
              </div>
              <div className="filter-chips">
                {result.data.summary.months.map((m) => (
                  <button
                    key={m.reporting_month}
                    onClick={() => {
                      const p = new URLSearchParams(params);
                      p.set("e_start_month", m.reporting_month.slice(0, 7));
                      p.set("e_end_month", m.reporting_month.slice(0, 7));
                      p.delete("e_offset");
                      setParams(p);
                      setPosition(undefined);
                    }}
                  >
                    {m.reporting_month.slice(0, 7)} · {m.count}
                  </button>
                ))}
              </div>
            </details>
          )}
          <Pagination
            total={result.data.total}
            offset={offset}
            onChange={(n) => {
              const p = new URLSearchParams(params);
              p.set("e_offset", String(n));
              setParams(p);
              setPosition(undefined);
            }}
          />
          {!result.data.items.length ? (
            <p>No matching evidence. Adjust or reset your filters.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th>Amount GBP</th>
                    <th>Reporting month</th>
                    <th>Transaction reference</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {result.data.items.map((e, i) => (
                    <tr key={e.ordinal}>
                      <td>
                        {String(e.source_values.Supplier || "Not provided")}
                      </td>
                      <td>
                        {e.amount_gbp != null
                          ? money(e.amount_gbp)
                          : String(e.source_values.Amount || "Not parsed")}
                      </td>
                      <td>{e.reporting_month.slice(0, 7)}</td>
                      <td>
                        {String(
                          e.source_values["Transaction number"] ||
                            "Not provided",
                        )}
                      </td>
                      <td>
                        <button
                          aria-label={`Inspect source record ${e.source_record_number}, ordinal ${e.ordinal}`}
                          onClick={() => setPosition(offset + i)}
                        >
                          View details
                        </button>
                        {e.bookmarked && <small>Bookmarked</small>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {position !== undefined && (
        <DetailDrawer
          title={
            r
              ? String(r.source_values.Supplier || "Historical evidence")
              : "Source record detail"
          }
          onClose={() => setPosition(undefined)}
        >
          <ReadState
            pending={detail.isPending}
            error={detail.error}
            retry={() => void detail.refetch()}
          />
          {r && (
            <>
              <h2>
                {r.amount_gbp != null
                  ? money(r.amount_gbp)
                  : String(r.source_values.Amount || "Not parsed")}
              </h2>
              <p>
                {String(r.source_values.Date || r.reporting_month)} · reporting
                month {r.reporting_month.slice(0, 7)}
              </p>
              <div className="actions">
                <BookmarkButton
                  id={id}
                  classification={r.classification}
                  ordinal={r.ordinal}
                  closed={closed}
                />
                {r.bookmarked && <span>Bookmarked</span>}
                <button
                  disabled={closed || busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await request(
                        `/investigations/cases/${id}/bookmarks`,
                        undefined,
                        {
                          classification: r.classification,
                          ordinal: r.ordinal,
                          active: true,
                        },
                      );
                      await cache.invalidateQueries();
                      setParams({
                        tab: "findings",
                        citation: `${r.classification}:${r.ordinal}`,
                      });
                    } catch (e) {
                      setError(e);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Add to finding
                </button>
              </div>
              {error !== undefined && <ErrorNotice error={error} />}
              <h3>Payment details</h3>
              <Fields
                values={{
                  transaction_reference: r.source_values["Transaction number"],
                  description: r.source_values.Description,
                }}
              />
              <h3>Classification</h3>
              <Fields
                values={{
                  expense_type: r.source_values["Expense type"],
                  expense_area: r.source_values["Expense area"],
                  entity: r.source_values.Entity,
                }}
              />
              <h3>Source provenance</h3>
              <p>
                Record {r.source_record_number} ·{" "}
                {r.source_currently_active
                  ? "Original version active"
                  : "Retained historical version"}
              </p>
              <details>
                <summary>
                  Original published fields and immutable lineage
                </summary>
                <Fields values={r.source_values} />
                <Fields
                  values={{
                    filename: r.filename,
                    file_id: r.file_id,
                    file_SHA256: r.file_sha256,
                    row_hash: r.row_hash,
                    raw_row_id: r.raw_row_id,
                    physical_line_start: r.physical_line_start,
                    physical_line_end: r.physical_line_end,
                    ordinal: r.ordinal,
                    classification: r.classification,
                  }}
                />
              </details>
              <div className="actions">
                <button
                  disabled={position === 0}
                  onClick={() => setPosition(position - 1)}
                >
                  Previous
                </button>
                <span>
                  {position + 1} of {detail.data?.total}
                </span>
                <button
                  disabled={position + 1 >= (detail.data?.total || 0)}
                  onClick={() => setPosition(position + 1)}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </DetailDrawer>
      )}
    </>
  );
}

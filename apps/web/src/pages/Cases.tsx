import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { RefreshCw, Plus, Search } from "lucide-react";
import { useCases } from "../hooks/queries";
import { label } from "../format";
import { Loading, ErrorNotice, Pagination } from "../components/Common";
import { SectionHeader, CaseCard, EmptyState } from "../components/Design";
import { Button } from "../components/ui/button";
import { caseTitle } from "../lib/presentation";
export function Cases() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") || "",
    raw = params.get("offset") || "0";
  const [search, setSearch] = useState("");

  const valid =
    ["", "OPEN", "INVESTIGATING", "REVIEWED", "CLOSED"].includes(status) &&
    /^\d+$/.test(raw) &&
    +raw <= 1000000;
  const offset = valid ? +raw : 0;
  const query = `offset=${offset}&limit=50${status ? `&status=${status}` : ""}`;
  const result = useCases(query, valid);
  const visible =
    result.data?.items.filter((c) =>
      `${c.case_reference} ${c.title} ${caseTitle(c)}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) || [];
  function update(key: string, value: string) {
    const p = new URLSearchParams(params);
    if (value) p.set(key, value);
    else p.delete(key);
    if (key === "status") p.delete("offset");
    setParams(p);
  }
  return (
    <>
      <SectionHeader
        eyebrow="Investigations"
        title="Saved cases"
        description="Evidence, findings and decisions. One place to continue the work."
        action={
          <div className="actions">
            <Button
              variant="outline"
              onClick={() => void result.refetch()}
              aria-label="Refresh cases"
            >
              <RefreshCw size={15} />
            </Button>
            <Button asChild>
              <Link to="/investigations/reviews">
                <Plus size={15} />
                New investigation
              </Link>
            </Button>
          </div>
        }
      />
      <div className="toolbar">
        <label className="search-field">
          <Search size={16} />
          <input
            aria-label="Search loaded cases"
            placeholder="Search this page of cases…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label>
          Status
          <select
            value={status}
            onChange={(e) => update("status", e.target.value)}
          >
            <option value="">All statuses</option>
            {["OPEN", "INVESTIGATING", "REVIEWED", "CLOSED"].map((s) => (
              <option value={s} key={s}>
                {label(s)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {!valid ? (
        <div role="alert">
          Invalid case filters.{" "}
          <button onClick={() => setParams({})}>Reset filters</button>
        </div>
      ) : result.isPending ? (
        <Loading />
      ) : result.isError ? (
        <ErrorNotice error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          <div className="list-meta">
            <span>{visible.length} shown on this page</span>
            <small>{result.data.total} saved records in this workspace</small>
          </div>
          {visible.length ? (
            <div className="case-grid">
              {visible.map((c) => (
                <CaseCard key={c.case_id} record={c} />
              ))}
            </div>
          ) : (
            <div className="panel">
              <EmptyState
                title="No cases in this view"
                detail={
                  search
                    ? "Try a different search or another page."
                    : "Start from a procurement review, or switch Demo Mode in the header to explore saved examples."
                }
                action={
                  <Button variant="outline" asChild>
                    <Link to="/investigations/reviews">
                      Browse the Review Queue
                    </Link>
                  </Button>
                }
              />
            </div>
          )}
          <Pagination
            total={result.data.total}
            offset={offset}
            onChange={(n) => update("offset", String(n))}
          />
        </>
      )}
    </>
  );
}

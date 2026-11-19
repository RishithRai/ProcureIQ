import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import { DetailDrawer } from "../components/Design";
import { useState } from "react";
import {
  Link,
  useParams,
  useSearchParams,
  useNavigate,
} from "react-router-dom";
import {
  useData,
  useScope,
  ScopeFilters,
  Metrics,
  Chart,
  str,
  RecordFields,
  ReadState,
} from "./shared";
import type { Row, DataPage } from "./shared";
import { Pagination } from "../components/Common";
import { money, label } from "../format";
function Transactions({ query, basis }: { query: string; basis: string }) {
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [order, setOrder] = useState("source");
  const [selected, setSelected] = useState("");
  const data = useData<DataPage>(
    `/spend/transactions?${query}&basis=${basis}&offset=${offset}&search=${encodeURIComponent(search)}&order=${order}`,
  );
  const detail = useData<{ record: Row }>(
    `/spend/transactions/${selected}`,
    !!selected,
  );
  return (
    <>
      <div className="toolbar">
        <label>
          Search transactions
          <input
            value={search}
            placeholder="Supplier, reference or description"
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label>
          Global ordering
          <select
            value={order}
            onChange={(e) => {
              setOrder(e.target.value);
              setOffset(0);
            }}
          >
            <option value="source">Source order</option>
            <option value="amount_desc">Amount descending</option>
            <option value="amount_asc">Amount ascending</option>
          </select>
        </label>
      </div>
      <ReadState
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && !data.isError && (
        <>
          <Pagination
            offset={offset}
            total={data.data.total}
            onChange={setOffset}
          />
          <div className="table-scroll evidence-table">
            <table>
              <thead>
                <tr>
                  {[
                    "Source record",
                    "Month",
                    "Supplier",
                    "Category",
                    "Area",
                    "Amount",
                    "Reference",
                  ].map((x) => (
                    <th key={x}>{x}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.data.items.map((r) => (
                  <tr key={str(r.raw_row_id)}>
                    <td>
                      <button onClick={() => setSelected(str(r.raw_row_id))}>
                        Inspect #{str(r.raw_row_id)}
                      </button>
                    </td>
                    <td>{str(r.reporting_month).slice(0, 7)}</td>
                    <td>{str(r.supplier_raw)}</td>
                    <td>{str(r.expense_type)}</td>
                    <td>{str(r.expense_area)}</td>
                    <td>{money(str(r.amount_gbp))}</td>
                    <td>{str(r.transaction_number)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.data.total && (
              <p className="empty">
                No transactions match this scope and search.
              </p>
            )}
          </div>
        </>
      )}
      {selected && (
        <DetailDrawer
          title="Transaction and source lineage"
          onClose={() => setSelected("")}
        >
          <ReadState
            pending={detail.isPending}
            error={detail.error}
            retry={() => void detail.refetch()}
          />
          {detail.data && (
            <>
              <div className="drawer-amount">
                <small>Published amount · GBP</small>
                <h2>
                  {money(
                    str(
                      (detail.data.record.source_values as Row)?.Amount,
                    ).replace(/[£,\s]/g, ""),
                  )}
                </h2>
                <h3>
                  {str((detail.data.record.source_values as Row)?.Supplier)}
                </h3>
              </div>
              <RecordFields
                value={{
                  reporting_month: detail.data.record.reporting_month,
                  ...Object.fromEntries(
                    [
                      "Date",
                      "Expense type",
                      "Expense area",
                      "Transaction number",
                      "Description",
                    ].map((k) => [
                      k,
                      (detail.data!.record.source_values as Row)?.[k] ?? null,
                    ]),
                  ),
                }}
              />
              <details>
                <summary>Original source and technical lineage</summary>
                <RecordFields value={detail.data.record} />
              </details>
            </>
          )}
        </DetailDrawer>
      )}
    </>
  );
}
export function Spend() {
  const navigate = useNavigate();
  const scope = useScope();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "overview";
  const setTab = (tab: string) => {
    const p = new URLSearchParams(params);
    p.set("tab", tab);
    setParams(p);
  };
  const [search, setSearch] = useState("");
  const [fullTable, setFullTable] = useState(false);
  const [offset, setOffset] = useState(0);
  const [value, setValue] = useState("positive_gbp");
  const summary = useData<{
    source_fingerprint: string;
    overview: Row[];
    monthly: Row[];
    concentration: Row[];
  }>(`/spend/summary?${scope.reporting}`, !scope.invalid);
  const basis = summary.data?.source_fingerprint || "";
  const groups = useData<DataPage>(
    `/spend/groups/${tab}?${scope.reporting}&offset=${offset}&basis=${basis}&search=${encodeURIComponent(search)}`,
    !!basis && tab !== "transactions" && tab !== "overview",
  );
  const leadingCategories = useData<DataPage>(
    `/spend/groups/expense_types?${scope.reporting}&limit=5&basis=${basis}`,
    !!basis,
  );
  const leadingSuppliers = useData<DataPage>(
    `/spend/groups/suppliers?${scope.reporting}&limit=5&basis=${basis}`,
    !!basis,
  );
  const pareto = useData<DataPage>(
    `/spend/pareto?${scope.reporting}&basis=${basis}`,
    !!basis && tab === "suppliers",
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Spend Explorer</p>
          <h1>Explore disclosed expenditure</h1>
          <p className="muted">
            Follow the population from category and supplier to original source
            records.
          </p>
        </div>
        <Link className="button" to={`/strategy/scenarios?${scope.reporting}`}>
          Build financial scenario
        </Link>
      </div>
      <ScopeFilters />
      {scope.invalid ? (
        <p role="alert">Invalid reporting scope. Reset filters.</p>
      ) : (
        <>
          <ReadState
            pending={summary.isPending}
            error={summary.error}
            retry={() => void summary.refetch()}
          />
          {summary.data && !summary.isError && (
            <>
              <Metrics row={summary.data.overview[0] || {}} />
              <Tabs
                value={tab}
                onValueChange={(v) => {
                  setTab(v);
                  setOffset(0);
                }}
                className="workspace-tabs"
              >
                <TabsList>
                  {[
                    ["overview", "Overview"],
                    ["expense_types", "Categories"],
                    ["suppliers", "Suppliers"],
                    ["transactions", "Transactions"],
                    ["category_concentration", "Concentration"],
                  ].map(([k, t]) => (
                    <TabsTrigger key={k} value={k}>
                      {t}
                    </TabsTrigger>
                  ))}
                </TabsList>
                <TabsContent value={tab}>
                  {tab === "overview" && (
                    <div>
                      <div className="analysis-overview">
                        <section className="panel padded">
                          <h2>Payments through the period</h2>
                          <label>
                            Expenditure measure
                            <select
                              value={value}
                              onChange={(e) => setValue(e.target.value)}
                            >
                              <option value="positive_gbp">
                                Positive payments
                              </option>
                              <option value="credit_gbp">
                                Credit magnitude
                              </option>
                              <option value="net_gbp">
                                Net disclosed payments
                              </option>
                            </select>
                          </label>
                          <Chart
                            rows={summary.data.monthly}
                            x="reporting_month"
                            value={value}
                            line
                          />
                        </section>
                        <aside className="panel padded">
                          <p className="eyebrow">Explore the population</p>
                          <h2>From patterns to source records</h2>
                          <p className="muted">
                            Compare categories, inspect supplier shares or open
                            an original payment record.
                          </p>
                          <div className="explore-actions">
                            {[
                              ["expense_types", "Category rankings"],
                              ["suppliers", "Supplier intelligence"],
                              ["transactions", "Source transactions"],
                            ].map(([k, t]) => (
                              <button key={k} onClick={() => setTab(k)}>
                                {t}
                                <span>↗</span>
                              </button>
                            ))}
                          </div>
                          <details>
                            <summary>What these payments represent</summary>
                            <p>
                              Published gross VAT-inclusive payments. Credits
                              remain separate. This disclosure subset does not
                              establish unit prices, service comparability or
                              savings.
                            </p>
                          </details>
                        </aside>
                      </div>
                      <div className="two-column">
                        <Breakdown
                          title="Top five categories"
                          rows={leadingCategories.data?.items || []}
                          scope={scope.reporting}
                          field="expense_type"
                        />
                        <Breakdown
                          title="Top five suppliers"
                          rows={leadingSuppliers.data?.items || []}
                          scope={scope.reporting}
                          field="supplier_id"
                        />
                      </div>
                      <details>
                        <summary>Selected population concentration</summary>
                        <RecordFields
                          value={summary.data.concentration[0] || {}}
                        />
                      </details>
                    </div>
                  )}
                  {tab !== "overview" && (
                    <section className="panel padded">
                      {tab === "transactions" ? (
                        <Transactions
                          key={scope.reporting}
                          query={scope.reporting}
                          basis={basis}
                        />
                      ) : (
                        <>
                          <ReadState
                            pending={groups.isPending}
                            error={groups.error}
                            retry={() => void groups.refetch()}
                          />
                          {groups.data && !groups.isError && (
                            <>
                              {tab === "expense_types" && (
                                <>
                                  <Breakdown
                                    title="Leading categories"
                                    rows={leadingCategories.data?.items || []}
                                    scope={scope.reporting}
                                    field="expense_type"
                                  />
                                  <label>
                                    Search all categories
                                    <input
                                      value={search}
                                      onChange={(e) => {
                                        setSearch(e.target.value);
                                        setOffset(0);
                                      }}
                                    />
                                  </label>
                                </>
                              )}
                              {tab === "category_concentration" && (
                                <p>
                                  HHI measures observed disclosed-payment
                                  concentration. A category with one resolved
                                  supplier naturally has HHI 10,000.
                                  Concentration alone does not prove inefficient
                                  procurement. Drill down to understand category
                                  scope and value.
                                </p>
                              )}
                              {tab === "suppliers" && (
                                <button
                                  onClick={() => setFullTable(!fullTable)}
                                >
                                  {fullTable
                                    ? "Show supplier cards"
                                    : "Show full supplier table"}
                                </button>
                              )}
                              <Pagination
                                offset={offset}
                                total={groups.data.total}
                                onChange={setOffset}
                              />
                              {tab === "suppliers" && (
                                <p>
                                  Full selected positive-supplier population:{" "}
                                  {pareto.data?.total ?? "…"}. Horizontal axis:
                                  supplier rank. Vertical axis: cumulative
                                  resolved positive-payment share (%). Click a
                                  point to open its supplier.
                                </p>
                              )}
                              {tab === "suppliers" && (
                                <Chart
                                  onSelect={(r) => {
                                    if (r.supplier_id)
                                      navigate(
                                        `/spend/suppliers/${str(r.supplier_id)}?${scope.reporting}`,
                                      );
                                  }}
                                  rows={pareto.data?.items || []}
                                  x="supplier_rank"
                                  value="cumulative_resolved_pct"
                                  line
                                />
                              )}
                              {tab === "suppliers" && !fullTable && (
                                <div className="supplier-grid">
                                  {groups.data.items.slice(0, 6).map((r) => (
                                    <SupplierCard
                                      key={str(r.supplier_id)}
                                      row={r}
                                      scope={scope.reporting}
                                    />
                                  ))}
                                </div>
                              )}
                              {(tab !== "suppliers" || fullTable) && (
                                <div className="table-scroll">
                                  <table>
                                    <thead>
                                      <tr>
                                        <th>Scope</th>
                                        <th>{label(value)}</th>
                                        <th>Concentration / share context</th>
                                        <th>Actions</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {groups.data.items.map((r, i) => (
                                        <tr key={i}>
                                          <td>
                                            {str(
                                              r.canonical_name || r.group_value,
                                            ) || "Unclassified"}
                                          </td>
                                          <td>
                                            {money(
                                              str(r[value] ?? r.positive_gbp),
                                            )}
                                          </td>
                                          <td>
                                            {tab === "category_concentration"
                                              ? `HHI ${Number(r.hhi).toFixed(2)}`
                                              : tab === "suppliers"
                                                ? `${Number(r.share_all_positive_pct).toFixed(2)}% of all positive payments; ${Number(r.cumulative_resolved_pct).toFixed(2)}% cumulative resolved`
                                                : "Published category"}
                                          </td>
                                          <td>
                                            {tab === "suppliers" ? (
                                              <Link
                                                to={`/spend/suppliers/${str(r.supplier_id)}?${scope.reporting}`}
                                              >
                                                Open supplier
                                              </Link>
                                            ) : (
                                              <Link
                                                to={`/spend?${new URLSearchParams({ ...Object.fromEntries(new URLSearchParams(scope.reporting)), expense_type: str(r.group_value), tab: "transactions" })}`}
                                              >
                                                Explore category
                                              </Link>
                                            )}{" "}
                                            ·{" "}
                                            <Link
                                              to={`/investigations/reviews?${new URLSearchParams({ ...Object.fromEntries(new URLSearchParams(scope.reporting)), ...(tab === "suppliers" ? { supplier_id: str(r.supplier_id) } : { expense_type: str(r.group_value) }) })}`}
                                            >
                                              Reviews
                                            </Link>
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                              <p className="small muted">
                                Concentration describes the disclosed payment
                                population, not inefficiency. Pareto uses
                                resolved positive-payment suppliers.
                              </p>
                            </>
                          )}
                        </>
                      )}
                    </section>
                  )}
                </TabsContent>
              </Tabs>
            </>
          )}
        </>
      )}
    </>
  );
}
export function Supplier() {
  const { supplierId = "" } = useParams();
  const scope = useScope();
  const navigate = useNavigate();
  const supplierScope = new URLSearchParams(scope.reporting);
  supplierScope.set("supplier_id", supplierId);
  const txLink = (extra: Record<string, string> = {}) =>
    `/spend?${new URLSearchParams({ ...Object.fromEntries(supplierScope), tab: "transactions", ...extra })}`;
  const data = useData<{
    supplier: Row;
    aliases: Row[];
    analytics: Record<string, Row[]>;
    share_context: Row;
    concentration_context: Row[];
    source_fingerprint: string;
    filters: Row;
  }>(`/spend/suppliers/${supplierId}?${scope.reporting}`);
  return (
    <>
      <Link to={`/spend?${scope.reporting}`}>Spend Explorer</Link>
      <ReadState
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <>
          <p className="eyebrow">Supplier intelligence</p>
          <h1>{str(data.data.supplier.canonical_name)}</h1>
          <p className="muted">
            {str(data.data.analytics.monthly[0]?.reporting_month).slice(0, 7)} –{" "}
            {str(data.data.analytics.monthly.at(-1)?.reporting_month).slice(
              0,
              7,
            )}{" "}
            ·{" "}
            {Number(
              data.data.share_context?.share_all_positive_pct || 0,
            ).toFixed(2)}
            % of selected positive payments
          </p>
          <Metrics row={data.data.analytics.overview[0] || {}} />
          <div className="actions">
            <Link className="button primary" to={txLink()}>
              Explore Transactions
            </Link>
            <Link
              className="button"
              to={`/investigations/reviews?${scope.reporting}&supplier_id=${supplierId}`}
            >
              Related reviews
            </Link>
            <Link
              className="button"
              to={`/strategy/scenarios?${scope.reporting}&supplier_id=${supplierId}`}
            >
              Build hypothetical scenario
            </Link>
            <Link
              className="button"
              to={`/strategy/optimization?context=${encodeURIComponent("Supplier " + str(data.data.supplier.canonical_name))}`}
            >
              Define sourcing assumptions
            </Link>
          </div>
          <div className="panel padded">
            <Chart
              onSelect={(r) =>
                navigate(
                  txLink({
                    start_month: str(r.reporting_month).slice(0, 7),
                    end_month: str(r.reporting_month).slice(0, 7),
                  }),
                )
              }
              rows={data.data.analytics.monthly}
              x="reporting_month"
              value="positive_gbp"
              line
            />
            <details>
              <summary>Recorded identity and aliases</summary>
              {data.data.aliases.map((r, i) => (
                <RecordFields key={i} value={r} />
              ))}
            </details>
            <details>
              <summary>Supplier share and concentration context</summary>
              <RecordFields value={data.data.share_context || {}} />
              {data.data.concentration_context.map((r, i) => (
                <RecordFields key={i} value={r} />
              ))}
            </details>
            <p>
              Reporting-period payments, not invoice or contract values. Click a
              month to inspect transactions.
            </p>
            <div className="filter-chips">
              {data.data.analytics.monthly.map((r) => (
                <Link
                  key={str(r.reporting_month)}
                  to={txLink({
                    start_month: str(r.reporting_month).slice(0, 7),
                    end_month: str(r.reporting_month).slice(0, 7),
                  })}
                >
                  {str(r.reporting_month).slice(0, 7)}
                </Link>
              ))}
            </div>
            <div className="two-column">
              {["expense_types", "expense_areas"].map((k) => (
                <Breakdown
                  key={k}
                  title={label(k)}
                  rows={data.data!.analytics[k]}
                  scope={supplierScope.toString()}
                  field={
                    k === "expense_types" ? "expense_type" : "expense_area"
                  }
                  total={str(data.data!.analytics.overview[0]?.positive_gbp)}
                />
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}

function SupplierCard({ row: r, scope }: { row: Row; scope: string }) {
  const detail = useData<{ analytics: Record<string, Row[]> }>(
    `/spend/suppliers/${str(r.supplier_id)}?${scope}`,
  );
  const months =
    detail.data?.analytics.monthly.filter((m) => Number(m.record_count) > 0) ||
    [];
  return (
    <Link
      className="supplier-card"
      to={`/spend/suppliers/${str(r.supplier_id)}?${scope}`}
    >
      <div className="supplier-monogram">
        {str(r.canonical_name).slice(0, 2).toUpperCase()}
      </div>
      <h3>{str(r.canonical_name)}</h3>
      <strong>{money(str(r.positive_gbp))}</strong>
      <p>
        {Number(r.share_all_positive_pct).toFixed(2)}% of selected positive
        payments
      </p>
      {detail.data && (
        <>
          <p>
            Activity:{" "}
            {months.length
              ? `${str(months[0].reporting_month).slice(0, 7)} – ${str(months.at(-1)?.reporting_month).slice(0, 7)}`
              : "No published lines"}
          </p>
          <p className="supplier-categories">
            {detail.data.analytics.expense_types
              .slice(0, 2)
              .map((x) => str(x.group_value))
              .join(" · ")}
          </p>
        </>
      )}
      <span>View supplier detail ↗</span>
    </Link>
  );
}

function Breakdown({
  title,
  rows,
  scope,
  field,
  total,
}: {
  title: string;
  rows: Row[];
  scope: string;
  field: string;
  total?: string;
}) {
  const [all, setAll] = useState(false);
  const [selected, setSelected] = useState<Row>();
  const params = (r: Row) =>
    new URLSearchParams({
      ...Object.fromEntries(new URLSearchParams(scope)),
      [field]: str(field === "supplier_id" ? r.supplier_id : r.group_value),
    }).toString();
  return (
    <section className="panel padded">
      <h2>{title}</h2>
      {(all ? rows : rows.slice(0, 5)).map((r, i) => (
        <button
          className="breakdown-bar"
          key={i}
          title={money(str(r.positive_gbp))}
          onClick={() => setSelected(r)}
        >
          <span>
            {str(r.canonical_name || r.group_value) || "Unclassified"}
          </span>
          <strong>{money(str(r.positive_gbp))}</strong>
          <span className="bar-track">
            <i
              style={{
                width: `${Math.max(0, Math.min(100, (Number(r.positive_gbp) / Number(total || rows[0]?.positive_gbp || 1)) * 100))}%`,
              }}
            />
          </span>
          {total && (
            <small>
              {Number(r.supplier_positive_share_pct || 0).toFixed(2)}% of
              supplier positive payments
            </small>
          )}
        </button>
      ))}
      {rows.length > 5 && (
        <button onClick={() => setAll(!all)}>
          {all ? "Top five" : "Complete breakdown"}
        </button>
      )}
      {selected && (
        <DetailDrawer
          title={
            str(selected.canonical_name || selected.group_value) ||
            "Unclassified"
          }
          onClose={() => setSelected(undefined)}
        >
          <h2>{money(str(selected.positive_gbp))}</h2>
          <div className="actions">
            <Link to={`/spend?${params(selected)}&tab=transactions`}>
              Matching transactions
            </Link>
            <Link to={`/spend?${params(selected)}&tab=suppliers`}>
              Related suppliers
            </Link>
            <Link to={`/investigations/reviews?${params(selected)}`}>
              Related exported reviews
            </Link>
            <Link to={`/strategy/scenarios?${params(selected)}`}>
              Build financial scenario
            </Link>
            {field === "supplier_id" && (
              <Link
                to={`/spend/suppliers/${str(selected.supplier_id)}?${scope}`}
              >
                Open supplier profile
              </Link>
            )}
          </div>
          <RecordFields value={selected} />
        </DetailDrawer>
      )}
    </section>
  );
}

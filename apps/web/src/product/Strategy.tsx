import { Hint } from "../components/Design";
import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { request, ApiError } from "../api/client";
import {
  useScope,
  ScopeFilters,
  str,
  RecordFields,
  saveJson,
  download,
  Chart,
} from "./shared";
import type { Row } from "./shared";
import { ErrorNotice } from "../components/Common";
import { label, money } from "../format";
const names = ["Conservative", "Base", "Ambitious"];
const empty = () =>
  Object.fromEntries(
    names.map((n) => [
      n,
      {
        addressable_pct: "0",
        adoption_pct: "0",
        improvement_pct: "0",
        implementation_cost: "0",
        operating_cost: "0",
      },
    ]),
  );
type ScenarioState = {
  baseline: Row | null;
  assumptions: Record<string, Record<string, string>>;
  result: Row | null;
  stale: boolean;
};
const initial = (): ScenarioState => ({
  baseline: null,
  assumptions: empty(),
  result: null,
  stale: false,
});
const Context = createContext<{
  state: ScenarioState;
  setState: React.Dispatch<React.SetStateAction<ScenarioState>>;
} | null>(null);
export function ProductState({ children }: { children: ReactNode }) {
  const [state, setState] = useState(initial);
  return (
    <Context.Provider value={{ state, setState }}>{children}</Context.Provider>
  );
}
export function useScenario() {
  const value = useContext(Context);
  if (!value) throw new Error("Product state missing");
  return value;
}
export function Scenarios() {
  const { state, setState } = useScenario();
  const scope = useScope();
  const [wholePopulation, setWholePopulation] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [kind, setKind] = useState("hmrc");
  const [manual, setManual] = useState({
    amount: "0",
    start_month: "",
    end_month: "",
    scope: "",
  });
  const [selected, setSelected] = useState("Base");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  async function action(fn: () => Promise<void>) {
    setError(undefined);
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(e);
      if (e instanceof ApiError && e.code === "stale_source")
        setState((s) => ({ ...s, stale: true }));
    } finally {
      setBusy(false);
    }
  }
  const doc = state.result?.document as Row | undefined;
  async function bind() {
    await action(async () => {
      const baseline = await request<Row>("/strategy/baseline", undefined, {
        kind,
        filters: Object.fromEntries(
          [...new URLSearchParams(scope.reporting)].map(([k, v]) => [
            k,
            k === "supplier_id" ? Number(v) : v,
          ]),
        ),
        ...manual,
        start_month: manual.start_month ? manual.start_month + "-01" : null,
        end_month: manual.end_month ? manual.end_month + "-01" : null,
      });
      setState((s) => ({ ...s, baseline, result: null, stale: false }));
    });
  }
  useEffect(() => {
    if (!state.baseline || state.stale) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setPreviewing(true);
      request<Row>("/strategy/calculate", controller.signal, {
        baseline: state.baseline,
        scenarios: state.assumptions,
        selected,
      })
        .then((result) => {
          if (!controller.signal.aborted) setState((s) => ({ ...s, result }));
        })
        .catch((e) => {
          if (
            !controller.signal.aborted &&
            e instanceof ApiError &&
            e.code === "stale_source"
          )
            setState((s) => ({ ...s, stale: true, result: null }));
        })
        .finally(() => {
          if (!controller.signal.aborted) setPreviewing(false);
        });
    }, 700);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [state.baseline, state.assumptions, state.stale, selected, setState]);
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Strategy Studio</p>
          <h1>Financial Scenario Lab</h1>
          <p className="muted">
            One explicitly selected expenditure pool. Three independent
            hypothetical alternatives.
          </p>
        </div>
        <Link className="button" to="/strategy/optimization">
          Optimization Studio
        </Link>
      </div>
      <div className="workflow-path" aria-label="Modelling workflow">
        <span className="current">01 · Select baseline</span>
        <span>02 · Set assumptions</span>
        <span>03 · Compare & export</span>
      </div>
      <ScopeFilters />
      <section className="panel padded baseline-panel">
        <p className="eyebrow">01 / Model basis</p>
        <h2>Select your expenditure pool</h2>
        <label>
          Baseline source
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="hmrc">
              Current filtered disclosed positive payments
            </option>
            <option value="manual">Analyst-provided manual baseline</option>
          </select>
        </label>
        {kind === "manual" && (
          <div className="filter-grid">
            {Object.keys(manual).map((k) => (
              <label key={k}>
                {label(k)}
                <input
                  type={k.endsWith("month") ? "month" : "text"}
                  value={manual[k as keyof typeof manual]}
                  onChange={(e) =>
                    setManual({ ...manual, [k]: e.target.value })
                  }
                />
              </label>
            ))}
          </div>
        )}
        {kind === "hmrc" && !scope.reporting && (
          <label className="check">
            <input
              type="checkbox"
              checked={wholePopulation}
              onChange={(e) => setWholePopulation(e.target.checked)}
            />
            Deliberately select the complete disclosed expenditure population.
            This does not imply all expenditure is addressable.
          </label>
        )}
        <button
          disabled={
            busy ||
            scope.invalid ||
            (kind === "hmrc" && !scope.reporting && !wholePopulation)
          }
          className="primary"
          onClick={() => void bind()}
        >
          Use selected baseline
        </button>
        {state.baseline && (
          <>
            <h3>{str(state.baseline.scope)}</h3>
            <p>
              <strong>{money(str(state.baseline.amount_gbp))}</strong> ·{" "}
              {str(state.baseline.period_label)}
            </p>
            <p className="small muted">{str(state.baseline.limitation)}</p>
          </>
        )}
        <details>
          <summary>Load saved scenario</summary>
          <label>
            Import saved scenario JSON
            <input
              type="file"
              accept=".json,application/json"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f)
                  void action(async () => {
                    if (f.size > 2000000) throw new Error("File too large");
                    const imported = await request<{
                      document: Row;
                      stale: boolean;
                    }>("/strategy/import", undefined, {
                      document: JSON.parse(await f.text()),
                    });
                    setState({
                      baseline: imported.document.baseline as Row,
                      assumptions: imported.document.scenarios as Record<
                        string,
                        Record<string, string>
                      >,
                      result: { document: imported.document },
                      stale: imported.stale,
                    });
                  });
              }}
            />
          </label>
        </details>
      </section>
      {state.stale && (
        <div className="notice">
          Historical scenario basis. Outputs and exports are blocked until
          reviewed.
          <button
            onClick={() =>
              void action(async () => {
                if (
                  !window.confirm(
                    "Accept the current source population and recompute this scenario?",
                  )
                )
                  return;
                const fresh = await request<Row>(
                  "/strategy/refresh",
                  undefined,
                  { document: doc },
                );
                setState((s) => ({
                  ...s,
                  baseline: fresh.baseline as Row,
                  result: null,
                  stale: false,
                }));
              })
            }
          >
            Review and accept current source
          </button>
        </div>
      )}
      {state.baseline && (
        <section className="panel padded">
          <p className="eyebrow">02 / Independent alternatives</p>
          <h2>Shape three scenarios</h2>
          <p className="muted small">
            Percentage inputs are 0–100. Costs apply to the same selected
            period. No assumptions are inferred from supplier exposure.
          </p>
          <div className="actions">
            <button
              onClick={() =>
                setState((s) => ({
                  ...s,
                  assumptions: Object.fromEntries(
                    names.map((n, i) => [
                      n,
                      {
                        addressable_pct: "20",
                        adoption_pct: String((i + 1) * 25),
                        improvement_pct: String(i + 1),
                        implementation_cost: "100000",
                        operating_cost: "50000",
                      },
                    ]),
                  ),
                  result: null,
                }))
              }
            >
              Load illustrative examples (not validated rates)
            </button>
            <button
              onClick={() =>
                setState((s) => ({ ...s, assumptions: empty(), result: null }))
              }
            >
              Reset assumptions
            </button>
          </div>
          <p className="small">
            Gross benefit = selected positive expenditure × addressable share ×
            adoption × improvement. Net benefit subtracts same-period
            implementation and operating costs.
          </p>
          <button
            onClick={() =>
              setState((s) => ({
                ...s,
                result: null,
                assumptions: {
                  Conservative: { ...s.assumptions.Base },
                  Base: { ...s.assumptions.Base },
                  Ambitious: { ...s.assumptions.Base },
                },
              }))
            }
          >
            Copy from Base to other cases
          </button>
          <div className="three-column">
            {names.map((n) => (
              <fieldset
                className={`scenario-input scenario-${n.toLowerCase()}`}
                key={n}
              >
                <legend>{n}</legend>
                {Object.entries(state.assumptions[n]).map(([k, v]) => (
                  <label key={k}>
                    <Hint
                      text={
                        (
                          {
                            addressable_pct:
                              "Share of selected payments that could plausibly be affected.",
                            adoption_pct:
                              "Share of addressable expenditure adopting the intervention.",
                            improvement_pct:
                              "Assumed reduction or benefit rate on affected expenditure.",
                            implementation_cost:
                              "One-time costs within this same reporting period.",
                            operating_cost:
                              "Ongoing costs within the selected period.",
                          } as Record<string, string>
                        )[k]
                      }
                    >
                      {label(k)}
                    </Hint>
                    {k.endsWith("_pct") && (
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="1"
                        aria-label={`${n} ${label(k)} slider`}
                        value={Math.min(100, Math.max(0, Number(v) || 0))}
                        onChange={(e) =>
                          setState((s) => ({
                            ...s,
                            result: null,
                            assumptions: {
                              ...s.assumptions,
                              [n]: { ...s.assumptions[n], [k]: e.target.value },
                            },
                          }))
                        }
                      />
                    )}
                    <input
                      aria-label={`${n} ${label(k)}`}
                      inputMode="decimal"
                      value={v}
                      onChange={(e) =>
                        setState((s) => ({
                          ...s,
                          result: null,
                          assumptions: {
                            ...s.assumptions,
                            [n]: { ...s.assumptions[n], [k]: e.target.value },
                          },
                        }))
                      }
                    />
                  </label>
                ))}
              </fieldset>
            ))}
          </div>
          <label>
            Sensitivity case
            <select
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setState((s) => ({ ...s, result: null }));
              }}
            >
              {names.map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
          <p role="status">
            {previewing
              ? "Updating backend-calculated preview…"
              : "Preview uses the verified backend model; invalid inputs do not produce a result."}
          </p>
          <button
            disabled={busy || state.stale}
            className="primary"
            onClick={() =>
              void action(async () => {
                const filters = state.baseline!.filters as Row;
                const result = await request<Row>(
                  "/strategy/calculate",
                  undefined,
                  {
                    baseline: { ...state.baseline, filters },
                    scenarios: state.assumptions,
                    selected,
                  },
                );
                setState((s) => ({ ...s, result }));
              })
            }
          >
            Calculate hypothetical cases
          </button>
        </section>
      )}
      {error !== undefined && <ErrorNotice error={error} />}{" "}
      {doc && !state.stale && (
        <section className="panel padded">
          <p className="eyebrow">03 / Decision support</p>
          <h2>Compare hypothetical outcomes</h2>
          <div className="three-column">
            {names
              .map((n) => [n, (doc.outputs as Record<string, Row>)[n]] as const)
              .map(([n, r]) => (
                <article
                  className={`scenario-result scenario-${n.toLowerCase()}`}
                  key={n}
                >
                  <p className="eyebrow">{n}</p>
                  <small>Net hypothetical benefit</small>
                  <strong className="result-amount">
                    {money(str(r.net_benefit_gbp))}
                  </strong>
                  <div className="result-details">
                    <span>
                      Gross benefit
                      <strong>{money(str(r.gross_benefit_gbp))}</strong>
                    </span>
                    <span>
                      Same-period costs
                      <strong>{money(str(r.total_costs_gbp))}</strong>
                    </span>
                    <span>
                      ROI
                      <strong>
                        {r.roi_pct == null
                          ? "Unavailable"
                          : `${str(r.roi_pct)}%`}
                      </strong>
                    </span>
                  </div>
                  <details>
                    <summary>Calculation breakdown</summary>
                    <RecordFields value={r} />
                  </details>
                </article>
              ))}
          </div>
          <Chart
            rows={names
              .map((n) => [n, (doc.outputs as Record<string, Row>)[n]] as const)
              .map(([name, r]) => ({ name, ...r }))}
            x="name"
            value="gross_benefit_gbp"
            compare="total_costs_gbp"
          />
          <p className="notice">
            These are alternatives. Do not add them together or describe them as
            expected or realized savings.
          </p>
          {state.result?.sensitivity && (
            <>
              <h3>Sensitivity: net hypothetical benefit</h3>
              <p>
                Each cell varies adoption and improvement while holding the
                selected case’s addressability and costs fixed. Hover or focus a
                cell for the exact assumptions; click to apply them.
              </p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Adoption</th>
                      {Array.from({ length: 11 }, (_, i) => (
                        <th key={i}>{i}% improvement</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from({ length: 11 }, (_, a) => (
                      <tr key={a}>
                        <th>{a * 10}%</th>
                        {(state.result!.sensitivity as Row[])
                          .filter((r) => Number(r.adoption_pct) === a * 10)
                          .map((r, i) => (
                            <td
                              key={i}
                              tabIndex={0}
                              title={`Adoption ${str(r.adoption_pct)}%, improvement ${str(r.improvement_pct)}%: ${money(str(r.net_benefit_gbp))} net hypothetical benefit`}
                              aria-label={`Adoption ${str(r.adoption_pct)}%, improvement ${str(r.improvement_pct)}%`}
                              onClick={() =>
                                setState((s) => ({
                                  ...s,
                                  result: null,
                                  assumptions: {
                                    ...s.assumptions,
                                    [selected]: {
                                      ...s.assumptions[selected],
                                      adoption_pct: str(r.adoption_pct),
                                      improvement_pct: str(r.improvement_pct),
                                    },
                                  },
                                }))
                              }
                              onKeyDown={(e) => {
                                if (e.key === "Enter") e.currentTarget.click();
                              }}
                              className={
                                Number(r.adoption_pct) ===
                                  Number(
                                    state.assumptions[selected].adoption_pct,
                                  ) &&
                                Number(r.improvement_pct) ===
                                  Number(
                                    state.assumptions[selected].improvement_pct,
                                  )
                                  ? "selected-sensitivity"
                                  : ""
                              }
                              style={{
                                background:
                                  Number(r.net_benefit_gbp) < 0
                                    ? "var(--negative-tint)"
                                    : `color-mix(in srgb, var(--primary) ${8 + Math.min(35, (Math.max(0, Number(r.net_benefit_gbp)) / Math.max(1, ...(state.result!.sensitivity as Row[]).map((x) => Math.abs(Number(x.net_benefit_gbp))))) * 35)}%, var(--card))`,
                              }}
                            >
                              {money(str(r.net_benefit_gbp))}
                            </td>
                          ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <h3>Break-even threshold</h3>
              <p className="muted small">
                Required improvement at the selected adoption level. This is a
                model threshold, not a forecast.
              </p>
              <div className="break-even">
                <strong>
                  {(state.result.break_even as Row).improvement_pct == null
                    ? "Unavailable"
                    : `${Number((state.result.break_even as Row).improvement_pct).toFixed(4)}% improvement`}
                </strong>
                <div className="threshold-track" aria-hidden="true">
                  <i
                    style={{
                      width: `${Math.min(100, Number((state.result.break_even as Row).improvement_pct) || 0)}%`,
                    }}
                  />
                </div>
                <div className="track-labels">
                  <small>0%</small>
                  <small>100% improvement</small>
                </div>
                <p>{str((state.result.break_even as Row).reason)}</p>
                <details>
                  <summary>Exact break-even value</summary>
                  <RecordFields value={state.result.break_even as Row} />
                </details>
              </div>
            </>
          )}
          <div className="actions">
            <button onClick={() => saveJson(doc, "procureiq_scenario.json")}>
              Download JSON
            </button>
            <button
              disabled={busy}
              onClick={() =>
                void action(() =>
                  download(
                    "/strategy/excel",
                    { document: doc },
                    "procureiq_scenario.xlsx",
                  ),
                )
              }
            >
              Download Excel model
            </button>
            <Link
              className="button primary"
              to={`/reports?${new URLSearchParams(
                Object.entries((state.baseline?.filters as Row) || {})
                  .filter(([, v]) => v != null)
                  .map(([k, v]) => [
                    k,
                    k.endsWith("month") ? str(v).slice(0, 7) : str(v),
                  ]),
              )}`}
            >
              Use in Executive Reports
            </Link>
          </div>
        </section>
      )}
    </>
  );
}

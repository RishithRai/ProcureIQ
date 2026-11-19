import { Badge } from "../components/ui/badge";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { request } from "../api/client";
import { useData, str, saveJson, ReadState, RecordFields } from "./shared";
import type { Row, DataPage } from "./shared";
import { ErrorNotice, Pagination } from "../components/Common";
import { money, label } from "../format";
type Candidate = {
  name: string;
  unit_cost: string;
  capacity: string;
  minimum: string;
  maximum: string | null;
  fixed_cost: string;
  eligible: boolean;
};
type Model = {
  title: string;
  units: string;
  assumption_note: string;
  demand: string;
  candidates: Candidate[];
  dependency_pct: string;
  min_suppliers: number;
  max_suppliers: number;
  time_limit: number;
  context: string | null;
};
const candidate = (): Candidate => ({
  name: "",
  unit_cost: "0",
  capacity: "0",
  minimum: "0",
  maximum: null,
  fixed_cost: "0",
  eligible: true,
});
export function Optimization() {
  const [params] = useSearchParams();
  const [step, setStep] = useState(1);
  const [view, setView] = useState("builder");
  const [validation, setValidation] = useState("");
  const [model, setModel] = useState<Model>({
    title: "",
    units: "",
    assumption_note: "",
    demand: "0",
    candidates: [candidate()],
    dependency_pct: "100",
    min_suppliers: 1,
    max_suppliers: 40,
    time_limit: 10,
    context: params.get("context"),
  });
  const [result, setResult] = useState<Row>();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  const [comparison, setComparison] = useState<
    { title: string; result: Row; assumptions: Model }[]
  >([]);
  const runs = useData<DataPage>(
    `/strategy/optimization/runs?offset=${offset}`,
  );
  async function run(save = false) {
    setBusy(true);
    setError(undefined);
    try {
      const value = await request<Row>(
        save ? "/strategy/optimization/runs" : "/strategy/optimization/solve",
        undefined,
        save ? { assumptions: model } : model,
      );
      const solved = save ? (value.result as Row) : value;
      setResult(solved);
      setComparison((c) => [
        ...c.slice(-5),
        {
          title: `${model.title} · dependency ${model.dependency_pct}%`,
          result: solved,
          assumptions: structuredClone(model),
        },
      ]);
      if (save) void runs.refetch();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function update(p: Partial<Model>) {
    setModel((m) => ({ ...m, ...p }));
    setResult(undefined);
  }
  function go(next: number) {
    if (
      next > 1 &&
      (!model.title.trim() ||
        !model.units.trim() ||
        model.assumption_note.trim().length < 10 ||
        !(Number(model.demand) > 0))
    ) {
      setValidation(
        "Provide a title, comparable unit, positive quantity and assumption notes (at least 10 characters).",
      );
      return;
    }
    if (
      next > 2 &&
      model.candidates.some(
        (c) =>
          !c.name.trim() ||
          !Number.isFinite(Number(c.unit_cost)) ||
          Number(c.unit_cost) < 0 ||
          !(Number(c.capacity) >= 0),
      )
    ) {
      setValidation(
        "Each supplier needs a name, nonnegative assumed price and capacity.",
      );
      return;
    }
    if (
      next > 3 &&
      (!(
        Number(model.dependency_pct) > 0 && Number(model.dependency_pct) <= 100
      ) ||
        model.min_suppliers < 1 ||
        model.max_suppliers < model.min_suppliers ||
        model.max_suppliers > 40)
    ) {
      setValidation(
        "Use dependency above 0 and at most 100%, and supplier counts between 1 and 40 with minimum no greater than maximum.",
      );
      return;
    }
    setValidation("");
    setStep(next);
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Strategy Studio</p>
          <h1>Constraint-based sourcing optimizer</h1>
          <p className="muted">
            Real MILP allocation from explicit comparable-unit assumptions.
          </p>
        </div>
        <Link to="/strategy/scenarios">Financial Scenario Lab</Link>
      </div>
      <div className="actions">
        <button
          aria-pressed={view === "builder"}
          onClick={() => setView("builder")}
        >
          Sourcing builder
        </button>
        <button
          aria-pressed={view === "saved"}
          onClick={() => setView("saved")}
        >
          Saved Strategies
        </button>
      </div>
      {view === "builder" && (
        <>
          <div className="workflow-path">
            {[
              "Define requirement",
              "Define suppliers",
              "Set constraints",
              "Optimize and compare",
            ].map((title, i) => (
              <button
                className={step === i + 1 ? "current" : ""}
                key={title}
                onClick={() => go(i + 1)}
              >
                {i + 1} · {title}
              </button>
            ))}
          </div>
          {validation && <p role="alert">{validation}</p>}
          <details className="method-note">
            <summary>Commercial assumptions · not verified HMRC prices</summary>
            <div className="notice">
              HMRC disclosures do not supply quotations, capacities or
              comparable service units. Every commercial input below is
              analyst-provided or explicitly illustrative; results are modelled
              costs, not achievable savings.
            </div>
          </details>
          {step == 1 && (
            <>
              <section className="panel padded">
                <p className="eyebrow">01 / Demand & requirements</p>
                <h2>Define the sourcing decision</h2>
                <button
                  onClick={() =>
                    update({
                      title: "[ILLUSTRATIVE] Comparable service units",
                      units: "equivalent service units",
                      assumption_note:
                        "Illustrative supplier costs and capacities, not verified HMRC commercial data.",
                      demand: "100",
                      dependency_pct: "60",
                      min_suppliers: 1,
                      max_suppliers: 2,
                      candidates: [
                        {
                          ...candidate(),
                          name: "Illustrative Supplier A",
                          unit_cost: "10",
                          capacity: "60",
                        },
                        {
                          ...candidate(),
                          name: "Illustrative Supplier B",
                          unit_cost: "20",
                          capacity: "100",
                        },
                      ],
                    })
                  }
                >
                  Load clearly illustrative example
                </button>
                <div className="filter-grid">
                  {(
                    ["title", "units", "assumption_note", "demand"] as const
                  ).map((k) => (
                    <label key={k}>
                      {label(k)}
                      <input
                        value={model[k]}
                        onChange={(e) =>
                          update({
                            [k]: e.target.value,
                          })
                        }
                      />
                    </label>
                  ))}
                </div>
                {model.context && (
                  <p>
                    Context: {model.context} (commercial assumptions remain
                    separate)
                  </p>
                )}
              </section>
            </>
          )}
          {step == 2 && (
            <>
              <section className="panel padded">
                <p className="eyebrow">02 / Comparable units</p>
                <h2>Candidate suppliers</h2>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        {[
                          "Supplier label",
                          "Unit cost GBP",
                          "Capacity",
                          "Minimum if selected",
                          "Maximum",
                          "Fixed cost GBP",
                          "Eligible",
                          "",
                        ].map((x, i) => (
                          <th key={i}>{x}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {model.candidates.map((c, i) => (
                        <tr key={i}>
                          {(
                            [
                              "name",
                              "unit_cost",
                              "capacity",
                              "minimum",
                              "maximum",
                              "fixed_cost",
                            ] as const
                          ).map((k) => (
                            <td key={k}>
                              <input
                                aria-label={`Supplier ${i + 1} ${label(k)}`}
                                value={c[k] ?? ""}
                                onChange={(e) =>
                                  update({
                                    candidates: model.candidates.map((x, j) =>
                                      j === i
                                        ? {
                                            ...x,
                                            [k]:
                                              k === "maximum" &&
                                              e.target.value === ""
                                                ? null
                                                : e.target.value,
                                          }
                                        : x,
                                    ),
                                  })
                                }
                              />
                            </td>
                          ))}
                          <td>
                            <input
                              aria-label={`Supplier ${i + 1} eligible`}
                              type="checkbox"
                              checked={c.eligible}
                              onChange={(e) =>
                                update({
                                  candidates: model.candidates.map((x, j) =>
                                    j === i
                                      ? { ...x, eligible: e.target.checked }
                                      : x,
                                  ),
                                })
                              }
                            />
                          </td>
                          <td>
                            <button
                              disabled={model.candidates.length <= 1}
                              onClick={() =>
                                update({
                                  candidates: model.candidates.filter(
                                    (_, j) => j !== i,
                                  ),
                                })
                              }
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="actions">
                  <button
                    disabled={model.candidates.length >= 40}
                    onClick={() =>
                      update({ candidates: [...model.candidates, candidate()] })
                    }
                  >
                    Add candidate supplier
                  </button>
                </div>
                {error !== undefined && <ErrorNotice error={error} />}
              </section>
            </>
          )}
          {step == 3 && (
            <>
              <section className="panel padded">
                <p className="eyebrow">03 / Allocation rules</p>
                <h2>Set your constraints</h2>
                <div className="constraint-grid">
                  <div className="dependency-control">
                    <label>
                      Maximum supplier dependency
                      <input
                        type="range"
                        min="1"
                        max="100"
                        step="1"
                        value={Number(model.dependency_pct) || 1}
                        onChange={(e) =>
                          update({ dependency_pct: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Dependency %
                      <input
                        inputMode="decimal"
                        value={model.dependency_pct}
                        onChange={(e) =>
                          update({ dependency_pct: e.target.value })
                        }
                      />
                    </label>
                    <small>
                      No selected supplier can exceed this share of demand.
                    </small>
                  </div>
                  <div className="filter-grid">
                    {(["min_suppliers", "max_suppliers"] as const).map((k) => (
                      <label key={k}>
                        {label(k)}
                        <input
                          type="number"
                          min="1"
                          max="40"
                          value={model[k]}
                          onChange={(e) =>
                            update({ [k]: Number(e.target.value) })
                          }
                        />
                      </label>
                    ))}
                  </div>
                </div>
              </section>
            </>
          )}
          <div className="actions">
            {step > 1 && (
              <button onClick={() => setStep(step - 1)}>Back</button>
            )}
            {step < 4 && (
              <button className="primary" onClick={() => go(step + 1)}>
                Continue
              </button>
            )}
          </div>
          {step === 4 && (
            <>
              <section className="panel padded">
                <h2>Optimize and compare</h2>
                <p>
                  {model.title} · {model.demand} {model.units} · maximum
                  dependency {model.dependency_pct}%
                </p>
                <button
                  disabled={busy}
                  className="primary"
                  onClick={() => void run()}
                >
                  Run optimization
                </button>
                <button onClick={() => setStep(3)}>Change constraints</button>
                {result?.feasible && (
                  <button disabled={busy} onClick={() => void run(true)}>
                    Save Strategy
                  </button>
                )}
                {error !== undefined && <ErrorNotice error={error} />}
              </section>
              {result && (
                <section className="panel padded">
                  <div className="section-heading">
                    <h2>Solver outcome: {label(str(result.status))}</h2>
                    <Badge variant="outline">{label(str(result.status))}</Badge>
                  </div>
                  <p>
                    {result.objective_gbp != null
                      ? `Modelled cost ${money(str(result.objective_gbp))}`
                      : "No validated allocation available."}
                  </p>
                  <p className="muted small">{str(result.limitation)}</p>
                  {((result.explanations as string[]) || []).map((s) => (
                    <p key={s}>{s}</p>
                  ))}
                  {Boolean(result.feasible) && (
                    <>
                      <div
                        className="allocation-bar"
                        aria-label="Supplier allocation shares"
                      >
                        {(result.allocations as Row[])
                          .filter((r) => Number(r.share_pct) > 0)
                          .map((r, i) => (
                            <div
                              key={str(r.name)}
                              style={{
                                width: `${Number(r.share_pct)}%`,
                                background: `var(--chart-${(i % 4) + 1})`,
                              }}
                              title={`${str(r.name)}: ${str(r.share_pct)}%`}
                            >
                              {Number(r.share_pct) >= 10
                                ? `${Number(r.share_pct).toFixed(1)}%`
                                : ""}
                            </div>
                          ))}
                      </div>

                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Supplier</th>
                              <th>Allocation</th>
                              <th>Share</th>
                              <th>Modelled cost</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(result.allocations as Row[]).map((r) => (
                              <tr key={str(r.name)}>
                                <td>{str(r.name)}</td>
                                <td>{str(r.allocation)}</td>
                                <td>{str(r.share_pct)}%</td>
                                <td>{money(str(r.modelled_cost))}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <h3>Binding constraints</h3>
                      {(result.binding_constraints as string[]).map((s) => (
                        <p key={s}>{s}</p>
                      ))}
                    </>
                  )}
                  <details>
                    <summary>Solver validation</summary>
                    <RecordFields value={result.validation as Row} />
                  </details>
                  <button
                    onClick={() =>
                      saveJson(
                        { assumptions: model, result },
                        "procureiq_optimization.json",
                      )
                    }
                  >
                    Export assumptions & result
                  </button>
                </section>
              )}
              {comparison.length > 0 && (
                <section className="panel padded">
                  <h2>Compare configurations</h2>
                  {comparison
                    .filter(
                      (r) =>
                        r.assumptions.units === model.units &&
                        r.assumptions.demand === model.demand &&
                        JSON.stringify(
                          r.assumptions.candidates.map((c) => c.name),
                        ) ===
                          JSON.stringify(model.candidates.map((c) => c.name)),
                    )
                    .map((r, i) => (
                      <article className="comparison-card" key={i}>
                        <h3>{r.title}</h3>
                        <small>
                          {str(r.result.status)} · Dependency cap{" "}
                          {r.assumptions.dependency_pct}% · Suppliers{" "}
                          {r.assumptions.min_suppliers}–
                          {r.assumptions.max_suppliers}
                        </small>
                        <p>
                          {((r.result.allocations as Row[]) || [])
                            .map(
                              (a) =>
                                `${str(a.name)}: ${str(a.allocation)} (${str(a.share_pct)}%)`,
                            )
                            .join(" · ")}
                        </p>
                        <details>
                          <summary>
                            Exact assumptions and constraint differences
                          </summary>
                          <RecordFields
                            value={r.assumptions as unknown as Row}
                          />
                        </details>
                        <strong>
                          {" "}
                          {r.result.objective_gbp == null
                            ? "No feasible objective"
                            : money(str(r.result.objective_gbp))}
                        </strong>
                      </article>
                    ))}
                  <small>
                    Only runs with matching units, demand and supplier names are
                    shown. Review all commercial assumptions before comparing
                    costs. Differences are modelled costs, not verified
                    procurement savings.
                  </small>
                </section>
              )}
            </>
          )}
        </>
      )}
      {view === "saved" && (
        <section className="panel padded">
          <h2>Saved Strategies</h2>
          <ReadState
            pending={runs.isPending}
            error={runs.error}
            retry={() => void runs.refetch()}
          />
          {runs.data && (
            <>
              <Pagination
                offset={offset}
                total={runs.data.total}
                onChange={setOffset}
              />
              {runs.data.items.map((r) => (
                <article className="saved-run" key={str(r.run_id)}>
                  <button
                    onClick={async () => {
                      try {
                        const saved = await request<{
                          assumptions: Model;
                          result: Row;
                        }>(`/strategy/optimization/runs/${str(r.run_id)}`);
                        setComparison((c) => [
                          ...c.slice(-5),
                          {
                            title: saved.assumptions.title,
                            result: saved.result,
                            assumptions: saved.assumptions,
                          },
                        ]);
                        setStep(4);
                        setView("builder");
                        setModel(saved.assumptions);
                        setResult(saved.result);
                      } catch (e) {
                        setError(e);
                      }
                    }}
                  >
                    Load / copy #{str(r.run_id)}
                  </button>{" "}
                  <span>{str(r.title)}</span>
                  <Badge variant="outline">{str(r.status)}</Badge>
                </article>
              ))}
              {!runs.data.total && <p>No saved solver results yet.</p>}
            </>
          )}
        </section>
      )}
    </>
  );
}

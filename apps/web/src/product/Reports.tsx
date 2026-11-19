import type { Page, Case } from "../api/types";
import { caseTitle, isDemo } from "../lib/presentation";
import { Badge } from "../components/ui/badge";
import { FileText, Presentation, Sheet } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { request } from "../api/client";
import { useScenario } from "./Strategy";
import {
  useScope,
  ScopeFilters,
  Metrics,
  str,
  RecordFields,
  download,
  useData,
  ReadState,
} from "./shared";
import type { Row } from "./shared";
import { ErrorNotice } from "../components/Common";
export function Reports() {
  const scope = useScope();
  const cases = useData<Page<Case>>("/investigations/cases?limit=100");
  const [search, setSearch] = useState("");
  const [step, setStep] = useState(1);
  const [insights, setInsights] = useState(true);
  const [recommendations, setRecommendations] = useState(true);
  const [findings, setFindings] = useState(true);
  const [slide, setSlide] = useState(0);
  const { state } = useScenario();
  const [include, setInclude] = useState(false);
  const [params] = useSearchParams();
  const [caseIds, setCaseIds] = useState(params.get("case") || "");
  const [result, setResult] = useState<Row>();
  const [basis, setBasis] = useState("");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setResult(undefined);
    setBasis("");
  }, [scope.reporting]);
  function body() {
    return {
      include_insights: insights,
      include_recommendations: recommendations,
      include_findings: findings,
      expected_content_hash: result
        ? str((result.brief as Row).content_hash)
        : undefined,
      filters: Object.fromEntries(
        [...new URLSearchParams(scope.reporting)].map(([k, v]) => [
          k,
          k === "supplier_id" ? Number(v) : v,
        ]),
      ),
      scenario: include ? state.result?.document : null,
      case_ids: caseIds ? caseIds.split(",").map((x) => Number(x.trim())) : [],
      expected_fingerprint: basis || undefined,
    };
  }
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError(undefined);
    try {
      await fn();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Reports</p>
          <h1>Executive evidence & decisions</h1>
          <p className="muted">
            Deterministic recommendations and editable five-slide presentations.
          </p>
        </div>
      </div>
      <div className="workflow-path">
        {["Choose scope", "Include evidence", "Preview and export"].map(
          (t, i) => (
            <button
              key={t}
              className={step === i + 1 ? "current" : ""}
              disabled={i === 2 && !result}
              onClick={() => setStep(i + 1)}
            >
              {i + 1} · {t}
            </button>
          ),
        )}
      </div>
      {step === 1 && (
        <section className="panel padded">
          <h2>Choose reporting scope</h2>
          <ScopeFilters />
          <p>
            {scope.reporting
              ? [...new URLSearchParams(scope.reporting)]
                  .map(([k, v]) => `${k.replaceAll("_", " ")}: ${v}`)
                  .join(" · ")
              : "All active disclosed payments"}
          </p>
          <p>
            Source compatibility is checked at preview and again at download.
          </p>
          <button
            className="primary"
            disabled={scope.invalid}
            onClick={() => setStep(2)}
          >
            Continue to evidence
          </button>
        </section>
      )}
      {step === 2 && (
        <section className="panel padded report-config">
          <p className="eyebrow">Report configuration</p>
          <h2>Choose the decision context</h2>
          <div className="content-chips">
            {[
              ["Key spending insights", insights, setInsights],
              [
                "Recommended investigations",
                recommendations,
                setRecommendations,
              ],
              ["Analyst-recorded findings", findings, setFindings],
            ].map(([title, checked, setter]) => (
              <label className="check" key={String(title)}>
                <input
                  type="checkbox"
                  checked={Boolean(checked)}
                  onChange={(e) => {
                    (setter as (v: boolean) => void)(e.target.checked);
                    setResult(undefined);
                  }}
                />
                {String(title)}
              </label>
            ))}
            <Badge variant="secondary">Observed expenditure</Badge>
            <Badge variant="secondary">Ranked review evidence</Badge>
            {include && <Badge variant="outline">Hypothetical scenario</Badge>}
            {caseIds && <Badge variant="outline">Investigation context</Badge>}
          </div>
          <label className="check">
            <input
              type="checkbox"
              disabled={!state.result?.document || state.stale}
              checked={include}
              onChange={(e) => {
                setInclude(e.target.checked);
                setResult(undefined);
              }}
            />
            Include the reviewed compatible hypothetical scenario
          </label>
          <p className="small muted">
            A scenario must be calculated in Strategy Studio and independently
            pass scope/source compatibility checks.
          </p>
          <details>
            <summary>Select saved investigations</summary>
            <ReadState
              pending={cases.isPending}
              error={cases.error}
              retry={() => void cases.refetch()}
            />
            <label>
              Search loaded saved investigations
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <p className="muted small">
              Only cases matching this exact scope and source can be included.
              The server checks compatibility when you preview.
            </p>
            {cases.data?.items
              .filter((c) =>
                `${c.case_reference} ${caseTitle(c)}`
                  .toLowerCase()
                  .includes(search.toLowerCase()),
              )
              .map((c) => (
                <label className="check case-selection" key={c.case_id}>
                  <input
                    type="checkbox"
                    checked={caseIds
                      .split(",")
                      .map((x) => x.trim())
                      .includes(String(c.case_id))}
                    onChange={(e) => {
                      const ids = caseIds
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean)
                        .filter((x) => x !== String(c.case_id));
                      if (e.target.checked) ids.push(String(c.case_id));
                      setCaseIds(ids.join(","));
                      setResult(undefined);
                    }}
                  />
                  <span>
                    {c.case_reference} · {caseTitle(c)}{" "}
                    {isDemo(c) && <Badge variant="outline">Demo</Badge>}
                  </span>
                </label>
              ))}
            <small>
              Showing up to 100 saved records. Other IDs can be entered below.
            </small>
          </details>
          <details>
            <summary>Exact case-ID fallback</summary>
            <label>
              Investigation IDs to include (optional, comma separated)
              <input
                value={caseIds}
                onChange={(e) => {
                  setCaseIds(e.target.value);
                  setResult(undefined);
                }}
                placeholder="Exact-scope cases only"
              />
            </label>
          </details>
          <button
            disabled={busy || scope.invalid}
            className="primary"
            onClick={() =>
              void action(async () => {
                const r = await request<Row>("/reports/preview", undefined, {
                  ...body(),
                  expected_fingerprint: undefined,
                  expected_content_hash: undefined,
                });
                setResult(r);
                setStep(3);
                setSlide(0);
                setBasis(str((r.brief as Row).source_fingerprint));
              })
            }
          >
            Review executive brief
          </button>
          {error !== undefined && <ErrorNotice error={error} />}
        </section>
      )}
      {result && step === 3 && (
        <section className="panel padded">
          <h2>Executive review · {str((result.brief as Row).period)}</h2>
          <Metrics row={(result.brief as Row).overview as Row} />
          <div className="report-basis">
            <Badge variant="outline">Source checked at preview</Badge>
            <small>{str((result.brief as Row).period)}</small>
          </div>
          <h3>Included in report</h3>
          <p>
            {insights ? "Disclosed-payment insights · " : ""}
            {recommendations ? "Recommended investigations · " : ""}
            {caseIds ? "Selected saved cases · " : ""}
            {findings && caseIds ? "Analyst findings · " : ""}
            {include ? "Hypothetical scenario" : "No financial scenario"}
          </p>
          <PresentationPreview
            model={result.presentation as Row}
            selected={slide}
            onSelect={setSlide}
          />
          <h3>Key Spending Insights</h3>
          <ul className="executive-findings">
            {((result.brief as Row).findings as string[]).map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
          <h3>Recommended investigations</h3>
          {((result.brief as Row).recommendations as Row[]).map((r, i) => (
            <article className="recommendation-card" key={i}>
              <h3>{str(r.title)}</h3>
              <p>
                Priority {str(r.priority_score)} · Exposure{" "}
                {str(r.positive_exposure_gbp)} GBP
              </p>

              <p>{str(r.observed_evidence)}</p>
              <p>{str(r.recommended_action)}</p>
              <details>
                <summary>Evidence and limitations</summary>
                <RecordFields value={r} />
              </details>
            </article>
          ))}
          <p className="notice">{str((result.brief as Row).caveat)}</p>
          {result.scenario && (
            <>
              <h3>Hypothetical scenario, not realized savings</h3>
              <RecordFields value={(result.scenario as Row).outputs as Row} />
            </>
          )}
          {((result.brief as Row).investigation_context as Row[])?.map(
            (c, i) => (
              <details key={i}>
                <summary>
                  Included case context ·{" "}
                  {str(c.case_reference) || str(c.case_id)}
                </summary>
                <RecordFields value={c} />
              </details>
            ),
          )}
          <h3>Generate deliverables</h3>
          <div className="export-grid">
            <div className="export-card">
              <Presentation size={24} />
              <h3>Executive presentation</h3>
              <p>Five editable slides · PowerPoint</p>
              <button
                className="primary"
                disabled={busy}
                onClick={() =>
                  void action(() =>
                    download(
                      "/reports/download/pptx",
                      body(),
                      "procureiq_executive.pptx",
                    ),
                  )
                }
              >
                Download Presentation
              </button>
            </div>
            <div className="export-card">
              <FileText size={24} />
              <h3>Evidence package</h3>
              <p>Complete source basis · JSON</p>
              <button
                disabled={busy}
                onClick={() =>
                  void action(() =>
                    download(
                      "/reports/download/json",
                      body(),
                      "procureiq_evidence.json",
                    ),
                  )
                }
              >
                Download evidence JSON
              </button>
            </div>
            {include && (
              <div className="export-card">
                <Sheet size={24} />
                <h3>Financial model</h3>
                <p>Formula-driven workbook · Excel</p>
                <button
                  disabled={busy}
                  onClick={() =>
                    void action(() =>
                      download(
                        "/strategy/excel",
                        { document: state.result?.document },
                        "procureiq_scenario.xlsx",
                      ),
                    )
                  }
                >
                  Download financial Excel
                </button>
              </div>
            )}
          </div>
          <p className="small muted">
            {str((result.brief as Row).attribution)}
          </p>
        </section>
      )}
    </>
  );
}

function PresentationPreview({
  model,
  selected,
  onSelect,
}: {
  model: Row;
  selected: number;
  onSelect: (i: number) => void;
}) {
  const [zoom, setZoom] = useState(false);
  const slides = (model?.slides as Row[]) || [];
  const shapes = (slides[selected]?.shapes as Row[]) || [];
  return (
    <section>
      <h3>Five-slide presentation preview</h3>
      <p className="small muted">{str(model?.rendering)}</p>
      <div className="actions">
        {slides.map((_, i) => (
          <button
            key={i}
            aria-pressed={selected === i}
            onClick={() => onSelect(i)}
          >
            Slide {i + 1}
          </button>
        ))}
      </div>
      <button onClick={() => setZoom(!zoom)}>
        {zoom ? "Fit slide to workspace" : "Enlarge slide for reading"}
      </button>
      <div className="slide-preview-scroll">
        <svg
          style={{ minWidth: zoom ? 1000 : undefined }}
          className="presentation-preview"
          viewBox={`0 0 ${str(model.width)} ${str(model.height)}`}
          role="img"
          aria-label={`Generated slide ${selected + 1}`}
        >
          <rect width="100%" height="100%" fill="white" />
          {shapes.map((s, i) => (
            <foreignObject
              key={i}
              x={Number(s.x)}
              y={Number(s.y)}
              width={Number(s.width)}
              height={Number(s.height)}
            >
              <div
                style={{
                  color: "#17324D",
                  fontFamily: "Arial, sans-serif",
                  fontSize: Number(s.font_size || 12),
                  fontWeight: s.bold ? 700 : 400,
                  whiteSpace: "pre-wrap",
                  height: "100%",
                  overflow: "hidden",
                  lineHeight: 1.15,
                }}
              >
                {s.kind === "text" ? (
                  str(s.text)
                ) : s.kind === "table" ? (
                  <table className="slide-table">
                    <tbody>
                      {(s.rows as string[][]).map((row, j) => (
                        <tr key={j}>
                          {row.map((cell, k) => (
                            <td
                              key={k}
                              style={{
                                background:
                                  j === 0
                                    ? "#17324D"
                                    : j % 2
                                      ? "#EEF3F8"
                                      : "white",
                                color: j === 0 ? "white" : "#17324D",
                              }}
                            >
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div>
                    {(s.categories as string[]).map((c, j) => (
                      <div key={j} style={{ marginBottom: 10, fontSize: 11 }}>
                        {c}
                        <div
                          style={{
                            background: "#2166AC",
                            height: 18,
                            width: `${(Number((s.values as number[])[j]) / Math.max(...(s.values as number[]))) * 100}%`,
                          }}
                        />
                        <span>
                          {Number((s.values as number[])[j]).toFixed(2)} £m
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </foreignObject>
          ))}
        </svg>
      </div>
    </section>
  );
}

import { Hint } from "./Design";
import type { Review } from "../api/types";
import { money, score, label } from "../format";
import { Fields, StatusBadge } from "./Common";
export function ReviewDetail({ review: r }: { review: Review }) {
  return (
    <>
      <p className="eyebrow">{label(r.opportunity_type)}</p>
      <h2>{r.title}</h2>
      <div className="measurements">
        <div>
          <small>Original review priority</small>
          <strong title={r.priority_score}>
            {score(r.priority_score)} <small>/ 100</small>
          </strong>
        </div>
        <div>
          <Hint text="Published payment exposure. This is not a potential savings estimate.">
            <small>Observed positive exposure</small>
          </Hint>
          <strong>{money(r.positive_exposure_gbp)}</strong>
        </div>
      </div>
      <div className="summary-strip">
        <span>
          <small>Source evidence</small>
          <strong>{r.primary_count.toLocaleString()}</strong>
        </span>
        {Object.entries(r.metrics || {})
          .filter(
            ([k, v]) =>
              [
                "supplier_count",
                "positive_supplier_count",
                "positive_expense_areas",
                "resolved_supplier_count",
                "expense_area_count",
                "area_count",
              ].includes(k) && typeof v !== "object",
          )
          .map(([k, v]) => (
            <span key={k}>
              <small>{label(k)}</small>
              <strong>{String(v)}</strong>
            </span>
          ))}
      </div>
      <p className="muted small">
        Exposure is not savings. Priority is not a probability of inefficiency.
      </p>
      {r.existing_case && (
        <p>
          <StatusBadge status={r.existing_case.status} />{" "}
          {r.existing_case.case_reference}
        </p>
      )}
      <section>
        <h3>Observed Evidence</h3>
        <p>{r.evidence_summary}</p>
        <p>
          {r.primary_count.toLocaleString()} primary ·{" "}
          {r.contextual_count.toLocaleString()} contextual source references
        </p>
        {r.metrics && (
          <details>
            <summary>Supporting measurements</summary>
            <Fields values={r.metrics} />
          </details>
        )}
      </section>
      <section>
        <h3>Why It Matters</h3>
        <p>{r.business_interpretation}</p>
        <small className="muted">
          Procurement hypothesis requiring investigation.
        </small>
      </section>
      <section>
        <h3>Suggested Investigation</h3>
        <p>{r.next_investigation_step}</p>
      </section>
      {r.caveats && (
        <details>
          <summary>Interpretation and limitations</summary>
          <ul>
            {r.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          <p>{r.exposure_definition}</p>
        </details>
      )}
    </>
  );
}

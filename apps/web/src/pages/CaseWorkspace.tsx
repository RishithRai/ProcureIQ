import { SectionHeader, MetricCard } from "../components/Design";
import { Badge } from "../components/ui/badge";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import { isDemo, caseTitle } from "../lib/presentation";
import { CaseWork, Lifecycle } from "../product/CaseWork";
import {
  Link,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useCase } from "../hooks/queries";
import { date, label, money, score } from "../format";
import {
  Loading,
  ErrorNotice,
  Historical,
  StatusBadge,
  Fields,
} from "../components/Common";
import { CaseEvidence } from "./CaseEvidence";
import { CaseActivity } from "./CaseActivity";
export function CaseWorkspace() {
  const { caseId = "" } = useParams();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const tab = ["overview", "evidence", "findings", "activity"].includes(
    params.get("tab") || "",
  )
    ? params.get("tab")!
    : "overview";
  const valid = /^[1-9]\d*$/.test(caseId) && Number.isSafeInteger(+caseId);
  const result = useCase(caseId, valid);
  if (!valid)
    return (
      <div className="notice" role="alert">
        Invalid case reference.{" "}
        <Link to="/investigations/cases">Browse Saved Cases</Link>
      </div>
    );
  if (result.isPending) return <Loading />;
  if (result.isError)
    return (
      <ErrorNotice error={result.error} retry={() => void result.refetch()} />
    );
  const c = result.data;
  const snapshot = c.review_snapshot;
  const reporting = new URLSearchParams(
    Object.entries(c.reporting_filters)
      .filter(([, v]) => v != null)
      .map(([k, v]) => [
        k,
        k.endsWith("month") ? String(v).slice(0, 7) : String(v),
      ]),
  ).toString();
  return (
    <>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/investigations/cases">Saved Cases</Link>
        <span>/</span>
        <span>{c.case_reference}</span>
      </nav>
      {location.state?.notice && (
        <div role="status" className="notice success">
          {String(location.state.notice)}
        </div>
      )}
      <SectionHeader
        eyebrow={`${c.case_reference} · ${label(c.opportunity_type)}`}
        title={caseTitle(c)}
        action={
          <div className="actions">
            {isDemo(c) && <Badge variant="outline">Demo</Badge>}
            <StatusBadge status={c.status} />
            <button
              className="primary"
              onClick={() =>
                setParams({
                  tab:
                    c.status === "REVIEWED" || c.status === "CLOSED"
                      ? "findings"
                      : "evidence",
                })
              }
            >
              Continue Investigation
            </button>
            <button onClick={() => void result.refetch()}>Refresh case</button>
          </div>
        }
      />
      {isDemo(c) && (
        <p className="demo-context">
          Demonstration case · saved content and audit history are preserved.
        </p>
      )}
      <div
        className={`case-hero-metrics ${tab !== "overview" ? "compact-case-metrics" : ""}`}
      >
        <MetricCard
          label="Observed exposure"
          value={
            typeof snapshot?.positive_exposure_gbp === "string"
              ? money(snapshot.positive_exposure_gbp)
              : "Not provided"
          }
          detail="Published payment context · not savings"
        />
        <MetricCard
          label="Investigation priority"
          value={`${score(c.original_score)} / 100`}
          detail="Original review ranking"
        />
        <MetricCard
          label="Evidence records"
          value={(c.primary_count + c.contextual_count).toLocaleString()}
          detail={`${c.primary_count.toLocaleString()} primary · ${c.contextual_count.toLocaleString()} contextual`}
        />
      </div>
      <Historical matches={c.basis_matches_current_source} />
      <details className="case-tools">
        <summary>More actions</summary>
        <Link className="button" to={`/spend?${reporting}`}>
          Explore reporting scope
        </Link>
        <Link className="button" to={`/strategy/scenarios?${reporting}`}>
          Evaluate a hypothetical scenario
        </Link>
        <Link
          className="button"
          to={`/strategy/optimization?context=${encodeURIComponent(c.case_reference)}`}
        >
          Define sourcing assumptions
        </Link>
        <Link className="button" to={`/reports?${reporting}&case=${c.case_id}`}>
          Include in executive review
        </Link>
      </details>
      <div className="case-layout">
        <section className="panel case-main">
          <Tabs value={tab} onValueChange={(tab) => setParams({ tab })}>
            <TabsList
              className="case-tabs"
              variant="line"
              aria-label="Case sections"
            >
              {["overview", "evidence", "findings", "activity"].map((t) => (
                <TabsTrigger key={t} value={t}>
                  {label(t)}
                </TabsTrigger>
              ))}
            </TabsList>
            <TabsContent value={tab} className="case-content">
              {tab === "overview" ? (
                <>
                  <h2>Investigation brief</h2>
                  <div className="case-overview-grid">
                    <section>
                      <h3>Investigation objective</h3>
                      <p>{c.objective}</p>
                      {isDemo(c) && (
                        <details>
                          <summary>Original saved title</summary>
                          <p>{c.title}</p>
                        </details>
                      )}
                    </section>
                    <section>
                      <h3>Observed evidence</h3>
                      <p>
                        {String(
                          snapshot?.evidence_summary ||
                            "See frozen evidence records.",
                        )}
                      </p>
                    </section>
                    <section>
                      <h3>Procurement hypothesis</h3>
                      <p>
                        {String(
                          snapshot?.business_interpretation || "Not provided",
                        )}
                      </p>
                    </section>
                    <section>
                      <h3>Recommended action</h3>
                      <p>
                        {String(
                          snapshot?.next_investigation_step || "Not provided",
                        )}
                      </p>
                    </section>
                  </div>
                  {snapshot?.metrics &&
                    typeof snapshot.metrics === "object" &&
                    !Array.isArray(snapshot.metrics) && (
                      <details>
                        <summary>Original measurements</summary>
                        <Fields values={snapshot.metrics} />
                      </details>
                    )}
                  {c.closure_explanation && (
                    <p>
                      {label(c.disposition || "Closed")}:{" "}
                      {c.closure_explanation}
                    </p>
                  )}
                  <button onClick={() => setParams({ tab: "evidence" })}>
                    Inspect frozen evidence
                  </button>
                </>
              ) : tab === "evidence" ? (
                <CaseEvidence
                  key={caseId}
                  id={caseId}
                  closed={c.status === "CLOSED"}
                />
              ) : tab === "findings" ? (
                <CaseWork id={caseId} closed={c.status === "CLOSED"} />
              ) : (
                <CaseActivity key={caseId} id={caseId} />
              )}
            </TabsContent>
          </Tabs>
        </section>
        <aside className="panel context">
          <h2>Investigation progress</h2>
          <Lifecycle record={c} />
          <p>
            {c.work_counts?.bookmarks ?? 0} bookmarked records ·{" "}
            {c.work_counts?.finding ?? 0} findings · {c.work_counts?.note ?? 0}{" "}
            notes
          </p>
          <dl>
            <dt>Review type</dt>
            <dd>{label(c.opportunity_type)}</dd>
            <dt>Created</dt>
            <dd>{date(c.created_at)}</dd>
            <dt>Last updated</dt>
            <dd>{date(c.updated_at)}</dd>
            <dt>Source basis</dt>
            <dd>
              {c.basis_matches_current_source
                ? "Matches current source"
                : "Historical Evidence Basis"}
            </dd>
          </dl>
          <details>
            <summary>Original source identity</summary>
            <p className="hash">{c.source_fingerprint}</p>
            <p>{c.rule_version}</p>
            <Fields values={c.reporting_filters} />
            <p className="small">Configuration identity</p>
            <p className="hash">{c.configuration_identity}</p>
          </details>
        </aside>
      </div>
    </>
  );
}

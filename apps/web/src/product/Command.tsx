import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  ScanSearch,
  Database,
  Wallet,
  Activity,
  ShieldCheck,
} from "lucide-react";
import { useData, str, ReadState } from "./shared";
import type { Row, DataPage } from "./shared";
import type { Reviews, Case, Page } from "../api/types";
import {
  SectionHeader,
  MetricCard,
  Panel,
  EmptyState,
  CaseCard,
  ActionLink,
} from "../components/Design";
import { Button } from "../components/ui/button";
import { StatusBadge } from "../components/Common";
import { money, label, date, score } from "../format";
export function Command() {
  const data = useData<{
    overview: Row[];
    months: Row[];
    case_counts: Record<string, number>;
    activity: Row[];
  }>("/command");
  const reviews = useData<Reviews>("/investigations/reviews?limit=4");
  const runs = useData<DataPage>("/operations/runs?limit=1", true, 3000);
  const cases = useData<Page<Case>>("/investigations/cases?limit=50");
  const visible = cases.data?.items || [];
  const counts = data.data?.case_counts || {};
  const totalCases = Object.values(counts).reduce((a, b) => a + b, 0);
  const activeCount =
    (counts.OPEN || 0) + (counts.INVESTIGATING || 0) + (counts.REVIEWED || 0);
  const active = visible.filter((c) => c.status !== "CLOSED");
  const latest = runs.data?.items[0];
  const activity = data.data?.activity || [];
  return (
    <>
      <SectionHeader
        eyebrow="Your decision workspace"
        title="Procurement workspace"
        description="Investigate spending, review opportunities and evaluate sourcing decisions."
        action={
          <Button asChild>
            <Link to="/investigations/reviews">
              Review opportunities <ArrowUpRight size={16} />
            </Link>
          </Button>
        }
      />
      <ReadState
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <>
          <div className="metric-grid">
            <MetricCard
              accent
              label="Positive disclosed expenditure"
              value={
                <span title={money(str(data.data.overview[0]?.positive_gbp))}>
                  {new Intl.NumberFormat("en-GB", {
                    style: "currency",
                    currency: "GBP",
                    notation: "compact",
                    maximumFractionDigits: 2,
                  }).format(Number(data.data.overview[0]?.positive_gbp))}
                </span>
              }
              detail={`${str(data.data.overview[0]?.record_count)} published lines · gross VAT-inclusive`}
              icon={<Wallet />}
            />
            <MetricCard
              label="Active investigations"
              value={String(activeCount)}
              detail="Open, investigating or reviewed · current workspace"
              icon={<BriefcaseBusiness />}
            />
            <MetricCard
              label="Review candidates"
              value={String(reviews.data?.qualified_count ?? "—")}
              detail={`${reviews.data?.exported_count ?? "—"} ranked reviews available`}
              icon={<ScanSearch />}
            />
            <MetricCard
              label="Latest pipeline"
              value={latest ? label(str(latest.status)) : "Not run"}
              detail={
                latest
                  ? `${label(str(latest.operation))} · Run #${str(latest.run_id)}`
                  : "No recorded execution"
              }
              icon={<Database />}
            />
          </div>
          <div className="dashboard-grid">
            <div className="dashboard-main">
              {totalCases > 0 ? (
                <Panel
                  title={
                    activeCount
                      ? "Investigations to continue"
                      : "Completed work"
                  }
                >
                  <ReadState
                    pending={cases.isPending}
                    error={cases.error}
                    retry={() => void cases.refetch()}
                  />
                  {active.length ? (
                    <div className="case-grid">
                      {active.slice(0, 4).map((c) => (
                        <CaseCard key={c.case_id} record={c} />
                      ))}
                    </div>
                  ) : (
                    <p>
                      {activeCount
                        ? "Open Saved Cases to continue your active investigations."
                        : "All investigations are closed. Revisit findings or select another procurement review."}
                    </p>
                  )}
                  <ActionLink to="/investigations/cases">
                    All investigations
                  </ActionLink>
                </Panel>
              ) : (
                <Panel title="Start with a procurement review">
                  <ol className="workflow-steps">
                    <li>Select a review</li>
                    <li>Investigate evidence</li>
                    <li>Evaluate possible actions</li>
                  </ol>
                </Panel>
              )}
              <Panel
                title="Priority procurement reviews"
                action={
                  <ActionLink to="/investigations/reviews">
                    View all reviews
                  </ActionLink>
                }
              >
                <ReadState
                  pending={reviews.isPending}
                  error={reviews.error}
                  retry={() => void reviews.refetch()}
                />
                <div className="review-tiles">
                  {reviews.data?.items.map((r) => (
                    <Link
                      className="review-tile"
                      key={r.opportunity_id}
                      to={`/investigations/reviews?review=${r.opportunity_id}`}
                    >
                      <div className="case-card-top">
                        <span className="review-kind">
                          {label(r.opportunity_type)}
                        </span>
                        <span className="priority-pill">
                          {score(r.priority_score)}
                        </span>
                      </div>
                      <h3>{r.title.replace(/ review:/, ":")}</h3>
                      <strong>{money(r.positive_exposure_gbp)}</strong>
                      <footer>
                        <span>Observed exposure · not savings</span>
                        <ArrowUpRight size={15} />
                      </footer>
                    </Link>
                  ))}
                </div>
              </Panel>
            </div>
            <div className="dashboard-main">
              {totalCases > 0 && (
                <Panel
                  title="Recent activity"
                  action={<Activity size={17} className="muted" />}
                >
                  {activity.length ? (
                    <ol className="activity-feed">
                      {activity.slice(0, 5).map((e) => (
                        <li key={str(e.event_id)}>
                          <span className="event-icon">
                            <BriefcaseBusiness size={14} />
                          </span>
                          <div>
                            <p>
                              <Link
                                to={`/investigations/cases/${str(e.case_id)}?tab=activity`}
                              >
                                {label(str(e.event_type))}
                              </Link>
                            </p>
                            <small>
                              {str(e.case_reference)} ·{" "}
                              {date(str(e.occurred_at))}
                            </small>
                          </div>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <EmptyState
                      title="A clear starting point"
                      detail="Your case activity will appear here as investigations progress."
                    />
                  )}
                </Panel>
              )}
              <Panel
                title="Data operations"
                action={<ShieldCheck size={17} className="muted" />}
              >
                {latest ? (
                  <>
                    <div className="operation-summary">
                      <span className="operation-icon">
                        <Database size={22} />
                      </span>
                      <div>
                        <h3>{label(str(latest.operation))}</h3>
                        <StatusBadge status={str(latest.status)} />
                      </div>
                    </div>
                    <p className="muted small">
                      {latest.finished_at
                        ? `Completed ${date(str(latest.finished_at))}`
                        : "Execution is in progress"}
                    </p>
                    <ActionLink
                      to={`/data-operations/runs/${str(latest.run_id)}`}
                    >
                      Inspect run #{str(latest.run_id)}
                    </ActionLink>
                  </>
                ) : (
                  <p className="muted">No pipeline runs recorded.</p>
                )}
                <div className="panel-bottom">
                  <span>Original source versions retained</span>
                  <ActionLink to="/data-operations">Operations</ActionLink>
                </div>
              </Panel>
              <Link className="strategy-callout" to="/strategy/scenarios">
                <span className="eyebrow">From evidence to decisions</span>
                <h3>What could change?</h3>
                <p>Model assumptions. Compare alternatives.</p>
                <span>
                  Open Strategy Studio <ArrowUpRight size={16} />
                </span>
              </Link>
            </div>
          </div>
        </>
      )}
    </>
  );
}

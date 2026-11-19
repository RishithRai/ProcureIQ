import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import { DetailDrawer } from "../components/Design";
import { Badge } from "../components/ui/badge";
import { MetricCard } from "../components/Design";
import { CheckCircle2, AlertCircle, Clock, Database } from "lucide-react";
import { label, date } from "../format";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { request } from "../api/client";
import { useData, str, RecordFields, ReadState } from "./shared";
import type { Row, DataPage } from "./shared";
import { ErrorNotice, Pagination } from "../components/Common";
export function Operations() {
  const [tab, setTab] = useState("overview");
  const [addSource, setAddSource] = useState(false);
  const [issue, setIssue] = useState<Row>();
  const [code, setCode] = useState("");
  const [severity, setSeverity] = useState("");
  const [month, setMonth] = useState("");
  const [search, setSearch] = useState("");
  const [sourceOffset, setSourceOffset] = useState(0);
  const [runOffset, setRunOffset] = useState(0);
  const sources = useData<DataPage>(
    `/operations/sources?offset=${sourceOffset}`,
    true,
    5000,
  );
  const manifests = useData<{ items: Row[] }>("/operations/manifests");
  const runs = useData<DataPage>(
    `/operations/runs?offset=${runOffset}`,
    true,
    2000,
  );
  const [qualityOffset, setQualityOffset] = useState(0);
  const [file, setFile] = useState("");
  const quality = useData<DataPage & { all_total: number; groups: Row[] }>(
    `/operations/quality?${new URLSearchParams(Object.entries({ offset: String(qualityOffset), file_id: file, issue_code: code, severity, reporting_month: month, search }).filter(([, v]) => v))}`,
  );
  const [manifest, setManifest] = useState("");
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  async function start(operation: string, source?: Row) {
    if (
      operation !== "verify" &&
      !window.confirm(
        operation === "activate"
          ? `Activate source ${str(source?.filename)} / ${str(source?.sha256)} after reviewing its lineage? Active analytics will change.`
          : "Register and ingest this controlled receipt manifest? Original versions remain retained; new versions remain inactive.",
      )
    )
      return;
    setBusy(true);
    setError(undefined);
    try {
      let registration: number | undefined;
      if (operation === "ingest") {
        const r = await request<Row>("/operations/registrations", undefined, {
          manifest_name: manifest,
        });
        registration = Number(r.registration_id);
      }
      const r = await request<Row>("/operations/runs", undefined, {
        operation,
        registration_id: registration,
        source_file_id: source?.file_id,
        expected_fingerprint: sources.data?.source_fingerprint,
        confirm_activation: operation === "activate",
      });
      setNotice(
        `Queued run #${str(r.run_id)}. Open the run to inspect actual stage outcomes.`,
      );
      void runs.refetch();
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
          <p className="eyebrow">Data Operations</p>
          <h1>Source integrity & pipeline execution</h1>
          <p className="muted">
            Controlled local receipts, immutable versions and recorded execution
            stages.
          </p>
        </div>
        <button
          className="primary"
          disabled={busy}
          onClick={() => void start("verify")}
        >
          Run read-only verification
        </button>
      </div>
      {notice && (
        <div role="status" className="notice">
          {notice}
        </div>
      )}
      {error !== undefined && <ErrorNotice error={error} />}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList
          className="operations-tabs-list"
          aria-label="Operations sections"
        >
          {["overview", "pipeline runs", "sources", "data quality"].map((t) => (
            <TabsTrigger value={t} key={t}>
              {label(t)}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="overview">
          <div className="metric-grid operations-metrics">
            <MetricCard
              label="Latest execution"
              value={label(str(runs.data?.items[0]?.status) || "No runs")}
              detail={
                runs.data?.items[0]
                  ? `Run #${str(runs.data.items[0].run_id)} · ${str(runs.data.items[0].operation)}`
                  : "Run verification to begin"
              }
              icon={<Clock size={18} />}
            />
            <MetricCard
              label="Retained source versions"
              value={sources.data ? String(sources.data.total) : "—"}
              detail="Original files remain immutable"
              icon={<Database size={18} />}
            />
            <MetricCard
              label="Recorded quality issues"
              value={quality.data ? String(quality.data.all_total) : "—"}
              detail="All retained source versions"
              icon={<AlertCircle size={18} />}
            />
          </div>
          <p>
            Last execution:{" "}
            {runs.data?.items[0]?.finished_at
              ? date(str(runs.data.items[0].finished_at))
              : "No completed run"}
            .
          </p>
          <button onClick={() => setTab("pipeline runs")}>
            Inspect pipeline outcomes
          </button>
          <button onClick={() => setTab("data quality")}>
            Explore quality warnings
          </button>
        </TabsContent>
        <TabsContent value="sources">
          <button className="primary" onClick={() => setAddSource(true)}>
            Add source
          </button>
        </TabsContent>
        {addSource && (
          <DetailDrawer title="Add source" onClose={() => setAddSource(false)}>
            <section className="panel padded">
              <h2>Register and process local sources</h2>
              <label>
                Controlled receipt manifest
                <select
                  value={manifest}
                  onChange={(e) => setManifest(e.target.value)}
                >
                  <option value="">Choose a manifest</option>
                  {manifests.data?.items.map((r) => (
                    <option key={str(r.name)} value={str(r.name)}>
                      {str(r.name)} · {str(r.source_count)} files
                    </option>
                  ))}
                </select>
              </label>
              <button
                disabled={!manifest || busy}
                onClick={() => void start("ingest")}
              >
                Register & ingest incrementally
              </button>
              <p className="small muted">
                Only verified acquisition receipts placed in the controlled
                local manifests directory are available. No browser file paths,
                shell commands or external URLs are accepted. New versions
                require separate explicit activation.
              </p>
            </section>
          </DetailDrawer>
        )}
        <TabsContent value="pipeline runs">
          <section className="panel padded">
            <h2>Recorded pipeline runs</h2>
            {runs.data && (
              <Pagination
                offset={runOffset}
                total={runs.data.total}
                onChange={setRunOffset}
              />
            )}
            <ReadState
              pending={runs.isPending}
              error={runs.error}
              retry={() => void runs.refetch()}
            />
            {runs.data?.items.map((r) => (
              <article className="pipeline-run-card" key={str(r.run_id)}>
                <Link to={`/data-operations/runs/${str(r.run_id)}`}>
                  Run #{str(r.run_id)} · {str(r.operation)} · {str(r.status)}
                </Link>{" "}
                <Badge variant="outline">{str(r.status)}</Badge>
                <small>
                  {label(str(r.current_stage))} ·{" "}
                  {r.finished_at ? date(str(r.finished_at)) : "Not finished"}
                </small>
              </article>
            ))}
            {runs.data?.total === 0 && (
              <p>
                No recorded runs yet. Run verification to create an actual
                execution record.
              </p>
            )}
          </section>
        </TabsContent>
        <TabsContent value="sources">
          <section className="panel padded">
            <h2>Source versions</h2>
            {sources.data && (
              <Pagination
                offset={sourceOffset}
                total={sources.data.total}
                onChange={setSourceOffset}
              />
            )}
            <ReadState
              pending={sources.isPending}
              error={sources.error}
              retry={() => void sources.refetch()}
            />
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Source</th>
                    <th>Version</th>
                    <th>Records</th>
                    <th>Validation</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.data?.items.map((r) => (
                    <tr key={str(r.file_id)}>
                      <td>{str(r.reporting_month).slice(0, 7)}</td>
                      <td>
                        <details>
                          <summary>{str(r.filename)}</summary>
                          <RecordFields value={r} />
                        </details>
                      </td>
                      <td>{r.active ? "Active" : "Inactive"}</td>
                      <td>{str(r.original_row_count)}</td>
                      <td>{label(str(r.import_status))} · ingestion checks</td>
                      <td>
                        <button
                          onClick={() => {
                            setFile(str(r.file_id));
                            setQualityOffset(0);
                            setTab("data quality");
                          }}
                        >
                          Quality details
                        </button>
                        {!r.active && (
                          <button
                            disabled={busy}
                            onClick={() => void start("activate", r)}
                          >
                            Review & activate
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </TabsContent>
        <TabsContent value="data quality">
          <section className="panel padded">
            <h2 id="quality-section">Recorded quality issues</h2>
            <div className="evidence-filters">
              <label>
                Issue type
                <select
                  value={code}
                  onChange={(e) => {
                    setCode(e.target.value);
                    setQualityOffset(0);
                  }}
                >
                  <option value="">All types</option>
                  {[
                    ...new Set(
                      quality.data?.groups?.map((g) => str(g.issue_code)),
                    ),
                  ].map((k) => (
                    <option key={k} value={k}>
                      {label(k)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Severity
                <select
                  value={severity}
                  onChange={(e) => {
                    setSeverity(e.target.value);
                    setQualityOffset(0);
                  }}
                >
                  <option value="">All severities</option>
                  {[
                    ...new Set(
                      quality.data?.groups?.map((g) => str(g.severity)),
                    ),
                  ].map((k) => (
                    <option key={k}>{k}</option>
                  ))}
                </select>
              </label>
              <label>
                Reporting month
                <input
                  type="month"
                  value={month}
                  onChange={(e) => {
                    setMonth(e.target.value);
                    setQualityOffset(0);
                  }}
                />
              </label>
              <label>
                Search issues
                <input
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setQualityOffset(0);
                  }}
                />
              </label>
            </div>
            <p>
              {quality.data?.total ?? "…"} matching of{" "}
              {quality.data?.all_total ?? "…"} recorded issues across retained
              versions. Warnings are review candidates, not proven payment
              errors.
            </p>
            <details>
              <summary>Counts by issue, severity and month</summary>
              {quality.data?.groups?.map((g, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setCode(str(g.issue_code));
                    setSeverity(str(g.severity));
                    setMonth(str(g.reporting_month).slice(0, 7));
                    setQualityOffset(0);
                  }}
                >
                  {label(str(g.issue_code))} · {str(g.severity)} ·{" "}
                  {str(g.reporting_month).slice(0, 7)}: {str(g.count)}
                </button>
              ))}
            </details>
            <button
              onClick={() => {
                setFile("");
                setCode("");
                setSeverity("");
                setMonth("");
                setSearch("");
                setQualityOffset(0);
              }}
            >
              All source versions
            </button>
            <ReadState
              pending={quality.isPending}
              error={quality.error}
              retry={() => void quality.refetch()}
            />
            {quality.data && (
              <>
                <Pagination
                  offset={qualityOffset}
                  total={quality.data.total}
                  onChange={setQualityOffset}
                />
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Issue</th>
                        <th>Severity</th>
                        <th>Month</th>
                        <th>Source record</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quality.data.items.map((r) => (
                        <tr key={str(r.issue_id)}>
                          <td>{label(str(r.issue_code))}</td>
                          <td>{str(r.severity)}</td>
                          <td>{str(r.reporting_month).slice(0, 7)}</td>
                          <td>{str(r.source_record_number)}</td>
                          <td>
                            <button onClick={() => setIssue(r)}>
                              Inspect issue
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
        </TabsContent>
      </Tabs>
      {issue && (
        <DetailDrawer
          title={label(str(issue.issue_code))}
          onClose={() => setIssue(undefined)}
        >
          <p>
            {label(str(issue.severity))} · reporting month{" "}
            {str(issue.reporting_month).slice(0, 7)} · source record{" "}
            {str(issue.source_record_number) || "File-level issue"}
          </p>
          <p>A recorded review warning is not a confirmed payment error.</p>
          <h3>Recorded issue evidence</h3>
          <RecordFields value={(issue.details as Row) || {}} />
          <details>
            <summary>Source identity and technical issue fields</summary>
            <RecordFields value={issue} />
          </details>
          {issue.raw_row_id && <IssueSource id={str(issue.raw_row_id)} />}
        </DetailDrawer>
      )}
    </>
  );
}
function IssueSource({ id }: { id: string }) {
  const data = useData<{ record: Row }>(`/spend/transactions/${id}`);
  return (
    <details>
      <summary>Original source record</summary>
      <ReadState
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && <RecordFields value={data.data.record} />}
    </details>
  );
}
export function PipelineRun() {
  const { runId = "" } = useParams();
  const data = useData<{ run: Row; stages: Row[] }>(
    `/operations/runs/${runId}`,
    true,
    1500,
  );
  const profile = data.data?.stages.find(
    (s) => s.name === "parsing_and_contracts",
  )?.output;
  const ingestion = data.data?.stages.find(
    (s) => s.name === "incremental_ingestion",
  )?.output;
  const receipt = data.data?.stages.find((s) => s.name === "source_validation")
    ?.output as Row | undefined;
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  return (
    <>
      <Link to="/data-operations">Data Operations</Link>
      <h1>Pipeline run #{runId}</h1>
      <ReadState
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <>
          <section className="panel padded">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{label(str(data.data.run.operation))}</p>
                <h2>{label(str(data.data.run.status))}</h2>
                <p className="muted">
                  {data.data.run.status === "succeeded"
                    ? "Final stage completed: "
                    : "Current stage: "}
                  {label(str(data.data.run.current_stage)) || "Awaiting worker"}
                </p>
              </div>
              <Badge variant="outline">{str(data.data.run.status)}</Badge>
            </div>
            <p>
              Total recorded stage duration:{" "}
              {data.data.stages
                .reduce((n, s) => n + Number(s.duration_ms || 0), 0)
                .toFixed(1)}{" "}
              ms. A successful run can verify already-ingested sources without
              adding records.
            </p>
            <div className="summary-strip">
              <span>
                <small>Manifest scope</small>
                <strong>
                  {receipt?.manifest
                    ? str(receipt.manifest)
                    : data.data.run.operation === "verify"
                      ? "Frozen acceptance baseline"
                      : "See source receipt"}
                </strong>
              </span>
              {Array.isArray(profile) && (
                <>
                  <span>
                    <small>Records profiled</small>
                    <strong>
                      {(profile as Row[])
                        .reduce((n, r) => n + Number(r.rows || 0), 0)
                        .toLocaleString()}
                    </strong>
                  </span>
                  <span>
                    <small>Profile issue records</small>
                    <strong>
                      {(profile as Row[])
                        .reduce(
                          (n, r) => n + Number(r.quality_issue_count || 0),
                          0,
                        )
                        .toLocaleString()}
                    </strong>
                  </span>
                </>
              )}
              {Array.isArray(ingestion) && (
                <>
                  <span>
                    <small>New source versions</small>
                    <strong>
                      {
                        (ingestion as Row[]).filter(
                          (r) => r.status === "loaded",
                        ).length
                      }
                    </strong>
                  </span>
                  <span>
                    <small>Already ingested, verified</small>
                    <strong>
                      {
                        (ingestion as Row[]).filter(
                          (r) => r.status === "verified_existing",
                        ).length
                      }
                    </strong>
                  </span>
                </>
              )}
              <span>
                <small>Failed stages</small>
                <strong>
                  {data.data.stages.filter((s) => s.status === "failed").length}
                </strong>
              </span>
            </div>
            {data.data.run.started_at && data.data.run.finished_at && (
              <p>
                Recorded execution duration:{" "}
                {(
                  (Date.parse(str(data.data.run.finished_at)) -
                    Date.parse(str(data.data.run.started_at))) /
                  1000
                ).toFixed(2)}{" "}
                seconds.
              </p>
            )}
            {data.data.run.error_summary && (
              <p role="alert">{str(data.data.run.error_summary)}</p>
            )}
            <details>
              <summary>Execution receipt & technical details</summary>
              <RecordFields value={data.data.run} />
            </details>
            {["failed", "interrupted"].includes(str(data.data.run.status)) &&
              data.data.run.operation !== "activate" && (
                <button
                  onClick={async () => {
                    try {
                      const r = await request<Row>(
                        `/operations/runs/${runId}/retry`,
                        undefined,
                        {},
                      );
                      setNotice(`Retry queued as run #${str(r.run_id)}`);
                    } catch (e) {
                      setError(e);
                    }
                  }}
                >
                  Retry with fresh validation
                </button>
              )}
            {notice && <p role="status">{notice}</p>}
            {error !== undefined && <ErrorNotice error={error} />}
          </section>
          <section className="panel padded">
            <h2>Actual stage outcomes</h2>
            <ol className="pipeline-timeline">
              {data.data.stages.map((s) => (
                <li key={str(s.stage_id)} className={`stage-${str(s.status)}`}>
                  <span className="stage-icon">
                    {s.status === "succeeded" ? (
                      <CheckCircle2 size={20} />
                    ) : s.status === "failed" ? (
                      <AlertCircle size={20} />
                    ) : (
                      <Clock size={20} />
                    )}
                  </span>
                  <div className="stage-content">
                    <div className="section-heading">
                      <h3>{label(str(s.name))}</h3>
                      <Badge variant="outline">{str(s.status)}</Badge>
                    </div>
                    <p className="muted small">
                      {s.duration_ms == null
                        ? "No duration recorded"
                        : `${Number(s.duration_ms).toFixed(1)} ms`}{" "}
                      · Started{" "}
                      {s.started_at ? date(str(s.started_at)) : "not recorded"}
                    </p>
                    {s.error && <p role="alert">{str(s.error)}</p>}
                    <details open={s.status === "failed"}>
                      <summary>
                        Validation output & recorded stage details
                      </summary>
                      <RecordFields value={s} />
                    </details>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </>
  );
}

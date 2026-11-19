import { date } from "../format";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { DetailDrawer } from "../components/Design";
import { Fields } from "../components/Common";
import type { EvidencePage } from "../api/types";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { request } from "../api/client";
import { useData, str, ReadState } from "./shared";
import type { Row, DataPage } from "./shared";
import { ErrorNotice, Pagination, Modal } from "../components/Common";
import type { Case } from "../api/types";
export function CaseWork({ id, closed }: { id: string; closed: boolean }) {
  const cache = useQueryClient();
  const [params] = useSearchParams();
  const initialCitation = params.get("citation")?.split(":");
  const [editor, setEditor] = useState(!!initialCitation);
  const [assessment, setAssessment] = useState("");
  const [nextStep, setNextStep] = useState("");
  const [view, setView] = useState("finding");
  const [offset, setOffset] = useState(0);
  const entries = useData<DataPage>(
    `/investigations/cases/${id}/entries?offset=${offset}`,
  );
  const [bookmarkOffset, setBookmarkOffset] = useState(0);
  const bookmarks = useData<DataPage>(
    `/investigations/cases/${id}/bookmarks?offset=${bookmarkOffset}`,
  );
  const [edit, setEdit] = useState<Row>();
  const [kind, setKind] = useState("finding");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [citations, setCitations] = useState<Row[]>(
    initialCitation
      ? [
          {
            classification: initialCitation[0],
            ordinal: Number(initialCitation[1]),
          },
        ]
      : [],
  );
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  async function save(deleted = false) {
    setBusy(true);
    setError(undefined);
    try {
      await request(
        `/investigations/cases/${id}/entries${edit ? "/" + str(edit.entry_id) : ""}`,
        undefined,
        {
          kind,
          title,
          content,
          sections:
            kind === "finding" ? { assessment, next_step: nextStep } : null,
          citations: kind === "finding" ? citations : [],
          expected_version: edit?.row_version ?? null,
          deleted,
        },
        edit ? "PATCH" : "POST",
      );
      toast.success(deleted ? "Entry removed" : "Analyst entry saved");
      setEditor(false);
      setEdit(undefined);
      setTitle("");
      setContent("");
      setCitations([]);
      setNotice(
        deleted
          ? "Entry deleted; prior content retained in activity."
          : "Analyst entry saved.",
      );
      await cache.invalidateQueries({ queryKey: ["product"] });
      await cache.invalidateQueries({ queryKey: ["activity", id] });
      await cache.invalidateQueries({ queryKey: ["case", id] });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="section-heading">
        <h2>Investigation notebook</h2>
        <button
          disabled={closed}
          className="primary"
          onClick={() => {
            setEdit(undefined);
            setTitle("");
            setContent("");
            setAssessment("");
            setNextStep("");
            setCitations([]);
            setKind(view);
            setEditor(true);
          }}
        >
          New {view === "finding" ? "Finding" : "Note"}
        </button>
      </div>
      <div className="actions">
        <button
          aria-pressed={view === "finding"}
          onClick={() => setView("finding")}
        >
          Findings
        </button>
        <button aria-pressed={view === "note"} onClick={() => setView("note")}>
          Notes
        </button>
      </div>
      <p className="muted">
        Analyst-recorded observations and conclusions. These do not establish
        verified savings.
      </p>
      {notice && <p role="status">{notice}</p>}
      <ReadState
        pending={entries.isPending}
        error={entries.error}
        retry={() => void entries.refetch()}
      />
      {entries.data && (
        <>
          {entries.data.items
            .filter((e) => e.kind === view)
            .map((e) => (
              <article className="panel padded" key={str(e.entry_id)}>
                <p className="eyebrow">
                  {str(e.kind)} · revision {str(e.row_version)}
                </p>
                <h3>{str(e.title)}</h3>
                <small className="muted">
                  Created{" "}
                  {e.created_at ? date(str(e.created_at)) : "Not recorded"} ·
                  Updated{" "}
                  {e.updated_at ? date(str(e.updated_at)) : "Not recorded"}
                </small>
                <p className="whitespace-pre-wrap">{str(e.content)}</p>
                {e.sections && (
                  <>
                    <h4>Assessment</h4>
                    <p>
                      {str((e.sections as Row).assessment) ||
                        "Preliminary — not yet assessed"}
                    </p>
                    <h4>Recommended next step</h4>
                    <p>
                      {str((e.sections as Row).next_step) || "Not yet recorded"}
                    </p>
                  </>
                )}
                <small>
                  {((e.citations as Row[]) || []).length} evidence citations
                </small>
                <p>
                  {((e.citations as Row[]) || []).map((c) => (
                    <Citation
                      key={`${c.classification}-${c.ordinal}`}
                      id={id}
                      citation={c}
                    />
                  ))}
                </p>
                {!closed && (
                  <button
                    onClick={() => {
                      setEditor(true);
                      setAssessment(str((e.sections as Row)?.assessment));
                      setNextStep(str((e.sections as Row)?.next_step));
                      setEdit(e);
                      setKind(str(e.kind));
                      setTitle(str(e.title));
                      setContent(str(e.content));
                      setCitations((e.citations as Row[]) || []);
                    }}
                  >
                    Edit entry
                  </button>
                )}
              </article>
            ))}
          {!entries.data.total && (
            <p>No analyst findings or notes recorded yet.</p>
          )}
          <Pagination
            offset={offset}
            total={entries.data.total}
            onChange={setOffset}
          />
        </>
      )}
      <details>
        <summary>Bookmarked evidence ({bookmarks.data?.total ?? "…"})</summary>
        {bookmarks.data && (
          <Pagination
            offset={bookmarkOffset}
            total={bookmarks.data.total}
            onChange={setBookmarkOffset}
          />
        )}
        <ReadState
          pending={bookmarks.isPending}
          error={bookmarks.error}
          retry={() => void bookmarks.refetch()}
        />
        {bookmarks.data?.items.map((b) => (
          <p key={`${b.classification}-${b.ordinal}`}>
            {str(b.classification)} #{str(b.ordinal)} · source record{" "}
            {str(b.source_record_number)} · SHA-256{" "}
            {str(b.file_sha256).slice(0, 12)}…
            {!closed && (
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  if (
                    !window.confirm(
                      "Remove this bookmark? Existing finding citations remain in the audit record.",
                    )
                  )
                    return;
                  setBusy(true);
                  try {
                    await request(
                      `/investigations/cases/${id}/bookmarks`,
                      undefined,
                      {
                        classification: b.classification,
                        ordinal: b.ordinal,
                        active: false,
                      },
                    );
                    await cache.invalidateQueries();
                  } catch (e) {
                    setError(e);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Remove bookmark
              </button>
            )}
          </p>
        ))}
      </details>
      {closed ? (
        <p>Reopen with a written reason before editing analyst work.</p>
      ) : editor ? (
        <DetailDrawer
          title={edit ? "Edit analyst entry" : "New analyst entry"}
          onClose={() => setEditor(false)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <h3>{edit ? "Edit entry" : "Record analyst work"}</h3>
            <label>
              Entry kind
              <select
                disabled={!!edit}
                value={kind}
                onChange={(e) => setKind(e.target.value)}
              >
                <option value="finding">Finding</option>
                <option value="note">Note</option>
              </select>
            </label>
            <label>
              Title
              <input
                required
                minLength={3}
                maxLength={240}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Observation / original reasoning
              <textarea
                required
                minLength={10}
                maxLength={8000}
                rows={5}
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
            </label>
            {kind === "finding" && (
              <>
                <label>
                  Assessment (optional)
                  <textarea
                    value={assessment}
                    maxLength={4000}
                    onChange={(e) => setAssessment(e.target.value)}
                  />
                </label>
                <label>
                  Recommended next step (optional)
                  <textarea
                    value={nextStep}
                    maxLength={4000}
                    onChange={(e) => setNextStep(e.target.value)}
                  />
                </label>
                <p className="small muted">
                  Preliminary observations are welcome. A definitive conclusion
                  is not required.
                </p>
              </>
            )}
            {kind === "finding" && (
              <fieldset>
                <legend>Attach bookmarked source evidence</legend>
                <p>{citations.length} selected citations</p>
                {citations.map((c) => (
                  <Citation
                    key={`${c.classification}-${c.ordinal}`}
                    id={id}
                    citation={c}
                  />
                ))}
                {bookmarks.data && (
                  <Pagination
                    offset={bookmarkOffset}
                    total={bookmarks.data.total}
                    onChange={setBookmarkOffset}
                  />
                )}
                {bookmarks.data?.items.map((b) => {
                  const c = {
                    classification: b.classification,
                    ordinal: b.ordinal,
                  };
                  const selected = citations.some(
                    (x) =>
                      x.classification === b.classification &&
                      x.ordinal === b.ordinal,
                  );
                  return (
                    <label
                      className="check"
                      key={`${b.classification}-${b.ordinal}`}
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() =>
                          setCitations(
                            selected
                              ? citations.filter(
                                  (x) =>
                                    x.classification !== b.classification ||
                                    x.ordinal !== b.ordinal,
                                )
                              : [...citations, c],
                          )
                        }
                      />
                      {str((b.source_values as Row)?.Supplier)} ·{" "}
                      {str((b.source_values as Row)?.Amount)} ·{" "}
                      {str((b.source_values as Row)?.Date)} · record{" "}
                      {str(b.source_record_number)}
                    </label>
                  );
                })}
                <small>
                  Bookmark source records from the Evidence tab. Only evidence
                  belonging to this case can be cited.
                </small>
              </fieldset>
            )}
            {error !== undefined && <ErrorNotice error={error} />}
            <div className="actions">
              <button className="primary" disabled={busy}>
                {busy ? "Saving…" : "Save entry"}
              </button>
              {edit && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setEditor(false);
                      setEdit(undefined);
                      setTitle("");
                      setContent("");
                      setCitations([]);
                    }}
                  >
                    Cancel edit
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      if (
                        window.confirm(
                          "Soft-delete this analyst entry? Its prior content remains in audit history.",
                        )
                      )
                        void save(true);
                    }}
                  >
                    Delete entry
                  </button>
                </>
              )}
            </div>
          </form>
        </DetailDrawer>
      ) : null}
    </>
  );
}
export function Lifecycle({ record: c }: { record: Case }) {
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [disposition, setDisposition] = useState("INSUFFICIENT_EVIDENCE");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const next = {
    OPEN: "INVESTIGATING",
    INVESTIGATING: "REVIEWED",
    REVIEWED: "CLOSED",
    CLOSED: "INVESTIGATING",
  }[c.status];
  async function change() {
    setBusy(true);
    try {
      await request(
        `/investigations/cases/${c.case_id}/status`,
        undefined,
        {
          status: next,
          expected_version: c.row_version,
          reason: reason || null,
          disposition: next === "CLOSED" ? disposition : null,
        },
        "PATCH",
      );
      await cache.invalidateQueries();
      setReason("");
      toast.success("Case status updated");
      setOpen(false);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="stepper" aria-label="Case lifecycle">
        {["OPEN", "INVESTIGATING", "REVIEWED", "CLOSED"].map((status, i) => (
          <span key={status} className={c.status === status ? "current" : ""}>
            <i>{i + 1}</i>
            {status.charAt(0) + status.slice(1).toLowerCase()}
          </span>
        ))}
      </div>
      <button onClick={() => setOpen(true)}>Manage case lifecycle</button>
      {open && (
        <Modal
          title={
            c.status === "CLOSED"
              ? "Reopen investigation"
              : `Move to ${next.toLowerCase()}`
          }
          onClose={() => setOpen(false)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void change();
            }}
          >
            <label>
              Written reason
              <textarea
                value={reason}
                minLength={10}
                required={next === "CLOSED" || c.status === "CLOSED"}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            {next === "CLOSED" && (
              <label>
                Disposition
                <select
                  value={disposition}
                  onChange={(e) => setDisposition(e.target.value)}
                >
                  {[
                    "INSUFFICIENT_EVIDENCE",
                    "NO_ACTIONABLE_FINDING",
                    "FURTHER_ACTION_RECOMMENDED",
                  ].map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
            )}
            {error !== undefined && <ErrorNotice error={error} />}
            <button disabled={busy} className="primary">
              {c.status === "CLOSED"
                ? "Reopen investigation"
                : `Move to ${next}`}
            </button>
            <p className="small muted">
              Closure records an analyst outcome, not verified financial
              savings.
            </p>
          </form>
        </Modal>
      )}
    </>
  );
}
export function BookmarkButton({
  id,
  classification,
  ordinal,
  closed = false,
}: {
  id: string;
  classification: string;
  ordinal: number;
  closed?: boolean;
}) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const cache = useQueryClient();
  return (
    <>
      {!closed && (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await request(
                `/investigations/cases/${id}/bookmarks`,
                undefined,
                { classification, ordinal, active: true },
              );
              setMessage("Evidence bookmarked.");
              toast.success("Evidence bookmarked");
              await cache.invalidateQueries({ queryKey: ["product"] });
              await cache.invalidateQueries({ queryKey: ["activity", id] });
              await cache.invalidateQueries({ queryKey: ["case", id] });
            } catch (e) {
              setError(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          Bookmark evidence
        </button>
      )}
      {message && <p role="status">{message}</p>}
      {error !== undefined && <ErrorNotice error={error} />}
    </>
  );
}

function Citation({ id, citation: c }: { id: string; citation: Row }) {
  const [open, setOpen] = useState(false);
  const record = useData<EvidencePage>(
    `/investigations/cases/${id}/evidence?classification=${str(c.classification)}&offset=${Number(c.ordinal) - 1}&limit=1`,
    open,
  );
  const r = record.data?.items[0];
  return (
    <>
      <button className="citation-chip" onClick={() => setOpen(true)}>
        {str(c.classification)} #{str(c.ordinal)} ↗
      </button>
      {open && (
        <DetailDrawer
          title="Cited source evidence"
          onClose={() => setOpen(false)}
        >
          <ReadState
            pending={record.isPending}
            error={record.error}
            retry={() => void record.refetch()}
          />
          {r && (
            <>
              <h3>{String(r.source_values.Supplier ?? "Published source")}</h3>
              <Fields values={r.source_values} />
              <details>
                <summary>Frozen source lineage</summary>
                <Fields
                  values={{
                    filename: r.filename,
                    sha256: r.file_sha256,
                    source_record_number: r.source_record_number,
                    raw_row_id: r.raw_row_id,
                    classification: r.classification,
                    ordinal: r.ordinal,
                  }}
                />
              </details>
            </>
          )}
        </DetailDrawer>
      )}
    </>
  );
}

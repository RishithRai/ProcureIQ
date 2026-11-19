import { useState } from "react";
import {
  FolderPlus,
  Bookmark,
  FileText,
  MessageSquare,
  ArrowRightLeft,
  LockKeyhole,
  RotateCcw,
} from "lucide-react";
import { useData } from "../product/shared";
import type { Page, Event } from "../api/types";
import { date, label } from "../format";
import { Loading, ErrorNotice, Pagination } from "../components/Common";
import type { Json } from "../api/types";
function note(value: Json | undefined) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return (
    <div className="audit-note">
      <h4>{String(value.title || "Recorded entry")}</h4>
      <p className="whitespace-pre-wrap">{String(value.content || "")}</p>
      {Array.isArray(value.citations) && value.citations.length > 0 && (
        <small>
          Citations:{" "}
          {value.citations
            .map((c) =>
              c && typeof c === "object" && !Array.isArray(c)
                ? `${String(c.classification)} #${String(c.ordinal)}`
                : "",
            )
            .join(", ")}
        </small>
      )}
    </div>
  );
}
export function CaseActivity({ id }: { id: string }) {
  const [offset, setOffset] = useState(0);
  const [kind, setKind] = useState("");
  const result = useData<Page<Event>>(
    `/investigations/cases/${id}/activity?offset=${offset}&kind=${kind}`.replace(
      /&kind=$/,
      "",
    ),
  );
  return result.isPending ? (
    <Loading />
  ) : result.isError ? (
    <ErrorNotice error={result.error} retry={() => void result.refetch()} />
  ) : (
    <>
      <h2>Activity</h2>
      <label>
        Activity type
        <select
          value={kind}
          onChange={(e) => {
            setKind(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">All events</option>
          {["lifecycle", "findings", "notes", "evidence"].map((k) => (
            <option key={k} value={k}>
              {label(k)}
            </option>
          ))}
        </select>
      </label>
      <p className="muted small">A durable record of this investigation.</p>
      <ol className="activity-feed case-activity">
        {result.data.items.map((e) => {
          const Icon = e.event_type.includes("BOOKMARK")
            ? Bookmark
            : e.event_type.includes("FINDING")
              ? FileText
              : e.event_type.includes("NOTE")
                ? MessageSquare
                : e.event_type === "CASE_CREATED"
                  ? FolderPlus
                  : e.event_type.includes("REOPEN")
                    ? RotateCcw
                    : e.new_status === "CLOSED"
                      ? LockKeyhole
                      : ArrowRightLeft;
          return (
            <li key={e.event_id}>
              <span className="event-icon">
                <Icon size={16} />
              </span>
              <div className="event-body">
                <div className="event-heading">
                  <h3>{label(e.event_type)}</h3>
                  <time dateTime={e.occurred_at}>{date(e.occurred_at)}</time>
                </div>
                <p>
                  {e.previous_status && e.previous_status !== e.new_status
                    ? `${label(e.previous_status)} → `
                    : ""}
                  {label(e.new_status)}
                </p>
                {e.reason && (
                  <details>
                    <summary>Written explanation</summary>
                    <blockquote>{e.reason}</blockquote>
                  </details>
                )}
                {e.details.classification && (
                  <p>
                    Evidence {String(e.details.classification)} #
                    {String(e.details.ordinal)}
                  </p>
                )}
                {(e.details.before || e.details.after) && (
                  <details>
                    <summary>View recorded changes</summary>
                    {e.details.before && (
                      <>
                        <small>Before</small>
                        {note(e.details.before)}
                      </>
                    )}
                    {e.details.after && (
                      <>
                        <small>After</small>
                        {note(e.details.after)}
                      </>
                    )}
                  </details>
                )}
                <small>Local application · Event {e.event_id}</small>
              </div>
            </li>
          );
        })}
      </ol>
      {!result.data.items.length && <p>No activity recorded yet.</p>}
      <Pagination
        total={result.data.total}
        offset={offset}
        onChange={setOffset}
      />
    </>
  );
}

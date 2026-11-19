import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import type { Reviews } from "../api/types";
import { ErrorNotice, Modal } from "./Common";
export function CreateCase({
  data,
  onClose,
  onStale,
}: {
  data: Reviews;
  onClose: () => void;
  onStale: () => void;
}) {
  const r = data.items[0];
  const [title, setTitle] = useState(r.title.slice(0, 240));
  const [objective, setObjective] = useState(
    r.next_investigation_step ||
      "Investigate the source evidence and validate the procurement hypothesis.",
  );
  const [error, setError] = useState<unknown>();
  const [invalid, setInvalid] = useState(false);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const cache = useQueryClient();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (
      title.trim().length < 3 ||
      objective.trim().length < 10 ||
      (objective.match(/[\p{L}\p{N}]/gu) || []).length < 5
    ) {
      setInvalid(true);
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      const result = await api.create({
        review_id: r.opportunity_id,
        filters: data.basis.filters,
        basis_token: data.basis_token,
        title,
        objective,
      });
      await cache.invalidateQueries({ queryKey: ["reviews"] });
      await cache.invalidateQueries({ queryKey: ["cases"] });
      cache.setQueryData(["case", String(result.case.case_id)], result.case);
      nav(`/investigations/cases/${result.case.case_id}`, {
        state: {
          notice: result.created
            ? "Investigation created with its original evidence basis."
            : "An investigation already exists for this exact review basis. Opened without changes.",
        },
      });
    } catch (err) {
      if (
        err instanceof ApiError &&
        ["stale_review_basis", "concurrent_change"].includes(err.code)
      ) {
        onStale();
        return;
      }
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title="Create Investigation"
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <form onSubmit={submit} noValidate>
        <p>{r.title}</p>
        <p className="muted small">
          Initial status: OPEN · {r.primary_count.toLocaleString()} primary
          references. The server attaches the current verified evidence; no
          amounts are submitted.
        </p>
        <label>
          Case title
          <input
            value={title}
            maxLength={240}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label>
          Investigation objective
          <textarea
            rows={4}
            value={objective}
            maxLength={4000}
            onChange={(e) => setObjective(e.target.value)}
          />
        </label>
        {invalid && (
          <p role="alert" className="validation">
            Enter a title of at least 3 characters and a meaningful objective of
            at least 10 characters.
          </p>
        )}
        <details>
          <summary>Attached source basis</summary>
          <p className="hash">{data.basis.source_fingerprint}</p>
          <p>{data.basis.rule_version}</p>
          <pre>{JSON.stringify(data.basis.filters, null, 2)}</pre>
        </details>
        {error !== undefined && <ErrorNotice error={error} />}
        <footer>
          <button type="button" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={busy} type="submit">
            {busy ? "Creating investigation…" : "Create Investigation"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}

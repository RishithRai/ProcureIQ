import type { Filters } from "../api/types";
export const detectors = [
  "supplier_concentration",
  "purchasing_fragmentation",
  "payment_pattern",
  "data_quality",
];
export const filterKeys = [
  "start_month",
  "end_month",
  "expense_type",
  "expense_area",
  "entity",
  "supplier_id",
] as const;
export function parseQueue(params: URLSearchParams) {
  const filters: Filters = {};
  const offset = params.get("offset");
  let invalid = offset !== null && (!/^\d+$/.test(offset) || +offset > 1000000);
  for (const key of filterKeys) {
    const v = params.get(key);
    if (!v) continue;
    if (key === "supplier_id") {
      if (!/^\d+$/.test(v) || !Number.isSafeInteger(+v) || +v < 1) {
        invalid = true;
        continue;
      }
      filters[key] = +v;
    } else if (key.endsWith("month")) {
      if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(v) || v.startsWith("0000")) {
        invalid = true;
        continue;
      }
      filters[key] = v;
    } else {
      if (v.length > 300) {
        invalid = true;
        continue;
      }
      filters[key] = v;
    }
  }
  if (
    filters.start_month &&
    filters.end_month &&
    filters.start_month > filters.end_month
  )
    invalid = true;
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v != null) query.set(k, String(v));
  });
  const reporting = query.toString();
  const kind = params.get("detector_type");
  if (kind) {
    if (detectors.includes(kind)) query.set("detector_type", kind);
    else invalid = true;
  }
  const priority = params.get("minimum_priority");
  if (priority) {
    if (!/^\d+(\.\d+)?$/.test(priority) || +priority > 100) invalid = true;
    else query.set("minimum_priority", priority);
  }
  const selection = params.get("review") || "";
  if (selection && !/^opp_[a-f0-9]{24}$/.test(selection)) invalid = true;
  return {
    query: query.toString(),
    reporting,
    invalid,
    selection,
    search: (params.get("q") || "").slice(0, 300),
  };
}

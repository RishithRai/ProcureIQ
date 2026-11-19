// Response shapes inspected against the running Stage 1 OpenAPI schema.
export type Status = "OPEN" | "INVESTIGATING" | "REVIEWED" | "CLOSED";
export type Json =
  string | number | boolean | null | Json[] | { [key: string]: Json };
export type Filters = {
  start_month?: string | null;
  end_month?: string | null;
  expense_type?: string | null;
  expense_area?: string | null;
  entity?: string | null;
  supplier_id?: number | null;
};
export type Basis = {
  filters: Filters;
  source_fingerprint: string;
  rule_version: string;
  configuration_identity: string;
};
export interface Review {
  opportunity_id: string;
  opportunity_type: string;
  title: string;
  scope: Record<string, Json>;
  positive_exposure_gbp: string;
  priority_score: string;
  evidence_summary: string;
  primary_count: number;
  contextual_count: number;
  review_basis_key: string;
  existing_case?: { case_id: number; case_reference: string; status: Status };
  metrics?: Record<string, Json>;
  scoring?: Record<string, Json>;
  business_interpretation?: string;
  next_investigation_step?: string;
  caveats?: string[];
  exposure_definition?: string;
}
export interface Page<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}
export interface Reviews extends Page<Review> {
  basis: Basis;
  basis_token: string;
  qualified_count: number;
  exported_count: number;
  deferred_count: number;
  counts_by_type: Record<string, number>;
  qualified_by_type: Record<string, number>;
}
export interface Case {
  work_counts?: Record<string, number>;
  namespace?: "NORMAL" | "DEMO";
  case_id: number;
  case_reference: string;
  title: string;
  objective: string;
  opportunity_id: string;
  opportunity_type: string;
  original_score: string;
  status: Status;
  row_version: number;
  primary_count: number;
  contextual_count: number;
  created_at: string;
  updated_at: string;
  source_fingerprint: string;
  rule_version: string;
  configuration_identity: string;
  reporting_filters: Filters;
  review_basis_key: string;
  basis_matches_current_source: boolean;
  review_snapshot?: Record<string, Json> | null;
  disposition?: string | null;
  closure_explanation?: string | null;
}
export interface Evidence {
  amount_gbp?: string | null;
  bookmarked?: boolean;
  case_id: number;
  classification: "primary" | "contextual";
  ordinal: number;
  raw_row_id: number;
  file_id: number;
  file_sha256: string;
  source_record_number: number;
  row_hash: string;
  source_values: Record<string, Json>;
  physical_line_start: number;
  physical_line_end: number;
  filename: string;
  reporting_month: string;
  source_currently_active: boolean;
}
export interface EvidencePage extends Page<Evidence> {
  unfiltered_total?: number;
  summary?: {
    suppliers: { supplier: string; count: number; positive_gbp: string }[];
    months: { reporting_month: string; count: number }[];
    composition: { positive_gbp: string; credit_gbp: string };
  };
  classification: "primary" | "contextual";
  basis_matches_current_source: boolean;
}
export interface Event {
  event_id: number;
  case_id: number;
  event_type: string;
  occurred_at: string;
  actor: "local_application";
  previous_status: Status | null;
  new_status: Status;
  reason: string | null;
  details: Record<string, Json>;
}
export interface CreateInput {
  review_id: string;
  filters: Filters;
  basis_token: string;
  title: string;
  objective: string;
}
export interface Creation {
  created: boolean;
  case: Case;
}

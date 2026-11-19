CREATE TABLE source_file (
 file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 reporting_month DATE NOT NULL CHECK (extract(day FROM reporting_month)=1),
 source_url TEXT NOT NULL, filename TEXT NOT NULL,
 sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
 size_bytes BIGINT NOT NULL CHECK (size_bytes>=0),
 original_row_count INTEGER NOT NULL CHECK (original_row_count>=0),
 acquired_at TIMESTAMPTZ, active BOOLEAN NOT NULL DEFAULT FALSE,
 import_status TEXT NOT NULL CHECK (import_status IN ('loading','loaded')),
 imported_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
 UNIQUE(reporting_month, sha256), CHECK (NOT active OR import_status='loaded')
);
CREATE UNIQUE INDEX source_file_one_active_month ON source_file(reporting_month) WHERE active;
CREATE TABLE raw_spend_row (
 raw_row_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 file_id BIGINT NOT NULL REFERENCES source_file,
 source_record_number INTEGER NOT NULL CHECK (source_record_number>0),
 physical_line_start INTEGER NOT NULL CHECK (physical_line_start>0),
 physical_line_end INTEGER NOT NULL CHECK (physical_line_end>=physical_line_start),
 source_values JSONB NOT NULL,
 row_hash CHAR(64) NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 UNIQUE(file_id, source_record_number)
);
CREATE TABLE supplier (
 supplier_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 canonical_name TEXT NOT NULL,
 normalized_key TEXT NOT NULL UNIQUE CHECK (normalized_key<>'')
);
CREATE TABLE supplier_alias (
 alias_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 original_name TEXT NOT NULL UNIQUE,
 normalized_key TEXT NOT NULL,
 supplier_id BIGINT REFERENCES supplier,
 mapping_method TEXT NOT NULL CHECK (mapping_method IN ('case_whitespace_v1','placeholder_v1')),
 review_status TEXT NOT NULL CHECK (review_status IN ('auto_resolved','unresolved')),
 reviewed_at TIMESTAMPTZ,
 mapped_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
 CHECK ((review_status='auto_resolved' AND supplier_id IS NOT NULL) OR
        (review_status='unresolved' AND supplier_id IS NULL))
);
CREATE INDEX supplier_alias_supplier_idx ON supplier_alias(supplier_id);
CREATE TABLE spend_line (
 spend_line_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 raw_row_id BIGINT NOT NULL UNIQUE REFERENCES raw_spend_row,
 payment_date DATE, department_family TEXT, entity TEXT, expense_type TEXT, expense_area TEXT,
 supplier_raw TEXT, supplier_id BIGINT REFERENCES supplier,
 transaction_number TEXT, amount_gbp NUMERIC(20,2), description TEXT, supplier_postcode TEXT,
 supplier_type TEXT, contract_number TEXT, project_code TEXT,
 parse_status TEXT NOT NULL CHECK (parse_status IN ('valid','invalid')),
 CHECK (parse_status<>'valid' OR (payment_date IS NOT NULL AND amount_gbp IS NOT NULL))
);
CREATE INDEX spend_line_payment_date_idx ON spend_line(payment_date);
CREATE INDEX spend_line_supplier_idx ON spend_line(supplier_id);
CREATE TABLE data_quality_issue (
 issue_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 file_id BIGINT REFERENCES source_file,
 raw_row_id BIGINT REFERENCES raw_spend_row,
 issue_code TEXT NOT NULL,
 severity TEXT NOT NULL CHECK (severity IN ('info','warning','error')),
 field TEXT, details JSONB NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
 resolved_at TIMESTAMPTZ,
 CHECK ((file_id IS NULL) <> (raw_row_id IS NULL))
);
CREATE INDEX data_quality_issue_file_idx ON data_quality_issue(file_id) WHERE file_id IS NOT NULL;
CREATE INDEX data_quality_issue_row_idx ON data_quality_issue(raw_row_id) WHERE raw_row_id IS NOT NULL;
CREATE FUNCTION reject_raw_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Raw source rows are immutable; register a new source version'; END;
$$;
CREATE TRIGGER immutable_raw BEFORE UPDATE OR DELETE ON raw_spend_row
FOR EACH ROW EXECUTE FUNCTION reject_raw_mutation();

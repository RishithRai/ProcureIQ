CREATE TABLE investigation_case (
 case_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 case_reference TEXT GENERATED ALWAYS AS ('PIQ-' || lpad(case_id::text,greatest(6,length(case_id::text)),'0')) STORED UNIQUE,
 title TEXT NOT NULL CHECK (length(btrim(title)) BETWEEN 3 AND 240),
 objective TEXT NOT NULL CHECK (length(btrim(objective)) BETWEEN 10 AND 4000),
 opportunity_id TEXT NOT NULL,
 opportunity_type TEXT NOT NULL CHECK (opportunity_type IN ('supplier_concentration','purchasing_fragmentation','payment_pattern','data_quality')),
 original_score NUMERIC NOT NULL CHECK (original_score BETWEEN 0 AND 100),
 review_snapshot JSONB NOT NULL CHECK (jsonb_typeof(review_snapshot)='object'),
 rule_version TEXT NOT NULL,
 configuration JSONB NOT NULL,
 configuration_identity CHAR(64) NOT NULL CHECK (configuration_identity ~ '^[0-9a-f]{64}$'),
 reporting_filters JSONB NOT NULL,
 source_fingerprint CHAR(64) NOT NULL CHECK (source_fingerprint ~ '^[0-9a-f]{64}$'),
 review_basis_key CHAR(64) NOT NULL UNIQUE CHECK (review_basis_key ~ '^[0-9a-f]{64}$'),
 primary_count INTEGER NOT NULL CHECK (primary_count>=0),
 contextual_count INTEGER NOT NULL CHECK (contextual_count>=0),
 status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','INVESTIGATING','REVIEWED','CLOSED')),
 row_version INTEGER NOT NULL DEFAULT 1 CHECK (row_version>0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 reviewed_at TIMESTAMPTZ,
 closed_at TIMESTAMPTZ,
 disposition TEXT CHECK (disposition IN ('FURTHER_ACTION_RECOMMENDED','NO_ACTIONABLE_FINDING','INSUFFICIENT_EVIDENCE')),
 closure_explanation TEXT,
 CHECK ((status='CLOSED') = (closed_at IS NOT NULL)),
 CHECK ((status='CLOSED') = (disposition IS NOT NULL)),
 CHECK (status<>'CLOSED' OR (closure_explanation IS NOT NULL AND length(btrim(closure_explanation))>=10)),
 CHECK (status NOT IN ('REVIEWED','CLOSED') OR reviewed_at IS NOT NULL)
);
CREATE INDEX investigation_case_status_id ON investigation_case(status,case_id);
CREATE TABLE case_evidence (
 case_id BIGINT NOT NULL REFERENCES investigation_case ON DELETE RESTRICT,
 classification TEXT NOT NULL CHECK (classification IN ('primary','contextual')),
 ordinal INTEGER NOT NULL CHECK (ordinal>0),
 raw_row_id BIGINT NOT NULL REFERENCES procureiq.raw_spend_row ON DELETE RESTRICT,
 file_id BIGINT NOT NULL REFERENCES procureiq.source_file ON DELETE RESTRICT,
 file_sha256 CHAR(64) NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
 source_record_number INTEGER NOT NULL CHECK (source_record_number>0),
 row_hash CHAR(64) NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 PRIMARY KEY(case_id,classification,ordinal),
 UNIQUE(case_id,classification,file_id,source_record_number)
);
CREATE INDEX case_evidence_raw_idx ON case_evidence(raw_row_id);
CREATE INDEX case_evidence_file_idx ON case_evidence(file_id);
CREATE TABLE case_event (
 event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 case_id BIGINT NOT NULL REFERENCES investigation_case ON DELETE RESTRICT,
 event_type TEXT NOT NULL CHECK (event_type IN ('CASE_CREATED','STATUS_CHANGED','CASE_REOPENED')),
 occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 actor TEXT NOT NULL DEFAULT 'local_application' CHECK (actor='local_application'),
 previous_status TEXT CHECK (previous_status IN ('OPEN','INVESTIGATING','REVIEWED','CLOSED')),
 new_status TEXT NOT NULL CHECK (new_status IN ('OPEN','INVESTIGATING','REVIEWED','CLOSED')),
 reason TEXT,
 details JSONB NOT NULL,
 CHECK (event_type<>'CASE_REOPENED' OR length(btrim(reason))>=10)
);
CREATE INDEX case_event_case_order ON case_event(case_id,event_id);
CREATE FUNCTION reject_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Investigation evidence and events are immutable'; END;
$$;
CREATE TRIGGER immutable_case_evidence BEFORE UPDATE OR DELETE ON case_evidence FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER immutable_case_event BEFORE UPDATE OR DELETE ON case_event FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE FUNCTION protect_case_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Cases cannot be deleted'; END IF;
 IF (to_jsonb(NEW) - ARRAY['case_reference','status','row_version','updated_at','reviewed_at','closed_at','disposition','closure_explanation'])
    IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['case_reference','status','row_version','updated_at','reviewed_at','closed_at','disposition','closure_explanation']) THEN
   RAISE EXCEPTION 'Original case snapshot is immutable';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER immutable_case_snapshot BEFORE UPDATE OR DELETE ON investigation_case FOR EACH ROW EXECUTE FUNCTION protect_case_snapshot();

CREATE TABLE optimization_run (
 run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 model_version TEXT NOT NULL,
 assumptions JSONB NOT NULL,
 result JSONB NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER immutable_optimization BEFORE UPDATE OR DELETE ON optimization_run FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TABLE source_registration (
 registration_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 manifest_name TEXT NOT NULL,
 manifest_sha256 CHAR(64) NOT NULL,
 receipts JSONB NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(manifest_name,manifest_sha256)
);
CREATE TRIGGER immutable_registration BEFORE UPDATE OR DELETE ON source_registration FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TABLE pipeline_run (
 run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 operation TEXT NOT NULL CHECK(operation IN ('verify','ingest','activate')),
 registration_id BIGINT REFERENCES source_registration,
 source_file_id BIGINT REFERENCES procureiq.source_file,
 expected_fingerprint CHAR(64),
 retry_of BIGINT REFERENCES pipeline_run,
 status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','succeeded','failed','interrupted')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 started_at TIMESTAMPTZ,
 finished_at TIMESTAMPTZ,
 current_stage TEXT,
 error_code TEXT,
 error_summary TEXT
);
CREATE TABLE pipeline_stage (
 stage_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 run_id BIGINT NOT NULL REFERENCES pipeline_run,
 name TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('running','succeeded','failed','interrupted')),
 started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 finished_at TIMESTAMPTZ,
 duration_ms NUMERIC,
 output JSONB,
 UNIQUE(run_id,name)
);
CREATE INDEX pipeline_run_status_idx ON pipeline_run(status,run_id);

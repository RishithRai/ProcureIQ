ALTER TABLE case_event DROP CONSTRAINT case_event_event_type_check;
ALTER TABLE case_event ADD CONSTRAINT case_event_event_type_check CHECK(event_type IN ('CASE_CREATED','STATUS_CHANGED','CASE_REOPENED','NOTE_CREATED','NOTE_UPDATED','NOTE_DELETED','FINDING_CREATED','FINDING_UPDATED','FINDING_DELETED','EVIDENCE_BOOKMARKED','BOOKMARK_REMOVED'));
CREATE TABLE case_bookmark (
 case_id BIGINT NOT NULL,
 classification TEXT NOT NULL,
 ordinal INTEGER NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 active BOOLEAN NOT NULL DEFAULT true,
 PRIMARY KEY(case_id,classification,ordinal),
 FOREIGN KEY(case_id,classification,ordinal) REFERENCES case_evidence ON DELETE RESTRICT
);
CREATE TABLE case_entry (
 entry_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 case_id BIGINT NOT NULL REFERENCES investigation_case ON DELETE RESTRICT,
 kind TEXT NOT NULL CHECK(kind IN ('note','finding')),
 title TEXT NOT NULL CHECK(length(btrim(title)) BETWEEN 3 AND 240),
 content TEXT NOT NULL CHECK(length(btrim(content)) BETWEEN 10 AND 8000),
 row_version INTEGER NOT NULL DEFAULT 1 CHECK(row_version>0),
 deleted BOOLEAN NOT NULL DEFAULT false,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(case_id,entry_id)
);
CREATE INDEX case_entry_case_idx ON case_entry(case_id,entry_id);
CREATE TABLE finding_evidence (
 case_id BIGINT NOT NULL,
 entry_id BIGINT NOT NULL,
 classification TEXT NOT NULL,
 ordinal INTEGER NOT NULL,
 PRIMARY KEY(entry_id,classification,ordinal),
 FOREIGN KEY(case_id,entry_id) REFERENCES case_entry(case_id,entry_id) ON DELETE RESTRICT,
 FOREIGN KEY(case_id,classification,ordinal) REFERENCES case_bookmark ON DELETE RESTRICT
);

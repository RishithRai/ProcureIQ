-- Logical workspaces, not an authorization boundary. Migrator wraps this in one
-- checksum-tracked transaction and advisory lock. Preserve every existing ID.
LOCK TABLE investigation_case IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS (SELECT review_basis_key FROM investigation_case GROUP BY review_basis_key HAVING count(*)>1) THEN
   RAISE EXCEPTION 'Conflicting legacy review bases require manual review';
 END IF;
END $$;
ALTER TABLE investigation_case ADD COLUMN namespace TEXT NOT NULL DEFAULT 'NORMAL'
 CHECK (namespace IN ('NORMAL','DEMO'));
-- The exact explicit prefix is the only automatic legacy classification rule.
ALTER TABLE investigation_case DISABLE TRIGGER immutable_case_snapshot;
UPDATE investigation_case SET namespace='DEMO' WHERE title ~ '^\s*\[LOCAL DEMO\]';
ALTER TABLE investigation_case ENABLE TRIGGER immutable_case_snapshot;
ALTER TABLE investigation_case DROP CONSTRAINT investigation_case_review_basis_key_key;
ALTER TABLE investigation_case ADD CONSTRAINT investigation_case_basis_namespace_key UNIQUE(review_basis_key,namespace);
CREATE INDEX investigation_case_namespace_status ON investigation_case(namespace,status,case_id);

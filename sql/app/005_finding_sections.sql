-- Existing free-text entries stay untouched; optional structured sections are
-- carried in before/after audit snapshots on subsequent explicit analyst edits.
ALTER TABLE case_entry ADD COLUMN sections JSONB CHECK (sections IS NULL OR jsonb_typeof(sections)='object');

-- Allow different users to save the same listing while preserving per-user deduplication.
-- Idempotent for both bootstrap and existing databases.
DO $$
DECLARE
    constraint_name text;
BEGIN
    SELECT con.conname
      INTO constraint_name
      FROM pg_constraint con
      JOIN pg_class rel ON rel.oid = con.conrelid
      JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
     WHERE nsp.nspname = current_schema()
       AND rel.relname = 'jobs'
       AND con.contype = 'u'
       AND (
           SELECT array_agg(att.attname ORDER BY key_column.ordinality)
             FROM unnest(con.conkey) WITH ORDINALITY AS key_column(attnum, ordinality)
             JOIN pg_attribute att
               ON att.attrelid = rel.oid
              AND att.attnum = key_column.attnum
       ) = ARRAY['job_link']::name[];

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE jobs DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_user_email_job_link
    ON jobs(user_email, job_link);

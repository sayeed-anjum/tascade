-- Add api_key table for project-scoped API key authentication.
-- The api_key_status enum already exists in the baseline schema (schema-v0.1.sql).

DO $$ BEGIN
  CREATE TYPE api_key_status AS ENUM ('active', 'revoked');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS api_key (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  hash TEXT NOT NULL UNIQUE,
  role_scopes TEXT[] NOT NULL DEFAULT '{}'::text[],
  status api_key_status NOT NULL DEFAULT 'active',
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at TIMESTAMPTZ NULL,
  revoked_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_api_key_project_status
  ON api_key(project_id, status);

CREATE INDEX IF NOT EXISTS idx_api_key_hash_active
  ON api_key(hash) WHERE status = 'active';

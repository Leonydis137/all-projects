-- Additive schema for Vantage Sentinel. Applied to the live vantage-data D1
-- database with: wrangler d1 execute vantage-data --remote --file=schema.sql
-- No existing table is altered or dropped.

CREATE TABLE IF NOT EXISTS sentinel_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  captured_at TEXT NOT NULL UNIQUE,
  overall_status TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sentinel_snapshots_captured
  ON sentinel_snapshots (captured_at DESC);

CREATE TABLE IF NOT EXISTS sentinel_briefings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot_id INTEGER NOT NULL REFERENCES sentinel_snapshots(id),
  created_at TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  status TEXT NOT NULL,
  text TEXT NOT NULL,
  error_code TEXT NOT NULL DEFAULT '',
  facts_sha256 TEXT NOT NULL,
  UNIQUE (snapshot_id, provider, facts_sha256)
);

CREATE INDEX IF NOT EXISTS idx_sentinel_briefings_created
  ON sentinel_briefings (created_at DESC);

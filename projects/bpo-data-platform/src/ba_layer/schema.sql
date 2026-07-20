PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ba_tasks (
  ba_task_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  task_name TEXT NOT NULL,
  date_start TEXT NOT NULL,
  date_end TEXT NOT NULL,
  status TEXT NOT NULL,
  b_db_path TEXT NOT NULL,
  ba_db_path TEXT NOT NULL,
  source_snapshot_json TEXT NOT NULL,
  current_build_id TEXT,
  published_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ba_release_registry (
  project_id TEXT PRIMARY KEY,
  ba_task_id TEXT NOT NULL,
  published_at TEXT NOT NULL,
  release_summary_json TEXT NOT NULL,
  FOREIGN KEY (ba_task_id) REFERENCES ba_tasks(ba_task_id)
);


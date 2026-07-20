PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  project_name TEXT NOT NULL,
  project_code TEXT,
  client_name TEXT,
  business_type TEXT,
  schema_version TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS process_tasks (
  task_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  task_type TEXT NOT NULL,
  status TEXT NOT NULL,
  input_summary TEXT,
  output_summary TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS source_files (
  file_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  task_id TEXT,
  file_type TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_hash TEXT NOT NULL,
  business_date TEXT,
  status TEXT NOT NULL DEFAULT 'recorded',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(project_id),
  FOREIGN KEY (task_id) REFERENCES process_tasks(task_id)
);

CREATE TABLE IF NOT EXISTS export_jobs (
  export_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  export_type TEXT NOT NULL,
  date_start TEXT,
  date_end TEXT,
  output_name TEXT,
  status TEXT NOT NULL,
  summary_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  finished_at TEXT,
  FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS demo_day_records (
  project_id TEXT NOT NULL,
  record_date TEXT NOT NULL,
  planned_headcount INTEGER NOT NULL,
  actual_headcount INTEGER NOT NULL,
  business_count INTEGER NOT NULL,
  quality_flags_json TEXT NOT NULL DEFAULT '[]',
  note TEXT NOT NULL DEFAULT '',
  source_task_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (project_id, record_date),
  FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS demo_person_day_records (
  project_id TEXT NOT NULL,
  record_date TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  employee_label TEXT NOT NULL,
  planned_hours REAL NOT NULL,
  actual_hours REAL NOT NULL,
  business_count INTEGER NOT NULL,
  quality_note TEXT NOT NULL DEFAULT '',
  source_task_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (project_id, record_date, employee_id),
  FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX IF NOT EXISTS idx_demo_day_project_date
ON demo_day_records (project_id, record_date);

CREATE INDEX IF NOT EXISTS idx_demo_person_project_date
ON demo_person_day_records (project_id, record_date);


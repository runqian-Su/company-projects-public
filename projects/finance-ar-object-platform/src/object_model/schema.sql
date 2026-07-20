PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS process_tasks (
  task_id TEXT PRIMARY KEY,
  task_type TEXT NOT NULL,
  status TEXT NOT NULL,
  input_file TEXT NOT NULL,
  as_of_date TEXT NOT NULL,
  summary_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finance_groups (
  group_id TEXT PRIMARY KEY,
  group_name TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'active',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finance_entities (
  entity_id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  entity_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (group_id, entity_name),
  FOREIGN KEY (group_id) REFERENCES finance_groups(group_id)
);

CREATE TABLE IF NOT EXISTS finance_business_objects (
  object_id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  parent_object_id TEXT,
  object_level TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_key TEXT NOT NULL,
  object_name TEXT NOT NULL,
  customer_name TEXT,
  source_doc_no TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (entity_id, object_level, object_type, object_key),
  FOREIGN KEY (group_id) REFERENCES finance_groups(group_id),
  FOREIGN KEY (entity_id) REFERENCES finance_entities(entity_id),
  FOREIGN KEY (parent_object_id) REFERENCES finance_business_objects(object_id)
);

CREATE TABLE IF NOT EXISTS ar_balance_facts (
  fact_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  group_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  as_of_date TEXT NOT NULL,
  has_open_balance INTEGER NOT NULL,
  open_balance_amount REAL NOT NULL,
  line_count INTEGER NOT NULL,
  source_task_id TEXT NOT NULL,
  raw_summary_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (object_id, as_of_date, source_task_id),
  FOREIGN KEY (object_id) REFERENCES finance_business_objects(object_id),
  FOREIGN KEY (group_id) REFERENCES finance_groups(group_id),
  FOREIGN KEY (entity_id) REFERENCES finance_entities(entity_id),
  FOREIGN KEY (source_task_id) REFERENCES process_tasks(task_id)
);

CREATE TABLE IF NOT EXISTS ar_balance_fact_lines (
  line_id TEXT PRIMARY KEY,
  fact_id TEXT NOT NULL,
  object_id TEXT NOT NULL,
  group_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  source_row INTEGER NOT NULL,
  customer_name TEXT NOT NULL,
  source_doc_no TEXT NOT NULL,
  ar_amount REAL NOT NULL,
  posting_date TEXT NOT NULL,
  writeoff_amount REAL NOT NULL,
  ar_balance REAL NOT NULL,
  description TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  source_task_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (fact_id, source_row),
  FOREIGN KEY (fact_id) REFERENCES ar_balance_facts(fact_id),
  FOREIGN KEY (object_id) REFERENCES finance_business_objects(object_id),
  FOREIGN KEY (group_id) REFERENCES finance_groups(group_id),
  FOREIGN KEY (entity_id) REFERENCES finance_entities(entity_id),
  FOREIGN KEY (source_task_id) REFERENCES process_tasks(task_id)
);

CREATE INDEX IF NOT EXISTS idx_finance_entities_group ON finance_entities (group_id);
CREATE INDEX IF NOT EXISTS idx_finance_objects_entity_level_type ON finance_business_objects (entity_id, object_level, object_type);
CREATE INDEX IF NOT EXISTS idx_ar_balance_facts_date ON ar_balance_facts (as_of_date);
CREATE INDEX IF NOT EXISTS idx_ar_balance_lines_fact ON ar_balance_fact_lines (fact_id);


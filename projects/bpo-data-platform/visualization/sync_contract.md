# 可视化同步契约

## 定位

可视化层是消费层，不是事实生产层，也不是业务操作层。

它只能读取 C 层公开 API 中的已发布结果，并写入客户端本地 SQLite 可视化池。

## 数据源选择

正确链路：

```text
当前发布版本
  -> 已发布 Ba 任务
  -> Ba 任务内记录
  -> 客户端本地 SQLite 可视化池
```

禁止链路：

```text
B 层事实库 -> 客户端可视化池
未发布 Ba 任务 -> 客户端可视化池
任意 SQLite 文件路径 -> 客户端可视化池
```

原因：

- B 层保存刚性事实，不包含 Ba 任务内的受控编辑、构建和发布状态；
- 未发布 Ba 任务仍处于操作态，不应作为看板可信口径；
- 客户端不应直接访问服务端 SQLite 文件。

## API 调用顺序

1. 查询当前发布任务：

```text
GET /api/releases/{project_id}/current
```

2. 如果没有 `current_release`，同步失败并提示需要先发布 Ba 任务。

3. 读取发布任务的数据：

```text
GET /api/ba/tasks/{ba_task_id}/records?dataset=day
GET /api/ba/tasks/{ba_task_id}/records?dataset=person
```

4. 写入本地可视化池。

## 本地 SQLite 表

### `sync_meta`

保存最近同步状态。

```text
key TEXT PRIMARY KEY
value TEXT NOT NULL
updated_at TEXT NOT NULL
```

### `released_tasks`

保存本地已同步发布任务。

```text
project_id TEXT PRIMARY KEY
ba_task_id TEXT NOT NULL
published_at TEXT
release_summary_json TEXT NOT NULL
synced_at TEXT NOT NULL
```

### `day_records`

保存已发布 Ba 任务的日数据展示缓存。

```text
project_id TEXT
ba_task_id TEXT
record_date TEXT
planned_headcount INTEGER
actual_headcount INTEGER
business_count INTEGER
quality_flags_json TEXT
note TEXT
updated_at TEXT
PRIMARY KEY (project_id, ba_task_id, record_date)
```

### `person_records`

保存已发布 Ba 任务的个人日数据展示缓存。

```text
project_id TEXT
ba_task_id TEXT
record_date TEXT
employee_id TEXT
employee_label TEXT
planned_hours REAL
actual_hours REAL
business_count INTEGER
quality_note TEXT
updated_at TEXT
PRIMARY KEY (project_id, ba_task_id, record_date, employee_id)
```

## 治理规则

- 客户端可视化池只读展示，不作为主数据源；
- 同步时按 `project_id + ba_task_id` 覆盖本地旧数据；
- 同步失败时保留本地旧数据；
- 可视化层不提供编辑、构建、发布能力；
- 可视化层不反写 B、Ba 或 C 层；
- 可视化层不连接真实外部系统。


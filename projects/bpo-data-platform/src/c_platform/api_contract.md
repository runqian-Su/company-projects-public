# C 层 API 契约

> 本文件是 C 层本地数据管理平台的接口契约。当前 Demo 已提供最小 FastAPI endpoint，契约用于说明前端、CLI、Agent Skill 和可视化消费层应该如何受控访问 A/B/Ba 能力。

## 设计原则

C 层是应用入口和访问边界，不拥有核心业务事实。

```text
C 层可以触发 A->B、B->Ba、Ba build、Ba publish。
C 层可以查询 B 层事实和已发布 Ba 结果。
C 层不能绕过 A 直接写 B。
C 层不能绕过 Ba 的 diff/apply/build/publish 规则。
```

统一响应格式：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

失败响应：

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "validation_error",
    "message": "可展示给用户的中文错误说明"
  }
}
```

## 项目与健康检查

### GET `/api/health`

用途：检查本地平台是否可用。

权限：只读。

响应：

```json
{
  "ok": true,
  "data": {
    "service": "bpo-data-platform-demo",
    "status": "ok"
  },
  "error": null
}
```

### GET `/api/projects`

用途：查询 B 层已注册项目。

权限：只读，只读 B 层。

响应 `data`：

```json
{
  "projects": [
    {
      "project_id": "demo_retail_ops",
      "project_name": "DemoCorp 零售运营样例项目",
      "status": "active"
    }
  ]
}
```

## A -> B 事实处理

### POST `/api/a-layer/run`

用途：触发 A 层合成原始输入处理，并将事实写入 B 层。

权限：受控写入。唯一允许常规写 B 层事实的 C 层入口。

请求：

```json
{
  "project_id": "demo_retail_ops",
  "raw_input_dir": "examples/raw-input"
}
```

响应 `data`：

```json
{
  "task_id": "task-demo-a-to-b-001",
  "project_id": "demo_retail_ops",
  "day_count": 3,
  "person_count": 5,
  "source_files": [
    {
      "file_name": "raw_day_records.csv",
      "file_type": "raw_day_csv",
      "file_hash": "sha256..."
    }
  ]
}
```

约束：

- 只允许调用白名单 A 层处理器。
- 不接受任意脚本路径。
- 写入 B 层时必须记录处理任务和源文件 hash。

## B 层事实查询

### GET `/api/b-layer/{project_id}/date-range`

用途：查询项目已入库日期范围。

权限：只读。

响应 `data`：

```json
{
  "project_id": "demo_retail_ops",
  "day": {
    "date_start": "2026-05-01",
    "date_end": "2026-05-03",
    "row_count": 3
  },
  "person": {
    "date_start": "2026-05-01",
    "date_end": "2026-05-03",
    "row_count": 5
  }
}
```

### GET `/api/b-layer/{project_id}/records`

用途：查询 B 层刚性事实记录。

权限：只读。

查询参数：

```text
dataset=day|person
date_start=YYYY-MM-DD
date_end=YYYY-MM-DD
```

约束：

- 只读 B 层。
- 不生成导出文件。
- 不修改任务状态。

## Ba 任务管理

### POST `/api/ba/tasks`

用途：从 B 层复制事实，创建 Ba 任务切片。

权限：受控写入 Ba。只读 B，不写 B。

请求：

```json
{
  "project_id": "demo_retail_ops",
  "date_start": "2026-05-01",
  "date_end": "2026-05-03"
}
```

响应 `data`：

```json
{
  "ba_task_id": "ba-demo_retail_ops-xxxxxxxxxx",
  "source_snapshot": {
    "project_id": "demo_retail_ops",
    "date_start": "2026-05-01",
    "date_end": "2026-05-03",
    "day_count": 3,
    "person_count": 5
  }
}
```

### GET `/api/ba/tasks`

用途：查询 Ba 任务列表。

权限：只读 Ba 元信息。

查询参数：

```text
project_id=demo_retail_ops
```

### GET `/api/ba/tasks/{ba_task_id}/records`

用途：查询 Ba 任务切片内记录。

权限：只读 Ba 任务库。

查询参数：

```text
dataset=day|person
date_start=YYYY-MM-DD
date_end=YYYY-MM-DD
```

## Ba 受控编辑

### GET `/api/ba/tasks/{ba_task_id}/editable`

用途：查询某个数据集的主键和可编辑字段。

权限：只读。

查询参数：

```text
dataset=day|person
```

响应 `data`：

```json
{
  "dataset": "day",
  "record_key": ["record_date"],
  "editable_fields": {
    "planned_headcount": "INTEGER",
    "note": "TEXT"
  }
}
```

### POST `/api/ba/tasks/{ba_task_id}/diff`

用途：生成编辑预览，不写事实表。

权限：受控操作预览。

请求：

```json
{
  "dataset": "day",
  "changes": [
    {
      "record_key": {
        "date": "2026-05-01"
      },
      "field": "planned_headcount",
      "new_value": 5
    }
  ]
}
```

响应 `data`：

```json
{
  "diff_id": "diff-xxxxxxxxxxxxxxxx",
  "expires_at": "2026-07-20T13:41:47+00:00",
  "preview": [
    {
      "record_key": {
        "date": "2026-05-01"
      },
      "field": "planned_headcount",
      "old_value": 4,
      "new_value": 5,
      "will_change": true
    }
  ]
}
```

### POST `/api/ba/tasks/{ba_task_id}/apply`

用途：应用已经预览过的 diff。

权限：受控写入 Ba。

请求：

```json
{
  "dataset": "day",
  "diff_id": "diff-xxxxxxxxxxxxxxxx",
  "reason": "演示任务切片内规划人力修正"
}
```

约束：

- 必须提供有效且未过期的 `diff_id`。
- 必须提供非空 `reason`。
- 只写 Ba 任务切片，不反写 B。
- 成功后当前 build 失效，需要重新 build。

## Ba 构建与发布

### POST `/api/ba/tasks/{ba_task_id}/build`

用途：执行任务级构建。

权限：受控写入 Ba 构建日志。

响应 `data`：

```json
{
  "build_id": "build-xxxxxxxxxxxxxxxx",
  "summary": {
    "day_count": 3,
    "person_count": 5,
    "fact_revision": 1
  }
}
```

### POST `/api/ba/tasks/{ba_task_id}/publish`

用途：发布当前任务。

权限：受控发布。

约束：

- 必须已有当前成功 build。
- 如果 apply 后未重新 build，发布失败。
- 发布结果写入 release registry。

响应 `data`：

```json
{
  "publish_id": "publish-xxxxxxxxxxxxxxxx",
  "release_summary": {
    "project_id": "demo_retail_ops",
    "ba_task_id": "ba-demo_retail_ops-xxxxxxxxxx",
    "build_id": "build-xxxxxxxxxxxxxxxx",
    "date_start": "2026-05-01",
    "date_end": "2026-05-03"
  }
}
```

## 发布结果查询

### GET `/api/releases/{project_id}/current`

用途：查询当前已发布 Ba 任务。

权限：只读 release registry。

约束：

- 高级看板和交付包应优先读取当前发布结果。
- 不应绕过发布状态直接读取未发布 Ba 中间表。

## 禁止接口

C 层不提供以下能力：

- 任意 SQL 执行；
- 任意 shell 执行；
- 直接写 B 层事实表；
- 跳过 diff 的 Ba 编辑；
- 未 build 直接发布；
- 删除运行目录；
- 外部消息发送。

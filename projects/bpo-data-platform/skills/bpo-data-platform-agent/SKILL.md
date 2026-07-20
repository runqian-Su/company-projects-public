# BPO 数据平台 Agent Skill（脱敏 Demo）

## 适用场景

当用户希望通过自然语言查询或操作本 Demo 的 BPO 多层数据平台时，使用本 Skill。

本 Skill 用于展示 Agent 如何在企业数据系统中作为受控入口工作：

```text
自然语言
  -> 意图解析
  -> 参数校验
  -> C 层 API 或白名单 CLI
  -> JSON 结果
```

它不是生产环境 Skill，不包含真实客户数据、真实外部系统连接或消息发送能力。

## 系统边界

本 Demo 的数据链路为：

```text
A 层：合成原始输入处理
B 层：刚性事实库
Ba 层：任务级可控操作层
C 层：本地 API / CLI 入口
```

Agent 必须遵守：

- B 层默认只读；
- A 层是常规写 B 的唯一入口；
- Ba 可以从 B 层复制事实，但不能反写 B；
- Ba 编辑必须先 `diff` 再 `apply`；
- `apply` 必须提供明确修改原因；
- `publish` 必须在当前任务成功 `build` 后执行；
- 不执行任意 shell 命令；
- 不修改配置文件；
- 不删除运行文件；
- 不发送外部消息。

## 推荐接入方式

优先使用 C 层 API。

默认本地地址：

```text
http://127.0.0.1:8787
```

如果 API 未启动，可以使用白名单 CLI。

CLI 根目录：

```text
company-projects-public/projects/bpo-data-platform
```

CLI 入口：

```bash
python3 cli/bpo_demo.py ...
```

## 支持意图

### 初始化 Demo

用户说：

```text
初始化 BPO demo
重置并生成合成数据
```

API：

```text
POST /api/demo/init
```

CLI：

```bash
python3 cli/bpo_demo.py init-db
```

### 查询项目

用户说：

```text
有哪些项目
查询 demo 项目列表
```

API：

```text
GET /api/projects
```

CLI：

```bash
python3 cli/bpo_demo.py b projects
```

### 查询 B 层日期范围

用户说：

```text
查询 demo_retail_ops 的日期范围
这个项目有哪些日期的数据
```

API：

```text
GET /api/b-layer/{project_id}/date-range
```

CLI：

```bash
python3 cli/bpo_demo.py b date-range --project demo_retail_ops
```

### 查询 B 层事实记录

用户说：

```text
查询 2026-05-01 到 2026-05-03 的日数据
查询 person 数据
```

必须解析：

```json
{
  "project_id": "demo_retail_ops",
  "dataset": "day | person",
  "date_start": "YYYY-MM-DD",
  "date_end": "YYYY-MM-DD"
}
```

API：

```text
GET /api/b-layer/{project_id}/records?dataset=day&date_start=YYYY-MM-DD&date_end=YYYY-MM-DD
```

CLI：

```bash
python3 cli/bpo_demo.py b query \
  --project demo_retail_ops \
  --dataset day \
  --date-start YYYY-MM-DD \
  --date-end YYYY-MM-DD
```

### 创建 Ba 任务

用户说：

```text
创建一个 2026-05-01 到 2026-05-03 的 Ba 任务
从 B 层复制这个日期范围做操作任务
```

API：

```text
POST /api/ba/tasks
```

请求：

```json
{
  "project_id": "demo_retail_ops",
  "date_start": "YYYY-MM-DD",
  "date_end": "YYYY-MM-DD"
}
```

CLI：

```bash
python3 cli/bpo_demo.py ba create-task \
  --project demo_retail_ops \
  --date-start YYYY-MM-DD \
  --date-end YYYY-MM-DD
```

### Ba 查询与可编辑字段

用户说：

```text
查询这个 Ba 任务里的 day 数据
这个任务哪些字段可以改
```

API：

```text
GET /api/ba/tasks/{ba_task_id}/records?dataset=day
GET /api/ba/tasks/{ba_task_id}/editable?dataset=day
```

CLI：

```bash
python3 cli/bpo_demo.py ba query --task BA_TASK_ID --dataset day
python3 cli/bpo_demo.py ba editable --task BA_TASK_ID --dataset day
```

### Ba 编辑预览

用户说：

```text
把 2026-05-01 的 planned_headcount 改成 5，先预览
```

必须先生成 diff，不得直接 apply。

API：

```text
POST /api/ba/tasks/{ba_task_id}/diff
```

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

CLI：

```bash
python3 cli/bpo_demo.py ba diff \
  --task BA_TASK_ID \
  --dataset day \
  --patch examples/sample-data/patch_update_planned_headcount.json
```

### Ba 应用编辑

用户说：

```text
应用刚才的 diff，原因是演示修正
```

必须具备：

```json
{
  "diff_id": "diff-...",
  "reason": "非空修改原因"
}
```

API：

```text
POST /api/ba/tasks/{ba_task_id}/apply
```

CLI：

```bash
python3 cli/bpo_demo.py ba apply \
  --task BA_TASK_ID \
  --dataset day \
  --diff-id DIFF_ID \
  --reason "演示修正"
```

### Ba 构建和发布

用户说：

```text
构建这个 Ba 任务
发布这个任务
```

API：

```text
POST /api/ba/tasks/{ba_task_id}/build
POST /api/ba/tasks/{ba_task_id}/publish
```

CLI：

```bash
python3 cli/bpo_demo.py ba build --task BA_TASK_ID
python3 cli/bpo_demo.py ba publish --task BA_TASK_ID
```

发布失败时，应解释是否因为尚未 build 或 build 已过期。

## 参数规则

项目：

```text
demo_retail_ops
```

数据集：

```text
day
person
```

日期：

```text
YYYY-MM-DD
```

Ba 任务：

```text
ba-demo_retail_ops-xxxxxxxxxx
```

## 禁止处理的请求

如果用户要求以下操作，应拒绝并说明需要在系统治理边界内处理：

- 直接修改 B 层事实；
- 跳过 diff 直接改 Ba；
- 没有 reason 就 apply；
- 未 build 直接强制 publish；
- 执行任意 shell；
- 删除 SQLite 或运行目录；
- 修改源码；
- 连接真实外部系统；
- 发送外部消息；
- 处理真实客户文件。

## 返回风格

返回应简洁说明：

- 执行了哪个受控入口；
- 查询或操作了哪个项目、数据集、日期范围；
- 如果是 Ba 编辑，明确说明“只修改 Ba 任务切片，不反写 B 层”；
- 如果失败，返回中文错误原因和下一步建议。


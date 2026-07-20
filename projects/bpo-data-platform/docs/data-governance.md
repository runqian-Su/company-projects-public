# 数据治理说明

## 核心原则

平台将事实、操作和消费拆开。

```text
A 生成事实。
B 保存事实。
Ba 在任务切片内操作事实副本。
C 提供受控访问。
可视化消费已发布数据。
```

这样可以避免企业数据工具中常见的问题：脚本、页面和人员都在用不同方式修改同一张表，最后没人能说清数据口径。

## B 层治理

B 层是刚性事实层。

允许：

- A 层导入；
- A 层重新处理和受控覆盖；
- 只读查询；
- 受控导出；
- 复制事实到 Ba 任务切片。

不允许：

- 业务人员直接编辑；
- Agent 写入；
- 前端直接写 SQLite；
- Ba 反向同步；
- 没有入库日志的隐藏重算。

建议元数据：

```text
projects
processing_tasks
source_files
fact_import_logs
export_logs
person_day_records
day_records
business_day_records
budget_fact_records
```

治理目的：

- 每条事实有来源；
- 每次入库有任务；
- 每个源文件有 hash；
- 每次导出可追溯；
- 每个下游操作知道自己复制自哪个 B 层快照。

## Ba 层治理

Ba 层是任务级可控操作层。

允许：

- 每个操作任务创建一个 SQLite 切片；
- 从 B 层复制声明范围内的项目事实；
- 导入已确认的业务输入；
- 编辑前先生成 diff 预览；
- 带原因应用编辑并写审计日志；
- 重建二级表；
- 发布符合条件的数据版本。

不允许：

- 反写 B 层；
- 不经预览直接编辑；
- 编辑声明范围外的字段；
- 输入未完整时发布；
- 来源或输入指纹变化后继续发布旧构建；
- 一个 Ba 切片混放多个项目。

建议元数据：

```text
ba_tasks
ba_source_snapshot
ba_input_status
ba_edit_logs
ba_build_logs
ba_publish_logs
ba_release_manifest
```

治理目的：

- 操作有范围；
- 编辑可审计；
- 输入是显式的；
- 构建可复现；
- 发布结果有清单。

## C 层治理

C 层是应用与访问层。

允许：

- 展示项目和任务状态；
- 查询 B 层事实或已发布 Ba 结果；
- 触发被允许的编排动作；
- 生成发布包；
- 暴露 output API。

不允许：

- 独立持有另一套业务事实；
- 静默修改 B 或 Ba 数据；
- 高级看板绕过 Ba 发布状态直接读中间表；
- 前端执行任意本地脚本。

## Agent 与 CLI 治理

Agent 和 CLI 入口必须明确、保守。

默认能力：

```text
查询项目
查询日期范围
查询数据集记录
导出被允许的 workbook
查看任务状态
```

禁止能力：

```text
写数据库
修改源文件
触发原始数据处理
修改配置
发送外部消息
删除运行文件
执行任意 shell 命令
```

这样可以让 AI 参与查询和交付流程，同时避免它成为无边界的数据操作员。

## 发布治理

发布数据应带清单。

建议发布清单字段：

```text
release_id
project_id
ba_task_id
date_start
date_end
datasets
source_snapshot
input_fingerprint
build_fingerprint
created_at
file_hashes
quality_flags
```

发布包是操作层和消费层之间的边界。仪表盘、导出和外部复核应优先读取已发布数据，而不是临时中间文件。

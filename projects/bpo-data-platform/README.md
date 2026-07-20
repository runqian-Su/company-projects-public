# BPO 多层数据平台 Demo

> 企业现代业务系统架构 Demo：事实处理、刚性事实库、任务级操作层、本地平台、CLI、Agent Skill 与可视化同步。

## 项目定位

本项目是从真实企业 BPO 数据平台项目中抽象、脱敏出来的公开作品集 Demo。

它的目标不是公开完整生产系统，也不是公开真实客户交付包，而是展示如何把传统企业中的数据处理、数据治理、人工干预、发布交付和可视化消费，建模为一套分层清晰、边界明确、可本地部署的业务系统。

核心链路：

```text
原始业务文件
  -> A 层事实处理
  -> B 层刚性事实库
  -> Ba 层任务级可控操作层
  -> C 层本地数据管理平台
  -> CLI / Agent Skill / 可视化消费
```

## 这个 Demo 展示什么

- 如何拆分原始处理、稳定事实、受控编辑、发布交付和可视化展示。
- 如何保持事实层刚性，同时允许业务人员在任务切片内进行可审计干预。
- 如何在企业内部轻量部署场景中，用 SQLite 支撑数据底座、任务切片和本地可视化池。
- 如何设计 CLI 和 Agent Skill 入口，让 AI 可以查询和导出，但不能绕过权限直接改库。
- 如何用“中心处理服务器 + 客户端本地 SQLite 可视化池”的方式支持低频、少客户端的内部看板场景。

## 分层架构

```text
A 层：项目级原始数据处理层
  - 图片、Excel、考勤记录、业务记录
  - OCR、解析、清洗、标准化
  - 生成标准事实对象并写入 B 层

B 层：刚性事实数据底座
  - 中心 SQLite 事实库
  - 项目注册、任务记录、源文件 hash、入库日志
  - 稳定的个人/日/业务事实
  - 作为 Ba、CLI、Skill、API 和导出服务的只读来源

Ba 层：任务级可控操作层
  - 每个操作任务一个独立 SQLite 切片
  - 从 B 层复制事实
  - 支持受控编辑、输入导入、重算、审计日志和发布
  - 不允许反写 B 层
  - `ba_task_id` 封装一次面向业务交付的受控版本

层间衔接编排层
  - 运行 A->B、B->Ba、Ba 构建、Ba 发布、C 导出等单元
  - 负责调度、快照、日志和校验
  - 不拥有业务数据模型

C 层：本地数据管理平台
  - FastAPI 后端
  - React/Vite 前端
  - 项目总览、任务管理、查询、导出、发布包 API
  - 当前 Demo 提供 API 契约，不启动 Web 服务

CLI / Agent Skill
  - 只读查询和受控导出
  - 不执行任意 shell
  - 不直接写 B 层数据库

可视化消费层
  - 中心处理服务器作为主数据源
  - 客户端本地 SQLite 作为可视化池
  - 低频同步、本地聚合、仪表盘展示
```

## Ba 任务为什么是核心操作对象

在这个 Demo 中，B 层保存“事实是什么”，但业务交付通常不是直接消费一组原始事实，而是消费一个已经声明范围、完成必要干预、通过构建检查并发布的任务版本。

因此 Ba 任务是面向业务交付的最高操作抽象，封装一次从事实复制、任务级修正、构建、审计到发布消费的受控版本。一个 Ba 任务同时包含：

- 从 B 层复制而来的事实快照；
- 项目、日期、数据集等任务范围；
- 任务内可控编辑、外部输入和修改原因；
- diff/apply 审计记录；
- 二级表或汇总结果的构建状态；
- 发布状态和下游消费边界。

也就是说，Ba 不是“给 B 层补一个人工编辑入口”，而是把一次分析、修正、构建、发布和交付封装成一个可追溯的业务任务。C 层 API、Agent Skill 和可视化同步都应该围绕已发布的 Ba 任务工作，而不是绕过 Ba 直接读取 B 层作为最终口径。

## 公开 Demo 边界

本仓库应只保留脱敏后的通用结构和示例。

可以包含：

- 架构说明文档；
- 通用代码骨架；
- 示例 SQLite schema；
- 伪造样例数据；
- 示例配置文件；
- Demo CLI 和 API 契约。

不应包含：

- 真实客户名称；
- 真实 Excel、图片、Word、PDF、ZIP 交付包；
- 真实员工姓名、手机号、账号、考勤记录或业务金额；
- 外部推送地址、访问密钥、口令、认证凭证或本机绝对路径；
- 生产运行日志、运行时数据库、缓存和生成输出。

## 快速运行

进入项目目录：

```bash
cd company-projects-public/projects/bpo-data-platform
```

初始化 B 层事实库、Ba 元信息库和合成数据：

```bash
python3 cli/bpo_demo.py init-db
```

这条命令会读取 `examples/raw-input/` 下的合成原始 CSV/JSON，经过 A 层清洗、类型转换、基础校验和源文件 hash 记录后写入 B 层事实表。

也可以单独运行 A -> B 管线：

```bash
python3 cli/bpo_demo.py a run
```

查询 B 层项目和日期范围：

```bash
python3 cli/bpo_demo.py b projects
python3 cli/bpo_demo.py b date-range --project demo_retail_ops
```

创建 Ba 任务切片：

```bash
python3 cli/bpo_demo.py ba create-task \
  --project demo_retail_ops \
  --date-start 2026-05-01 \
  --date-end 2026-05-03
```

生成编辑预览、应用编辑、构建并发布：

```bash
python3 cli/bpo_demo.py ba diff \
  --task ba-demo_retail_ops-xxxxxxxxxx \
  --dataset day \
  --patch examples/sample-data/patch_update_planned_headcount.json

python3 cli/bpo_demo.py ba apply \
  --task ba-demo_retail_ops-xxxxxxxxxx \
  --dataset day \
  --diff-id diff-xxxxxxxxxxxxxxxx \
  --reason "演示任务切片内规划人力修正"

python3 cli/bpo_demo.py ba build --task ba-demo_retail_ops-xxxxxxxxxx
python3 cli/bpo_demo.py ba publish --task ba-demo_retail_ops-xxxxxxxxxx
```

运行时 SQLite 会生成在 `examples/runtime/`，该目录已被 `.gitignore` 排除。

启动最小 C 层 API：

```bash
python3 src/c_platform/run_api.py
```

默认地址：

```text
http://127.0.0.1:8787
```

示例：

```bash
curl http://127.0.0.1:8787/api/health
curl http://127.0.0.1:8787/api/projects
curl "http://127.0.0.1:8787/api/b-layer/demo_retail_ops/date-range"
```

## 目录结构

```text
bpo-data-platform/
  README.md
  docs/
    architecture.md
    ba-task-abstraction.md
    data-governance.md
    anonymization-plan.md
  src/
    a_layer/
    b_layer/
    ba_layer/
    c_platform/
      api_contract.md
  cli/
  skills/
    bpo-data-platform-agent/
  visualization/
    sync_contract.md
    sync_release.py
  examples/
    raw-input/
    config/
    sample-data/
```

## 当前状态

当前已完成第三版增强：A 层合成原始输入处理、B 层只读查询、Ba 任务级操作、diff/apply/build/publish、统一 CLI、C 层 API 契约、最小 FastAPI endpoint、脱敏版 Agent Skill 设计稿，以及可视化层本地 SQLite 同步 Demo。前端暂保留为架构边界说明。

可视化层同步说明见：

```text
visualization/README.md
visualization/sync_contract.md
```

C 层接口契约见：

```text
src/c_platform/api_contract.md
docs/c-layer-api-contract.md
```

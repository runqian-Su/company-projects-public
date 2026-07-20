# 可视化层说明

本目录展示“中心处理服务器 + 客户端本地 SQLite 可视化池”的最小实现思路。

关键边界：

```text
B 层是刚性事实底座，不是看板消费口。
Ba 层负责任务级操作、构建和发布。
可视化层只同步当前已发布 Ba 任务的数据。
客户端本地 SQLite 只是展示缓存，不是主数据源。
```

## 同步链路

```text
C 层 API
  GET /api/releases/{project_id}/current
        |
        v
  当前已发布 ba_task_id
        |
        v
  GET /api/ba/tasks/{ba_task_id}/records?dataset=day
  GET /api/ba/tasks/{ba_task_id}/records?dataset=person
        |
        v
客户端本地 SQLite 可视化池
```

## 文件

```text
sync_contract.md       同步契约和治理边界
sync_release.py        最小同步脚本
```

## 使用

先启动 C 层 API，并完成一次 Ba build/publish。

```bash
cd company-projects-public/projects/bpo-data-platform
python3 src/c_platform/run_api.py
```

然后在另一个终端同步当前发布结果：

```bash
python3 visualization/sync_release.py \
  --api-base http://127.0.0.1:8787 \
  --project demo_retail_ops \
  --db examples/runtime/client_visualization_pool.sqlite
```

同步后，本地 SQLite 包含：

```text
sync_meta
released_tasks
day_records
person_records
```

这些表只服务展示和本地筛选，不允许回写 B 或 Ba。


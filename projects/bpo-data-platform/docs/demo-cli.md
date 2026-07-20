# Demo CLI 使用说明

本 Demo 的 CLI 用来展示 B 层和 Ba 层的数据治理边界。

## 初始化

```bash
cd company-projects-public/projects/bpo-data-platform
python3 cli/bpo_demo.py init-db
```

初始化会在 `examples/runtime/` 下生成：

```text
b_layer.sqlite
ba_meta.sqlite
```

这些都是运行时文件，不进入 Git。

初始化过程会自动执行一次 A -> B 合成事实处理管线：

```text
examples/raw-input/raw_day_records.csv
examples/raw-input/raw_person_day_records.json
  -> A 层清洗、类型转换、基础校验、源文件 hash
  -> B 层 demo_day_records / demo_person_day_records
```

## A 层合成处理

单独运行 A -> B 管线：

```bash
python3 cli/bpo_demo.py a run
```

A 层会做四件事：

- 读取合成原始 CSV/JSON；
- 清洗文本字段并转换整数、浮点数；
- 校验项目、日期、重复主键和 person/day 对应关系；
- 写入 B 层事实表，并记录处理任务与源文件 hash。

## B 层只读查询

查询项目：

```bash
python3 cli/bpo_demo.py b projects
```

查询日期范围：

```bash
python3 cli/bpo_demo.py b date-range --project demo_retail_ops
```

查询日数据：

```bash
python3 cli/bpo_demo.py b query \
  --project demo_retail_ops \
  --dataset day \
  --date-start 2026-05-01 \
  --date-end 2026-05-03
```

B 层命令只读，不修改业务数据。

## Ba 层任务级操作

创建任务：

```bash
python3 cli/bpo_demo.py ba create-task \
  --project demo_retail_ops \
  --date-start 2026-05-01 \
  --date-end 2026-05-03
```

查询任务记录：

```bash
python3 cli/bpo_demo.py ba query \
  --task ba-demo_retail_ops-xxxxxxxxxx \
  --dataset day
```

查看可编辑字段：

```bash
python3 cli/bpo_demo.py ba editable \
  --task ba-demo_retail_ops-xxxxxxxxxx \
  --dataset day
```

生成 diff 预览：

```bash
python3 cli/bpo_demo.py ba diff \
  --task ba-demo_retail_ops-xxxxxxxxxx \
  --dataset day \
  --patch examples/sample-data/patch_update_planned_headcount.json
```

应用 diff：

```bash
python3 cli/bpo_demo.py ba apply \
  --task ba-demo_retail_ops-xxxxxxxxxx \
  --dataset day \
  --diff-id diff-xxxxxxxxxxxxxxxx \
  --reason "演示任务切片内规划人力修正"
```

构建并发布：

```bash
python3 cli/bpo_demo.py ba build --task ba-demo_retail_ops-xxxxxxxxxx
python3 cli/bpo_demo.py ba publish --task ba-demo_retail_ops-xxxxxxxxxx
```

## 治理边界

- Ba 从 B 层复制事实，但不反写 B 层。
- `diff` 只生成预览，不修改事实表。
- `apply` 必须提供有效 `diff_id` 和修改原因。
- `publish` 必须在当前任务成功 `build` 后执行。
- CLI 不提供任意 shell 入口，不包含外部消息发送能力。

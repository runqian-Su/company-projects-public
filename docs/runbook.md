# 运行索引

## BPO 数据平台

```bash
cd projects/bpo-data-platform
python3 cli/bpo_demo.py init-db
python3 cli/bpo_demo.py b projects
python3 cli/bpo_demo.py ba create-task --project demo_retail_ops --date-start 2026-05-01 --date-end 2026-05-03
```

## 财务应收对象库

```bash
cd projects/finance-ar-object-platform
python3 cli/finance_ar_demo.py init-db
python3 cli/finance_ar_demo.py verify --as-of-date 2026-05-31
```

## 招投标 Agent 工作流

```bash
cd projects/tender-agent-workflow
python3 cli/tender_demo.py v1-run
python3 cli/tender_demo.py v2-cluster
```

## 考勤脏数据管线

```bash
cd projects/attendance-dirty-data-pipeline
python3 scripts/run_demo.py run
```

## 方案生成 Skill

```bash
cd projects/proposal-generation-skill
python3 scripts/run_demo.py validate
python3 scripts/run_demo.py render-demo
```

## 猎头推荐报告 Skill

```bash
cd projects/talent-report-skill
python3 scripts/run_demo.py compose
python3 scripts/run_demo.py validate
python3 scripts/run_demo.py render-preview
```

## 说明

所有公开 Demo 均使用合成输入。运行产物默认写入各项目 `examples/runtime/`，该目录由 `.gitignore` 排除。


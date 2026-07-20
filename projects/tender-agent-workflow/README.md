# 招投标 Agent 编排 Demo

> Agent Workflow Demo：从招投标候选发现、硬门控、字段抽取、能力匹配，到多 worker 集群汇总交付。

## 项目定位

本项目是从真实招投标线索处理项目中抽象、脱敏出来的公开作品集 Demo。

它的重点不是展示爬虫能力，而是展示如何把一个容易失控的 Agent 任务拆成有边界、有门控、有状态、有交付口径的工作流。

真实项目中形成过两代编排：

- **V1 多 Skill 编排**：发现、字段抽取、分析、推送分别由独立 Skill 承担，主编排只负责调度、报告和状态。
- **V2 Agent 集群编排**：多个 worker agent 并行运行，各自产出标准记录，主 agent 负责汇总、去重、失败策略和最终交付。

## 这个 Demo 展示什么

- 如何把 Agent 任务拆成可复用 Skill；
- 如何用标题/详情硬门控控制线索质量；
- 如何把字段抽取结果转成固定交付结构；
- 如何对候选线索做能力匹配和优先级评分；
- 如何用主 agent 汇总多个 worker 的输出并去重；
- 如何避免“一个 Agent 自由发挥到底”的不可控模式。

## 架构概览

```text
V1 多 Skill 编排

discovery-open / discovery-webbridge
  -> hard gate
  -> field extract
  -> capability analysis
  -> push preview
  -> pipeline report
```

```text
V2 Agent 集群编排

worker A   worker B   worker C   worker A1
   |          |          |          |
   v          v          v          v
final_records from each worker
   -> master merge
   -> dedupe
   -> quality summary
   -> delivery preview
   -> cluster report
```

## 快速运行

进入项目目录：

```bash
cd company-projects-public/projects/tender-agent-workflow
```

运行 V1 多 Skill 编排 Demo：

```bash
python3 cli/tender_demo.py v1-run
```

运行 V2 Agent 集群编排 Demo：

```bash
python3 cli/tender_demo.py v2-cluster
```

查看合成输入：

```bash
python3 cli/tender_demo.py show-samples
```

运行时报告会生成在 `examples/runtime/`。

## 目录结构

```text
tender-agent-workflow/
  README.md
  cli/
  docs/
  examples/
    sample-data/
    runtime/
  src/
    tender_workflow/
```

## 公开 Demo 边界

本仓库只保留脱敏后的通用结构和合成数据。

不包含：

- 真实客户、公司、销售或项目名称；
- 真实招标网站登录态、浏览器凭据、验证码处理或浏览器会话；
- 真实机器人地址、访问密钥或接口凭据；
- 真实 SQLite、Excel、PDF、ZIP、截图或运行报告；
- 真实内部 Agent 路径和本机绝对路径。

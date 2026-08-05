# 财务应收对象库 Demo

> 数据建模 Demo：从应收明细到集团、主体、往来对象、单据号和应收余额事实。

## 项目定位

本项目是从真实财务应收分析项目中抽象、脱敏出来的公开作品集 Demo。

它的重点不是生成一张财务报表，而是展示如何把原始应收明细建模为可查询、可汇总、可校验的多层业务对象库。

核心链路：

```text
合成应收明细
  -> L1 集团
  -> L2 主体
  -> L3 往来对象
  -> L4 应收来源单据号
  -> Fact 应收余额事实
  -> 汇总一致性验证
```

## 这个 Demo 展示什么

- 如何把行级财务明细抽象成多层对象；
- 如何区分“对象层”和“分析事实”；
- 如何用对象级命中规则处理明细展开；
- 如何验证集团、主体、往来对象、单据号之间的余额口径一致；
- 如何用只读 CLI 查询对象库，而不是反复读取原始表格。

## 项目节奏与 AI-native 工作方式

真实项目中的核心对象模型和第一条可运行链路是在约两个小时内完成的：先识别“集团、主体、往来对象、单据号、应收事实”的稳定结构，再借助 AI 协作快速生成导入、建表、查询和汇总验证代码。

后续迭代重点不在继续堆功能，而在把模型做成可交付系统：补齐口径校验、异常视图、对象查询、导出、CLI、Skill 和本地平台入口。这个过程体现的是用业务建模先压住复杂度，再用 AI 放大实现速度。

## 核心建模口径

```text
L1 集团：DemoCorp Group
L2 主体：会计主体
L3 往来对象：主体 + 客户
L4 单据号对象：主体 + 客户 + 应收来源单据号
Fact：挂在 L4 单据号对象上的应收余额事实
```

本 Demo 的关键规则：

```text
余额不是行级过滤条件，而是 L4 单据号对象命中条件。
只要某个 L4 单据号对象下任意明细存在应收余额，
该 L4 对象命中后，其下全部明细都会进入事实明细。
```

这对应真实财务数据处理中常见的情况：一个单据号对象下面可能有多条明细，有些行余额为空，但它们仍然属于同一个被命中的业务对象。

## 快速运行

进入项目目录：

```bash
cd company-projects-public/projects/finance-ar-object-platform
```

初始化对象库并导入合成数据：

```bash
python3 cli/finance_ar_demo.py init-db
```

查询汇总：

```bash
python3 cli/finance_ar_demo.py summary --as-of-date 2026-05-31
```

查询主体余额：

```bash
python3 cli/finance_ar_demo.py entity-balances --as-of-date 2026-05-31
```

查询往来对象余额：

```bash
python3 cli/finance_ar_demo.py counterparty-balances --as-of-date 2026-05-31
```

查询单据号余额：

```bash
python3 cli/finance_ar_demo.py document-balances --as-of-date 2026-05-31
```

查询某个单据号对象下全部明细：

```bash
python3 cli/finance_ar_demo.py document-lines \
  --as-of-date 2026-05-31 \
  --entity-name "Demo Entity A" \
  --customer-name "Customer Alpha" \
  --source-doc-no "AR-2026-001"
```

运行一致性验证：

```bash
python3 cli/finance_ar_demo.py verify --as-of-date 2026-05-31
```

运行时 SQLite 会生成在 `examples/runtime/`，该目录已被 `.gitignore` 排除。

## 目录结构

```text
finance-ar-object-platform/
  README.md
  cli/
  docs/
  examples/
    raw-input/
  src/
    object_model/
```

## 公开 Demo 边界

本仓库只保留脱敏后的通用结构和合成数据。

不包含：

- 真实公司、客户、人员、项目名称；
- 真实 Excel、SQLite、PDF、ZIP 或导出文件；
- 真实应收金额和财务明细；
- 外部系统连接和消息推送能力。

# C 层 API 契约说明

C 层是本地数据管理平台的访问入口。当前 Demo 已提供最小 FastAPI endpoint，并保留接口契约用于说明未来前端、CLI、Agent Skill 和可视化层应该如何接入。

契约正文见：

```text
src/c_platform/api_contract.md
```

## 契约覆盖范围

- 健康检查与项目列表；
- A -> B 合成事实处理触发；
- B 层只读日期范围和记录查询；
- Ba 任务创建、查询、editable；
- Ba diff、apply、logs、build、publish；
- 当前发布结果查询。

## 核心边界

```text
A 层是常规写 B 的唯一入口。
B 层对 C 层默认只读。
Ba 只能复制 B，不能反写 B。
Ba 编辑必须 diff -> apply。
Ba 发布必须 build 后执行。
高级看板和交付包应读取已发布 Ba 结果。
```

## 为什么 V3 只做契约

这个作品集项目的重点是企业数据治理架构，而不是 Web 框架实现。

因此 V3 先用 API 契约明确 C 层职责，并只补最小 endpoint：

- 前端应该调用哪些能力；
- Agent Skill 可以调用哪些能力；
- 哪些动作是受控写入；
- 哪些动作必须保持只读；
- 哪些能力明确禁止。

后续如果需要展示更完整的应用形态，可以在该契约之上补最小 FastAPI 实现。

## 最小 FastAPI 实现

入口：

```text
src/c_platform/app.py
src/c_platform/run_api.py
```

启动：

```bash
python3 src/c_platform/run_api.py
```

默认监听：

```text
http://127.0.0.1:8787
```

实现范围：

- 健康检查；
- 初始化 demo；
- 项目列表；
- A -> B 合成处理；
- B 层日期范围与记录查询；
- Ba 创建任务、查询、editable、diff、apply、logs、build、publish；
- 当前发布结果查询。

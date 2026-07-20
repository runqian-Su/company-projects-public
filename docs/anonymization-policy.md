# 脱敏原则

## 总原则

公开目录只展示结构、机制和合成样例，不展示真实业务数据。

允许保留：

- 抽象后的架构说明；
- 脱敏 Demo 代码；
- 合成 CSV/JSON/Markdown；
- 通用规则、校验逻辑和运行入口；
- 与真实业务无关的示例名称。

不允许保留：

- 真实客户、公司、人员、候选人、销售和项目名称；
- 真实 Excel、Word、PDF、PPT、图片、音频、压缩包、SQLite 或数据库文件；
- 真实金额、考勤、简历、访谈、财务明细和客户材料；
- 本机绝对路径、内部 Agent 路径、内部域名和运行日志；
- 机器人地址、访问密钥、密码、接口凭据或外部系统连接信息。

## 命名规则

公开 Demo 使用合成名称：

```text
公司：DemoCorp
员工：EMP-001 / Demo Alice
客户：Demo Client / Demo Buyer
候选人：Demo Candidate
项目：demo_retail_ops
来源：synthetic-open / device_log / manual_import
```

## runtime 目录

各项目的 `examples/runtime/` 只保留 `.gitkeep`。

运行 Demo 后生成的报告、HTML、JSON 或预览文件属于运行产物，不提交到公开仓库。


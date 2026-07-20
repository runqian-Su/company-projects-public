# Skills 目录说明

本目录用于放置脱敏版 Agent Skill 设计稿。

当前包含：

```text
bpo-data-platform-agent/
  SKILL.md
```

它不是生产环境 Skill，也不连接真实外部系统。它的作用是展示 Agent 如何在 BPO 多层数据平台中作为受控入口：

- 优先调用 C 层 API；
- API 不可用时使用白名单 CLI；
- 默认只读 B 层；
- Ba 编辑必须遵守 diff -> apply -> build -> publish；
- 不执行任意 shell；
- 不发送外部消息；
- 不处理真实客户文件。


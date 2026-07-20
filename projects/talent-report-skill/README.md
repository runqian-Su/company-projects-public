# 猎头推荐报告 Skill Demo

> 轻量补充 Demo：用标准化 `report.json` 和模板渲染边界，降低 AI 输出不稳定和推荐报告幻觉。

## 项目定位

本项目是从真实猎头推荐报告 Skill 中抽象、脱敏出来的公开作品集 Demo。

它不是主案例，也不强调复杂技术。它更像一个“AI 作为前端自动化”的例子：AI 负责把简历事实和访谈洞察整理成标准报告对象，后续渲染器只消费这个对象，不再自由发挥。

核心价值：

- 把简历抽取、访谈洞察、报告合成和模板渲染拆开；
- 用 `resume.raw.json` 保存事实层；
- 用 `insight.json` 保存分析层；
- 用 `report.json` 作为唯一正式展示对象；
- 用模板渲染消费 `report.json`，降低格式漂移和幻觉。

## 链路结构

```text
resume.raw.json
  -> transcript.json / insight.json
  -> report.json
  -> Markdown / Word 模板渲染
```

公开版只保留合成 JSON 和 Markdown 预览渲染，不包含真实简历、音频、Word 模板或候选人信息。

## 快速运行

进入项目目录：

```bash
cd company-projects-public/projects/talent-report-skill
```

合成标准报告对象：

```bash
python3 scripts/run_demo.py compose
```

校验 `report.json`：

```bash
python3 scripts/run_demo.py validate
```

渲染 Markdown 预览：

```bash
python3 scripts/run_demo.py render-preview
```

运行结果默认写入 `examples/runtime/`，该目录已被 `.gitignore` 排除。

## 公开 Demo 边界

不包含：

- 真实候选人姓名、简历、音频、访谈记录和联系方式；
- 真实 Word 模板、logo、图片或 docx 产物；
- 真实外部转写、OCR 或模型接口；
- 真实本地路径、内部运行目录和接口凭据。


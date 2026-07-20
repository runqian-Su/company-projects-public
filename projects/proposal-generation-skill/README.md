# 方案生成 Skill Demo

> 受约束内容生产 Demo：用内建资产库、模板框架和结构化校验，提高方案产出的风格一致性，并降低 AI 幻觉和执行链路不稳定。

## 项目定位

本项目是从真实政企营销方案生成 Skill 中抽象、脱敏出来的公开作品集 Demo。

它的重点不是让 AI 从零自由写一份方案，而是把方案生产拆成可控链路：

```text
结构模式
  -> 资产库
  -> 行业叙述库
  -> 模板注册表
  -> deck JSON
  -> validate
  -> HTML/PDF 渲染
  -> render report
```

公开版只保留合成资产、合成 deck 和 HTML 预览渲染，不包含真实公司素材、真实客户案例、真实图片和 PDF 产物。

## 这个 Demo 展示什么

- 如何用资产 registry 固定公司介绍、资质、案例等可复用内容；
- 如何用结构模式约束方案章节，而不是每次自由发挥；
- 如何用模板 registry 限制页面类型和字段契约；
- 如何让行业页只能从内建行业叙述库取数，降低幻觉；
- 如何在渲染前做 validate，避免缺模板、缺资产、章节不一致；
- 如何生成 render report，让执行链路可检查、可复盘。

## 快速运行

进入项目目录：

```bash
cd company-projects-public/projects/proposal-generation-skill
```

校验样例 deck：

```bash
python3 scripts/run_demo.py validate
```

渲染 HTML 预览：

```bash
python3 scripts/run_demo.py render-demo
```

查看内建 registry 摘要：

```bash
python3 scripts/run_demo.py inspect
```

运行结果默认写入 `examples/runtime/`，该目录已被 `.gitignore` 排除。

## 目录结构

```text
proposal-generation-skill/
  README.md
  assets/
    registry/
    structure_modes/
    industry_narratives/
    templates/
  docs/
  examples/
    decks/
    runtime/
  scripts/
  src/
    proposal_skill/
```

## 公开 Demo 边界

不包含：

- 真实公司介绍、资质、荣誉、客户案例和 logo；
- 真实 PPT、PDF、图片、截图或渲染产物；
- 真实客户材料、内部素材库和本地绝对路径；
- 外部模型接口、真实接口凭据或浏览器自动化依赖。


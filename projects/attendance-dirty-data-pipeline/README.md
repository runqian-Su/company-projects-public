# 考勤脏数据处理 Pipeline Demo

> 数据清洗 Demo：把多来源、非标准、带异常的考勤输入收敛为可复核的标准日记录和人员汇总。

## 项目定位

本项目是从真实集团考勤处理项目中抽象、脱敏出来的公开作品集 Demo。

它的重点不是“做一个考勤系统”，而是展示如何处理企业环境里非常常见的脏数据：

- 文件来源不一致；
- 字段命名不一致；
- 人员姓名存在空格、别名、大小写或编码差异；
- 同一天存在重复打卡、缺卡、非法时间；
- 请假、外出、排休等状态需要覆盖普通打卡规则；
- 白名单外人员不能进入最终交付；
- 每条异常都要能解释原因。

## 这个 Demo 展示什么

- 如何把原始行清洗成标准 `employee_id + date + punches`；
- 如何用别名表和白名单做身份归一；
- 如何合并多个来源的同日打卡；
- 如何识别重复、缺失、非法和非白名单记录；
- 如何让请假/外出状态覆盖迟到、早退、缺卡等打卡异常；
- 如何生成可复核的异常报告和人员汇总。

## 核心链路

```text
合成脏 CSV/JSON
  -> 字段归一
  -> 身份解析
  -> 白名单过滤
  -> 打卡时间清洗
  -> 多来源合并
  -> 请假/外出状态覆盖
  -> 规则判定
  -> 标准日记录 + 异常报告 + 人员汇总
```

## 快速运行

进入项目目录：

```bash
cd company-projects-public/projects/attendance-dirty-data-pipeline
```

运行完整 Demo：

```bash
python3 scripts/run_demo.py run
```

查看合成输入：

```bash
python3 scripts/run_demo.py show-samples
```

运行结果默认写入 `examples/runtime/`，该目录已被 `.gitignore` 排除。

## 目录结构

```text
attendance-dirty-data-pipeline/
  README.md
  docs/
  examples/
    sample-data/
    runtime/
  scripts/
  src/
    attendance_pipeline/
```

## 公开 Demo 边界

本仓库只保留脱敏后的通用结构和合成数据。

不包含：

- 真实组织、人员、部门和项目名称；
- 真实业务 Excel、导出文件、截图或压缩包；
- 真实本地运行日志、打包产物或内部路径；
- 外部系统连接和真实接口凭据。

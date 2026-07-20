# 脱敏说明

## 保留内容

- 简历事实层、洞察层、展示层的对象边界；
- `report.json` schema 和校验逻辑；
- 合成样例与 Markdown 预览渲染。

## 移除内容

- 真实候选人、客户、公司、学校和联系方式；
- 真实简历、音频、Word 模板、图片和输出报告；
- 外部转写、OCR、模型接口和接口凭据；
- 本机绝对路径和内部运行产物。

## 合成命名规则

```text
候选人：Demo Candidate
公司：Demo Group / Demo Tech
岗位：Demo Operations Director
文件：resume.raw.json / insight.json / report.json
```


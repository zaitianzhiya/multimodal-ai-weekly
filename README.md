# 多模态AI每周发展摘要 (Multimodal AI Weekly Digest)

> 聚焦全球多模态AI领域，每周筛选 TOP 20 影响力事件，深度追踪视觉理解、图像生成、视频生成、语音音频、全模态统一架构、产业生态六大维度。
>
> 方法论继承自 [GitHub Weekly Curation](https://github.com/zaitianzhiya/github-weekly-digest) 的工程实践。

## 方法论

采用"多源信息采集 + 六维影响力评价 + AI 深度分析"的人机协作模式：

1. **多源信息采集：** 覆盖全球头部AI企业官方发布、学术预印本、科技媒体、行业评测（共 28 个信息源，11 个生态分组，5 个模态覆盖）
2. **交叉验证去重：** 同一事件在多个独立来源确认后才纳入
3. **六维影响力加权：** 技术突破度(25%) + 行业影响力(25%) + 生态价值(20%) + 模型能力(15%) + 商业信号(10%) + 时间敏感性(5%)
4. **AI 深度分析：** 每个 TOP 20 事件按"事件概述 → 关键数据 → 影响分析 → 下一步关注"结构展开
5. **模态交叉洞察：** 识别多个模态的融合趋势

## 领域范围

| 模态 | 说明 |
|------|------|
| 👁️ 视觉理解 | 图像/视频理解、OCR、视觉问答、视觉定位、视觉推理 |
| 🎨 图像生成 | 文生图、图生图、图像编辑、风格迁移、可控生成 |
| 🎬 视频生成 | 文生视频、图生视频、视频编辑、视频续写 |
| 🔊 语音音频 | 语音识别/合成、音乐生成、音频理解、声纹 |
| 🔄 全模态统一 | any-to-any模型、统一架构、跨模态融合 |

## 信息源体系

### Tier 1: 原始数据源（13 个）

| 类别 | 来源 | 采集方式 |
|------|------|---------|
| 美国科技巨头 | OpenAI / Google DeepMind / Anthropic / Meta AI | Web Search |
| 中国大模型企业 | DeepSeek / 通义千问 / 智谱AI | Web Search |
| 图像生成专精 | Midjourney / Black Forest Labs (FLUX) | Web Search |
| 视频生成专精 | 快手可灵(Kling) / Runway | Web Search |
| 学术界 | arXiv cs.CV (multimodal filter) | RSS |

### Tier 2: 引用数据源（15 个）

| 类别 | 来源 |
|------|------|
| 中国科技媒体 | 36氪 / 机器之心 / 量子位 / IT之家 / 雷锋网 |
| 英文科技媒体 | TechCrunch / The Verge / VentureBeat |
| 行业评测研究 | FutureAGI / Pandaily / IDC |
| 开源社区 | HuggingFace / GitHub |

## 六维影响力权重

| 维度 | 权重 | 说明 |
|------|------|------|
| **技术突破度** | 25% | 多模态理解/生成能力的本质提升程度 |
| **行业影响力** | 25% | 对多模态产业格局和主流技术路线的影响 |
| **生态价值** | 20% | 开源/API开放对开发者生态的增益 |
| **模型能力** | 15% | 在权威基准和实际体验中的表现水平 |
| **商业信号** | 10% | 融资/收购/人才/战略调整的意义 |
| **时间敏感性** | 5% | 事件的即时性和不可逆性 |

## 项目结构

```
multimodal-ai-weekly/
├── .github/workflows/
│   ├── weekly-digest.yml       # 每周一 18:47 CST 主工作流
│   └── watchdog.yml            # 周一 3 次补发检查
├── config/
│   ├── sources.yml             # 28 个信息源 + 11 个生态分组 + 5 模态覆盖
│   ├── keywords.yml            # 正/负向关键词 + 重点关注组织
│   └── quality.yml             # 六维评分 + 置信度 + 分类体系
├── prompts/
│   ├── weekly-deep.md          # 深度分析 Prompt（禁止裸术语/两层阅读）
│   ├── taxonomy.md             # 分类 + 评分规则
│   └── feedback-rules.md       # 反馈闭环
├── output/
│   └── YYYY-WNN.md              # 周报输出
├── feedback/                    # 读者反馈（注入 AI Prompt）
├── README.md
└── CLAUDE.md
```

## 部署

- 📋 GitHub Actions 每周一 UTC 10:47（北京时间 18:47）自动运行
- 🛡️ 看门狗 3 次检查补发
- 📬 反馈: 提交到 `feedback/YYYY-WNN.md`
- 🔄 频率: 每周一发布

## 相关项目

- [GitHub Weekly Digest](https://github.com/zaitianzhiya/github-weekly-digest) — 方法论源头
- [领域知识自动化收集评价存储部署发布-完整方法论](../领域知识自动化收集评价存储部署发布-完整方法论.md) — 通用方法论指南

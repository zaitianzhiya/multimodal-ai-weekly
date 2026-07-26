# CLAUDE.md — Multimodal AI Weekly Digest

This file provides guidance to Claude Code (claude.ai) when working with this repository.

## Project overview

**Multimodal AI Weekly Digest** (多模态AI每周发展摘要) is a weekly report covering global multimodal AI developments — vision understanding, image generation, video generation, audio/speech, and unified any-to-any architectures. It collects events from 28 information sources across 11 ecosystem groups, scores them on a 6-dimension impact scale, and publishes AI-generated Chinese deep analysis.

This project is a domain-specific application of the methodology from `github-weekly-digest`, sibling to `embodied-intelligence-weekly`. Both share identical Python code — only config differs.

## Architecture

```
28 sources → RealSearchCollector → Merge/Dedup → 6-dim Score → DeepAnalyzer (LLM) → MarkdownRenderer → GitHub Actions commit
     (11 ecosystems, Tier 1/2, 5 modalities)      |                 |                   |
                                                   v                 v                   v
                                              Confidence A/B/C/D  "No naked jargon"   weekly/YYYY-NN.md
                                                                   + modality markers
```

## Key modules

| Module | Path | Purpose |
|--------|------|---------|
| Collectors | `src/collectors/` | `base.py` (EventRecord, SourceCitation), `web_search.py` (RealSearchCollector) |
| Filters | `src/filters/` | `dedup.py`, `quality.py`, `scorer.py` |
| AI | `src/ai/` | `llm_client.py` (multi-provider), `deep_analyzer.py`, `feedback_loader.py` |
| Render | `src/render/` | `markdown_weekly.py` |
| Config | `config/` | `sources.yml` (28 sources, 11 ecosystems, 5 modalities), `keywords.yml`, `quality.yml` |
| Prompts | `prompts/` | `weekly-deep.md` (with modality markers), `taxonomy.md`, `feedback-rules.md` |
| Orchestrator | `src/main.py` | collect → merge → dedup → filter → score → AI → render |

## Quick start

```bash
pip install -r requirements.txt
python run.py --mode weekly                      # data-only
export GEMINI_API_KEY="your-key"
python run.py --mode weekly                      # with AI summaries
```

## Deployment

- **Workflow**: `.github/workflows/weekly-digest.yml` — cron `47 10 * * 1` (Mon 18:47 CST)
- **Watchdog**: `.github/workflows/watchdog.yml` — 3× Monday checks
- **Secrets needed**: `GH_TOKEN`, `GEMINI_API_KEY`
- **Concurrency group**: `multimodal-weekly`

## 6-dimension scoring + 6 category labels + 5 modality markers

| # | Category | Weight | Modality |
|---|----------|--------|----------|
| 1 | Vision Understanding | 25% Tech Breakthrough | 👁️ |
| 2 | Image Generation | 25% Industry Impact | 🎨 |
| 3 | Video Generation | 20% Ecosystem Value | 🎬 |
| 4 | Audio & Speech | 15% Model Capability | 🔊 |
| 5 | Omni Unified | 10% Business Signal | 🔄 |
| 6 | Industry/Ecosystem | 5% Time Sensitivity | 🏭 |

## Important notes

- **Code identical to embodied-intelligence-weekly**: Both projects share the same Python pipeline — only config files and prompts differ.
- **25 sources in 11 ecosystems** with **5 modality tags** — unique among the weekly digest family.
- **LLM graceful degradation**: Data-only reports on API key failure.

## Related projects

- `../github-weekly-digest/` — Methodology source
- `../embodied-intelligence-weekly/` — Same-format sibling (code-identical, config-different)
- `../领域知识自动化收集评价存储部署发布-完整方法论.md` — Universal methodology guide

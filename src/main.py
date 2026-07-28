"""Orchestrator: collect → filter → score → AI → render pipeline."""

import argparse
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

from src.collectors.base import EventRecord
from src.collectors.real_search import RealSearchCollector
from src.filters.dedup import Deduplicator
from src.filters.quality import QualityFilter
from src.filters.scorer import Scorer
from src.render.markdown_weekly import MarkdownRenderer

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    """Load all YAML config files and merge into one dict."""
    config: dict = {}
    for filename in ["sources.yml", "keywords.yml", "quality.yml"]:
        path = ROOT / "config" / filename
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            config.update(data)
    return config


def _auto_categorize(record: EventRecord, config: dict) -> list[str]:
    """Auto-classify based on title + description + keyword matching."""
    text = f"{record.title} {record.description}".lower()
    category_mapping = config.get("category_mapping", {})
    matched: list[str] = []
    for cat_id, keywords in category_mapping.items():
        if any(kw.lower() in text for kw in keywords):
            # Use category name from config
            cat_configs = config.get("categories", [])
            cat_name = cat_id
            for cc in cat_configs:
                if cc.get("id") == cat_id:
                    cat_name = cc.get("name", cat_id)
                    break
            matched.append(cat_name)
    return matched if matched else []


def _merge_records(records: list[EventRecord]) -> list[EventRecord]:
    """Merge records with same event_id, combining citation chains."""
    merged: dict[str, EventRecord] = {}
    for r in records:
        if r.event_id in merged:
            existing = merged[r.event_id]
            existing_keys = {c.source_key for c in existing.citations}
            for c in r.citations:
                if c.source_key not in existing_keys:
                    existing.citations.append(c)
            # Take the longer description
            if r.description and len(r.description) > len(existing.description or ""):
                existing.description = r.description
        else:
            merged[r.event_id] = r
    return list(merged.values())



def _generate_cn_titles(records: list[EventRecord]) -> None:
    """Generate Chinese titles for ALL event records via LLM batch translation.

    Strategy: LLM translates all events in batches (20 per call).
    Falls back to keyword pre-processing only if no LLM key is available.
    """
    import re

    # ── Preprocessing: longest-match-first keyword substitution ──
    _PREPROCESS: list[tuple[str, str]] = sorted([
        ("artificial intelligence", "AI"),
        ("data center", "数据中心"), ("Data Center", "数据中心"),
        ("DeepSeek", "DeepSeek"), ("OpenAI", "OpenAI"),
        ("Google", "谷歌"), ("Microsoft", "微软"),
        ("Amazon", "亚马逊"), ("Meta", "Meta"),
        ("NVIDIA", "英伟达"), ("Nvidia", "英伟达"),
        ("Apple", "苹果"), ("Tesla", "特斯拉"),
        ("Samsung", "三星"), ("Sony", "索尼"),
        ("China", "中国"), ("Chinese", "中国"),
        ("United States", "美国"), ("U.S.", "美国"),
        ("Japan", "日本"), ("European", "欧洲"), ("Europe", "欧洲"),
        ("AI model", "AI模型"), ("AI models", "AI模型"),
        ("large language model", "大语言模型"),
        ("foundation model", "基础模型"),
        ("parameter", "参数"), ("parameters", "参数"),
        ("research", "研究"), ("paper", "论文"),
        ("announced", "宣布"), ("released", "发布"),
        ("launched", "推出"), ("introduced", "推出"),
        ("LLM", "大模型"), ("GPU", "GPU"),
        ("open source", "开源"), ("open-source", "开源"),
    ], key=lambda x: -len(x[0]))

    for r in records:
        en = r.title.strip()
        cn = en
        for term, cn_term in _PREPROCESS:
            idx = 0
            while True:
                idx = cn.find(term, idx)
                if idx == -1:
                    break
                before_ok = idx == 0 or not cn[idx - 1].isalnum() and cn[idx - 1] != "'"
                after_ok = (idx + len(term) == len(cn)
                            or not cn[idx + len(term)].isalnum() and cn[idx + len(term)] != "'")
                if before_ok and after_ok:
                    cn = cn[:idx] + cn_term + cn[idx + len(term):]
                    idx += len(cn_term)
                else:
                    idx += 1
        cn = re.sub(r'\s{2,}', " ", cn).strip()
        r.title_cn = cn if cn != en else ""

    # ── LLM batch translation for ALL events ──
    try:
        from src.ai.llm_client import LLMClient
        client = LLMClient()
    except Exception:
        print("  [CN translate] No LLM key found — using keyword-only fallback")
        return

    BATCH_SIZE = 20
    id_to_cn: dict[str, str] = {}
    all_records = [r for r in records if r.title.strip()]

    for batch_start in range(0, len(all_records), BATCH_SIZE):
        batch = all_records[batch_start:batch_start + BATCH_SIZE]
        lines = [f"{j+1}. {r.title}" for j, r in enumerate(batch)]
        prompt = (
            "Translate these headlines into concise, fluent Chinese.\n"
            "Rules: keep technical acronyms (GPU/NPU/LLM/API/SDK) as-is.\n"
            "Return one line per number, format: N. 中文翻译\n\n"
            + "\n".join(lines)
        )
        try:
            result = client.chat(
                "You translate English headlines to fluent, concise Chinese. "
                "Preserve technical acronyms. Output format: N. Chinese translation.",
                prompt, temperature=0.1,
            )
            for line in result.strip().split("\n"):
                line = line.strip()
                parts = line.split(". ", 1)
                if len(parts) == 2 and parts[0].isdigit():
                    idx = int(parts[0]) - 1
                    if 0 <= idx < len(batch):
                        id_to_cn[batch[idx].event_id] = parts[1].strip()
        except Exception as e:
            print(f"  [CN translate] Batch {batch_start // BATCH_SIZE + 1} failed: {e}")
            continue

    for r in records:
        if r.event_id in id_to_cn and id_to_cn[r.event_id]:
            r.title_cn = id_to_cn[r.event_id]
    print(f"  [CN translate] LLM translated {len(id_to_cn)}/{len(all_records)} titles")


def run_weekly(config: dict):
    """Full weekly pipeline: collect from all Tier 1 + Tier 2 sources."""
    print(f"[Weekly] Starting pipeline — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    records: list[EventRecord] = []

    sources_cfg = config.get("sources", {})
    enabled_sources = {k: v for k, v in sources_cfg.items() if v.get("enabled", True)}

    print(f"[Weekly] Collecting from {len(enabled_sources)} sources...")

    for source_key, source_cfg in enabled_sources.items():
        try:
            collector = RealSearchCollector(config, source_key)
            collector.gh_token = os.environ.get("GH_TOKEN", "")
            items = collector.collect()
            for item in items:
                item.categories = _auto_categorize(item, config)
            records.extend(items)
            if items:
                print(f"  [{source_key}] {len(items)} items — {source_cfg.get('name', source_key)}")
        except Exception as e:
            print(f"  [{source_key}] FAILED: {e}")

    if not records:
        print("[Weekly] No records collected — check source configuration.")
        return

    # Merge + dedup
    merged = _merge_records(records)
    print(f"[Weekly] Merged: {len(merged)} unique events (from {len(records)} raw)")

    dedup = Deduplicator(str(ROOT / "data" / "state.json"))
    new_records, seen = dedup.deduplicate(merged)
    print(f"[Weekly] Dedup: {len(new_records)} new / {seen} already seen")

    if not new_records:
        print("[Weekly] All events already seen this cycle.")
        return

    # Filter + score
    qf = QualityFilter(config)
    scorer = Scorer(config)

    new_records = qf.filter(new_records)
    new_records = scorer.score(new_records)
    new_records.sort(key=lambda r: r.confidence_score, reverse=True)

    grade_counts = {}
    for r in new_records:
        g = r.confidence_grade
        grade_counts[g] = grade_counts.get(g, 0) + 1
    grade_str = ", ".join(f"{k}:{v}" for k, v in sorted(grade_counts.items()))
    print(f"[Weekly] Filtered+Scored: {len(new_records)} events — {grade_str}")

    # Generate Chinese titles (LLM batch translation with keyword preprocess)
    _generate_cn_titles(new_records)
    cn_count = sum(1 for r in new_records if r.title_cn)
    print(f"[Weekly] CN titles generated: {cn_count}/{len(new_records)}")

    # AI deep analysis
    deep_analysis = ""
    try:
        from src.ai.llm_client import LLMClient
        from src.ai.deep_analyzer import DeepAnalyzer

        client = LLMClient()
        analyzer = DeepAnalyzer(client, ROOT / "prompts")
        top_n = min(len(new_records), 15)
        deep_analysis = analyzer.analyze(new_records, top_n=top_n)
        print(f"[Weekly] AI deep analysis generated ({len(deep_analysis)} chars)")
    except Exception as e:
        print(f"[Weekly] AI skipped (will render data-only report): {e}")

    # Render
    renderer = MarkdownRenderer(str(ROOT / "output"))
    stats = {
        "本周采集": len(records),
        "去重后": len(new_records),
        "新事件": len(new_records),
        "可信度分布": grade_str,
        "独立生态覆盖": _eco_coverage(new_records),
    }
    renderer.render_weekly_report(new_records, deep_analysis=deep_analysis, stats=stats)

    print(f"[Weekly] ✅ Done — report written to output/")
    print(f"[Weekly] Top event: {new_records[0].title[:80] if new_records else 'N/A'}")


def _eco_coverage(records: list[EventRecord]) -> str:
    ecosystems: set[str] = set()
    for r in records:
        for c in r.citations:
            ecosystems.add(c.ecosystem)
    return f"{len(ecosystems)} ecosystems: {', '.join(sorted(ecosystems)[:8])}"


# ---- CLI entry ----

def main():
    parser = argparse.ArgumentParser(description="Weekly domain intelligence digest")
    parser.add_argument(
        "--mode", choices=["weekly", "daily"], default="weekly",
        help="Run mode: weekly (full pipeline) or daily (Tier 1 only)",
    )
    args = parser.parse_args()

    # Ensure root in path for absolute imports
    sys.path.insert(0, str(ROOT))

    config = load_config()
    print(f"[Main] Mode: {args.mode} | Sources: {len(config.get('sources', {}))}")

    if args.mode == "weekly":
        run_weekly(config)
    else:
        print("[Main] Daily mode not yet configured — use weekly.")


if __name__ == "__main__":
    main()

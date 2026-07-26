"""Markdown renderer — weekly report output."""

from datetime import datetime
from pathlib import Path

from src.collectors.base import EventRecord


class MarkdownRenderer:
    """Render weekly reports, event cards, and category indexes in Markdown."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_weekly_report(
        self,
        records: list[EventRecord],
        deep_analysis: str = "",
        stats: dict = None,
    ) -> str:
        """Generate the main weekly report Markdown file."""
        now = datetime.utcnow()
        week_str = now.strftime("%Y-W%V")

        lines = [
            "---",
            f"date: {now.strftime('%Y-%m-%d')}",
            "type: weekly-moc",
            f"week: {week_str}",
            f"total_events: {len(records)}",
            "---",
            "",
            f"# {week_str}",
            "",
            f"> 本期共收录 **{len(records)}** 个事件",
            f"> 生成时间: {now.strftime('%Y-%m-%d %H:%M')} UTC",
            "",
            "---",
            "",
        ]

        # AI deep analysis
        if deep_analysis:
            lines.append(deep_analysis)
            lines.extend(["", "---", ""])

        # Top N table
        top_n = min(len(records), 20)
        lines.append(f"## Top {top_n} 事件")
        lines.append("")
        lines.append("| # | 事件 | 组织 | 可信度 | 独立源 | 分类 |")
        lines.append("|---|------|------|--------|--------|------|")

        for i, r in enumerate(records[:top_n], 1):
            cats = " ".join(f"`{c}`" for c in r.categories[:3]) if r.categories else "-"
            lines.append(
                f"| {i} | {r.title[:50]} | {r.organization} | "
                f"{r.confidence_grade}({r.confidence_score:.0f}) | "
                f"{r.independent_ecosystems} | {cats} |"
            )

        lines.extend(["", "---", ""])

        # Categories
        lines.append("## 分类整理")
        lines.append("")
        cats = self._group_by_category(records)
        for cat, crecs in sorted(cats.items()):
            lines.append(f"### {cat}")
            lines.append("")
            lines.append("| # | 事件 | 组织 | 可信度 |")
            lines.append("|---|------|------|--------|")
            for i, r in enumerate(crecs, 1):
                lines.append(
                    f"| {i} | {r.title[:60]} | {r.organization} | "
                    f"{r.confidence_grade} |"
                )
            lines.append("")

        # Stats
        if stats:
            lines.extend(["---", "", "## 数据洞察", ""])
            for k, v in stats.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")

        # Feedback
        lines.extend([
            "---",
            "",
            "## 反馈",
            "",
            f"> 对本期周报有意见？请提交到 `feedback/{week_str}.md`",
            "> 格式：`- [x] 事件标题: 正确分类为 #分类 (理由)`",
            "> 标记为 `[x]` 表示已确认的永久规则",
            "",
            f"*本期自动生成 | {now.strftime('%Y-%m-%d')}*",
        ])

        content = "\n".join(lines)
        week_dir = self.output_dir / "weekly" / now.strftime("%Y")
        week_dir.mkdir(parents=True, exist_ok=True)
        (week_dir / f"{week_str}.md").write_text(content, encoding="utf-8")
        return content

    def _group_by_category(self, records: list[EventRecord]) -> dict[str, list[EventRecord]]:
        cats: dict[str, list[EventRecord]] = {}
        for r in records:
            for c in r.categories:
                cats.setdefault(c, []).append(r)
        uncat = [r for r in records if not r.categories]
        if uncat:
            cats["未分类"] = uncat
        return cats

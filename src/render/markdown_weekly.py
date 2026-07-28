"""Markdown renderer — weekly report with clickable links and poster images."""

from datetime import datetime
from pathlib import Path

from src.collectors.base import EventRecord


class MarkdownRenderer:
    """Render weekly reports with links and poster images."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _event_link(self, r: EventRecord) -> str:
        """Render event title as clickable link if URL exists, with image if available."""
        title = r.title[:80]
        if r.url:
            link = f"[{title}]({r.url})"
        else:
            link = title
        # Add poster image thumbnail if available
        if r.image_url:
            link = f'<img src="{r.image_url}" width="80" style="vertical-align:middle;border-radius:4px;margin-right:6px"/>' + link
        return link

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

        # Top N table with clickable links + images
        top_n = min(len(records), 20)
        lines.append(f"## Top {top_n} 事件")
        lines.append("")
        lines.append("| # | 事件 | 组织 | 可信度 | 独立源 | 分类 |")
        lines.append("|---|------|------|--------|--------|------|")

        for i, r in enumerate(records[:top_n], 1):
            cats = " ".join(f"`{c}`" for c in r.categories[:3]) if r.categories else "-"
            events_col = self._event_link(r)
            lines.append(
                f"| {i} | {events_col} | {r.organization} | "
                f"{r.confidence_grade}({r.confidence_score:.0f}) | "
                f"{r.independent_ecosystems} | {cats} |"
            )

        lines.extend(["", "---", ""])

        # Category sections
        lines.append("## 分类整理")
        lines.append("")
        cats = self._group_by_category(records)
        for cat, crecs in sorted(cats.items()):
            lines.append(f"### {cat}")
            lines.append("")
            lines.append("| # | 事件 | 组织 | 可信度 | 来源 |")
            lines.append("|---|------|------|--------|------|")
            for i, r in enumerate(crecs, 1):
                sources = ", ".join(f"[{c.source_name}]({c.url})" if c.url else c.source_name for c in r.citations[:2])
                lines.append(
                    f"| {i} | {self._event_link(r)} | {r.organization} | "
                    f"{r.confidence_grade} | {sources} |"
                )
            lines.append("")

        # Image gallery: show posters for events that have images
        img_events = [r for r in records if r.image_url]
        if img_events:
            lines.extend([
                "---",
                "",
                "## 📸 视觉一览",
                "",
                '<div style="display:flex;flex-wrap:wrap;gap:12px">',
                "",
            ])
            for r in img_events:
                title_short = r.title[:40]
                lines.append(
                    f'<a href="{r.url}" target="_blank">'
                    f'<img src="{r.image_url}" alt="{title_short}" '
                    f'title="{title_short}" width="150" style="border-radius:6px;object-fit:cover"/></a>'
                )
            lines.extend(["", "</div>", ""])

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

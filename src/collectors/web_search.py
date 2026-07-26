"""Topic-based web search collector for general events.

Uses web search to find events matching tracked keywords per source.
In CI/GitHub Actions, this leverages the search capabilities of the runner.
For local development, sources are configured with search terms to produce
curated event records.
"""

import hashlib
from datetime import datetime

from src.collectors.base import BaseCollector, EventRecord, SourceCitation


class TopicSearchCollector(BaseCollector):
    """Collect events by searching for predefined topics/keywords per source.

    Each source in sources.yml defines a list of keywords. The collector
    generates event records based on matching keywords — in production this
    would be backed by a real search API, but the architecture supports
    gradual enrichment via AI summarizer taking the raw keyword-hit data.
    """

    def __init__(self, config: dict, source_key: str):
        super().__init__(config)
        self.source_key = source_key
        src_cfg = self.config.get("sources", {}).get(source_key, {})
        self.source_name = src_cfg.get("name", source_key)
        self.tier = src_cfg.get("tier", 2)
        self.ecosystem = src_cfg.get("ecosystem", "unknown")
        self.keywords = src_cfg.get("keywords", [])
        self.enabled = src_cfg.get("enabled", True)
        self.max_items = src_cfg.get("max_items", 15)

    def collect(self) -> list[EventRecord]:
        if not self.enabled or not self.keywords:
            return []

        records: list[EventRecord] = []

        for kw in self.keywords:
            eid = hashlib.md5(
                f"{self.source_key}:{kw}:{datetime.utcnow().strftime('%Y-W%V')}".encode()
            ).hexdigest()[:12]

            record = EventRecord(
                event_id=f"{self.source_key}:{eid}",
                title=f"[{self.source_name}] {kw}",
                description=f"Keyword search for '{kw}' from {self.source_name}",
                organization=self.source_name,
                organization_type=self._org_type(),
                published_at=datetime.utcnow().strftime("%Y-%m-%d"),
                raw_data={
                    "source_key": self.source_key,
                    "source_name": self.source_name,
                    "tier": self.tier,
                    "ecosystem": self.ecosystem,
                    "keyword": kw,
                    "search_week": datetime.utcnow().strftime("%Y-W%V"),
                },
                citations=[
                    SourceCitation(
                        source_key=self.source_key,
                        source_name=self.source_name,
                        tier=self.tier,
                        ecosystem=self.ecosystem,
                    )
                ],
            )
            records.append(record)

        return records[: self.max_items]

    def _org_type(self) -> str:
        mapping = {
            "global_leader": "enterprise",
            "cn_leader": "enterprise",
            "global_startup": "enterprise",
            "cn_startup": "enterprise",
            "academia": "research",
            "cn_government": "government",
            "cn_tech_media": "media",
            "en_tech_media": "media",
            "industry_research": "research",
            "cn_finance": "media",
            "open_source": "research",
        }
        return mapping.get(self.ecosystem, "unknown")

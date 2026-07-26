"""Real web search collector — fetches actual news events via multiple sources.

Sources (all free, no extra API key needed in CI):
  1. DuckDuckGo News search — for recent news articles
  2. arXiv API — for academic papers (official API, free)
  3. GitHub Search API — for repos (uses GH_TOKEN from env)

Falls back gracefully to filtered keyword skeletons on any failure.
"""

import hashlib
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

import requests

from src.collectors.base import BaseCollector, EventRecord, SourceCitation


# ── arXiv API ──────────────────────────────────────────────────────────────────

ARXIV_API = "http://export.arxiv.org/api/query"


def _fetch_arxiv(keywords: list[str], max_results: int = 5) -> list[dict]:
    """Search arXiv for recent papers matching keywords."""
    query = " OR ".join(f'all:"{kw}"' for kw in keywords[:5])
    params = {
        "search_query": f"({query})",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    try:
        resp = requests.get(ARXIV_API, params=params, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        results = []
        for entry in root.findall("atom:entry", ns):
            title = " ".join((entry.find("atom:title", ns).text or "").split())
            summary = " ".join((entry.find("atom:summary", ns).text or "").split())[:300]
            link = entry.find("atom:id", ns).text
            published = entry.find("atom:published", ns).text
            results.append({
                "title": title,
                "url": link,
                "snippet": summary,
                "published": published[:10] if published else "",
                "source": "arXiv",
            })
        return results
    except Exception as e:
        print(f"    [arXiv] failed: {e}")
        return []


# ── DuckDuckGo search ───────────────────────────────────────────────────────────

def _fetch_ddg(target_name: str, keyword: str, max_results: int = 3) -> list[dict]:
    """Search DuckDuckGo for recent news about a topic.

    Uses the named-parameter search query to get relevant results.
    Tries news search first, falls back to text search.
    """
    query = f'"{target_name}" {keyword}'
    results = []

    # Try news search
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results, timelimit="w"):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("body", "")[:300],
                    "published": r.get("date", ""),
                    "source": r.get("source", "News"),
                })
        if results:
            return results
    except ImportError:
        pass
    except Exception as e:
        msg = str(e).lower()
        if "ratelimit" in msg or "403" in msg:
            print(f"    [DDG] rate-limited in this environment, skipping DDG")
            return []
        # other errors → try text search

    # Fallback: text search
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")[:300],
                    "published": "",
                    "source": "Web",
                })
    except ImportError:
        return []
    except Exception:
        return []

    return results


# ── GitHub Search API ───────────────────────────────────────────────────────────

def _fetch_github_topics(
    topics: list[str], gh_token: Optional[str], max_results: int = 5
) -> list[dict]:
    """Search GitHub for repos matching topics."""
    if not gh_token:
        return []
    query = " OR ".join(f"topic:{t}" for t in topics[:3])
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
    }
    params = {"q": query, "sort": "updated", "order": "desc", "per_page": max_results}
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            headers=headers, params=params, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("items", []):
            results.append({
                "title": f"{item['full_name']}: {item.get('description', '')[:100]}",
                "url": item["html_url"],
                "snippet": item.get("description", "")[:300],
                "published": item.get("updated_at", "")[:10],
                "source": "GitHub",
                "stars": item.get("stargazers_count", 0),
                "language": item.get("language", ""),
            })
        return results
    except Exception as e:
        print(f"    [GitHub] search failed: {e}")
        return []


# ── Collector class ─────────────────────────────────────────────────────────────

class RealSearchCollector(BaseCollector):
    """Collect real event content from DuckDuckGo, arXiv, and GitHub.

    Strategy per source type:
      - rss (arXiv): search papers by keyword
      - api (GitHub topics): search repos
      - web_search: search DuckDuckGo news for each keyword
      - Falls back to keyword skeleton if no real results
    """

    def __init__(self, config: dict, source_key: str):
        super().__init__(config)
        self.source_key = source_key
        src_cfg = self.config.get("sources", {}).get(source_key, {})
        self.source_name = src_cfg.get("name", source_key)
        self.tier = src_cfg.get("tier", 2)
        self.ecosystem = src_cfg.get("ecosystem", "unknown")
        self.src_type = src_cfg.get("type", "web_search")
        self.keywords = src_cfg.get("keywords", [])
        self.topics = src_cfg.get("topics", [])
        self.enabled = src_cfg.get("enabled", True)
        self.max_items = src_cfg.get("max_items", 5)
        self.gh_token = None  # set from main.py

    def collect(self) -> list[EventRecord]:
        if not self.enabled:
            return []

        results = []

        if self.src_type == "rss":
            results = _fetch_arxiv(self.keywords, self.max_items)

        elif self.src_type == "api" and self.topics:
            results = _fetch_github_topics(self.topics, self.gh_token, self.max_items)

        elif self.keywords:
            # Web search: try DuckDuckGo for the first few keywords
            ddg_had_results = False
            for kw in self.keywords[:3]:
                news = _fetch_ddg(self.source_name, kw, max_results=2)
                if news:
                    ddg_had_results = True
                    for r in news:
                        r["keyword"] = kw
                    results.extend(news)
                    time.sleep(0.5)  # polite rate limiting

            if not ddg_had_results:
                print(f"    [{self.source_key}] DDG unavailable — using keyword skeleton")
                return self._build_fallback_records()

        if results:
            return self._build_records(results)
        else:
            return self._build_fallback_records()

    def _build_records(self, results: list[dict]) -> list[EventRecord]:
        records = []
        for r in results[:self.max_items]:
            eid = hashlib.md5(r["url"].encode()).hexdigest()[:12]
            record = EventRecord(
                event_id=f"{self.source_key}:{eid}",
                title=r.get("title", "")[:200],
                description=r.get("snippet", ""),
                url=r.get("url", ""),
                organization=self.source_name,
                published_at=r.get("published", ""),
                raw_data={
                    **r,
                    "source_key": self.source_key,
                    "source_name": self.source_name,
                    "tier": self.tier,
                    "ecosystem": self.ecosystem,
                    "collector": "RealSearchCollector",
                    "collected_at": datetime.utcnow().isoformat(),
                },
                citations=[
                    SourceCitation(
                        source_key=self.source_key,
                        source_name=self.source_name,
                        tier=self.tier,
                        ecosystem=self.ecosystem,
                        url=r.get("url", ""),
                    )
                ],
            )
            records.append(record)
        return records

    def _build_fallback_records(self) -> list[EventRecord]:
        records = []
        for kw in self.keywords[:self.max_items]:
            eid = hashlib.md5(
                f"{self.source_key}:{kw}:{datetime.utcnow().strftime('%Y-W%V')}".encode()
            ).hexdigest()[:12]
            record = EventRecord(
                event_id=f"{self.source_key}:{eid}",
                title=f"[{self.source_name}] {kw}",
                description=f"搜索关键词 '{kw}' — 本周暂无实时结果（DDG不可用）",
                organization=self.source_name,
                published_at=datetime.utcnow().strftime("%Y-%m-%d"),
                raw_data={
                    "source_key": self.source_key,
                    "source_name": self.source_name,
                    "tier": self.tier,
                    "ecosystem": self.ecosystem,
                    "keyword": kw,
                    "fallback": True,
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
        return records

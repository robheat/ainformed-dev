"""
fetch_feeds.py — Pull raw stories from RSS feeds and targeted web scraping.
Outputs: pipeline/cache/raw_stories.json
"""
import json
import os
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from html import unescape

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = CACHE_DIR / "raw_stories.json"

# RSS feeds to poll
RSS_FEEDS = [
    {
        "name": "Hacker News AI",
        "url": "https://hnrss.org/newest?q=AI+LLM+machine+learning&count=30",
        "category_hint": "general",
    },
    {
        "name": "ArXiv cs.AI",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "category_hint": "research",
    },
    {
        "name": "ArXiv cs.LG",
        "url": "https://rss.arxiv.org/rss/cs.LG",
        "category_hint": "research",
    },
    {
        "name": "ArXiv cs.CL",
        "url": "https://rss.arxiv.org/rss/cs.CL",
        "category_hint": "research",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category_hint": "industry",
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category_hint": "industry",
    },
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/feed/",
        "category_hint": "research",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "category_hint": "industry",
    },
    {
        "name": "Wired AI",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "category_hint": "general",
    },
]

MAX_STORIES_PER_FEED = 15
REQUEST_TIMEOUT = 15


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_url(url: str) -> bytes | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AInformedBot/1.0 (+https://ainformed.dev/llms.txt)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read()
    except Exception as exc:
        print(f"  [WARN] Failed to fetch {url}: {exc}")
        return None


def _ns(tag: str, namespace: str = "") -> str:
    return f"{{{namespace}}}{tag}" if namespace else tag


def parse_rss(raw: bytes, source_name: str, category_hint: str) -> list[dict]:
    stories = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"  [WARN] XML parse error for {source_name}: {e}")
        return stories

    # Handle both RSS 2.0 and Atom
    ns_atom = "http://www.w3.org/2005/Atom"
    items = root.findall(".//item") or root.findall(f".//{_ns('entry', ns_atom)}")

    for item in items[:MAX_STORIES_PER_FEED]:
        title_el = item.find("title") or item.find(_ns("title", ns_atom))
        link_el = (
            item.find("link")
            or item.find(_ns("link", ns_atom))
        )
        desc_el = (
            item.find("description")
            or item.find("summary")
            or item.find(_ns("summary", ns_atom))
            or item.find(_ns("content", ns_atom))
        )
        pub_el = (
            item.find("pubDate")
            or item.find("published")
            or item.find(_ns("published", ns_atom))
        )

        title = _strip_html(title_el.text if title_el is not None else "")
        # Atom <link> stores URL in href attribute
        link = ""
        if link_el is not None:
            link = link_el.get("href") or (link_el.text or "")
        link = link.strip()
        description = _strip_html(desc_el.text if desc_el is not None else "")[:600]
        pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

        if not title or not link:
            continue

        stories.append(
            {
                "title": title,
                "url": link,
                "description": description,
                "source_name": source_name,
                "category_hint": category_hint,
                "pub_date": pub_date,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return stories


def fetch_all() -> list[dict]:
    all_stories: list[dict] = []
    seen_urls: set[str] = set()

    for feed in RSS_FEEDS:
        print(f"Fetching: {feed['name']} ...")
        raw = _fetch_url(feed["url"])
        if raw is None:
            continue

        stories = parse_rss(raw, feed["name"], feed["category_hint"])
        new = [s for s in stories if s["url"] not in seen_urls]
        seen_urls.update(s["url"] for s in new)
        all_stories.extend(new)
        print(f"  → {len(new)} new stories")

    print(f"\nTotal raw stories: {len(all_stories)}")
    return all_stories


if __name__ == "__main__":
    stories = fetch_all()
    OUTPUT_FILE.write_text(json.dumps(stories, indent=2, ensure_ascii=False))
    print(f"Saved to {OUTPUT_FILE}")

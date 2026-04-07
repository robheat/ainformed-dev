"""
generate_content.py — Use Venice AI to write full article JSON from curated stories.
Input:  pipeline/cache/curated_stories.json
Output: content/articles/<slug>.json (one per story, committed to repo)
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from venice_client import json_chat

CACHE_DIR = Path(__file__).parent / "cache"
INPUT_FILE = CACHE_DIR / "curated_stories.json"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "articles"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["models", "research", "tools", "policy", "industry", "open-source", "general"]

ARTICLE_SYSTEM_PROMPT = """\
You are a senior AI journalist writing for AInformed.dev, a daily AI news digest.
Given a raw story (title, description, source), write a complete article in JSON format.

Requirements:
- title: Crisp, informative headline (max 120 chars). Not clickbait.
- summary: Two concise sentences explaining the key takeaway. (~50 words)
- body: Three clear paragraphs (~250 words total):
  Paragraph 1: What happened — the core news.
  Paragraph 2: Why it matters — context, implications, comparisons.
  Paragraph 3: What's next — reactions, future outlook, open questions.
  Separate paragraphs with \\n\\n.
- category: One of: models, research, tools, policy, industry, open-source, general
- tags: 3-6 lowercase single-word or hyphenated tags
- twitterThread: An array of 4-6 tweet strings (each ≤280 chars) that form a thread
  summarizing the story. First tweet should hook the reader. Last tweet should link
  back: "Read more at https://ainformed.dev"

Write factually. Do not hallucinate details not present in the input.
If the description is thin, stay close to what's stated.

Respond with ONLY valid JSON matching this schema:
{
  "title": string,
  "summary": string,
  "body": string,
  "category": string,
  "tags": string[],
  "twitterThread": string[]
}
"""


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def generate_article(story: dict) -> dict | None:
    """Generate a full article JSON from a curated story using Venice AI."""
    messages = [
        {"role": "system", "content": ARTICLE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "title": story["title"],
                    "description": story.get("description", ""),
                    "source_name": story["source_name"],
                    "source_url": story["url"],
                    "category_hint": story.get("category_hint", "general"),
                },
                ensure_ascii=False,
            ),
        },
    ]

    try:
        result = json_chat(messages, temperature=0.4, max_tokens=2048)
    except Exception as exc:
        print(f"  [ERROR] Venice AI call failed: {exc}")
        return None

    # Validate and normalize
    if not isinstance(result, dict) or "title" not in result:
        print(f"  [ERROR] Invalid response shape")
        return None

    category = result.get("category", story.get("category_hint", "general"))
    if category not in CATEGORIES:
        category = "general"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = f"{today}-{slugify(result['title'])}"

    article = {
        "slug": slug,
        "title": result["title"],
        "summary": result.get("summary", ""),
        "body": result.get("body", ""),
        "sourceUrl": story["url"],
        "sourceName": story["source_name"],
        "category": category,
        "tags": result.get("tags", [])[:6],
        "publishedAt": datetime.now(timezone.utc).isoformat(),
        "imageUrl": None,
        "twitterThread": result.get("twitterThread", []),
    }

    return article


def generate_all():
    if not INPUT_FILE.exists():
        print("ERROR: curated_stories.json not found. Run curate.py first.")
        sys.exit(1)

    curated: list[dict] = json.loads(INPUT_FILE.read_text())
    print(f"Generating articles for {len(curated)} stories...")

    written = 0
    for i, story in enumerate(curated):
        print(f"\n[{i+1}/{len(curated)}] {story['title'][:80]}")
        article = generate_article(story)
        if article is None:
            print("  → Skipped (generation failed)")
            continue

        out_path = CONTENT_DIR / f"{article['slug']}.json"
        out_path.write_text(json.dumps(article, indent=2, ensure_ascii=False))
        print(f"  → Saved: {out_path.name}")
        written += 1

    print(f"\nDone. Generated {written}/{len(curated)} articles.")
    return written


if __name__ == "__main__":
    generate_all()

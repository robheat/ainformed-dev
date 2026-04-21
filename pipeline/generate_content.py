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

from venice_client import chat, json_chat, generate_image

CACHE_DIR = Path(__file__).parent / "cache"
INPUT_FILE = CACHE_DIR / "curated_stories.json"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "articles"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR = Path(__file__).parent.parent / "public" / "images" / "articles"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

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
- twitterThread: An array of 4-6 tweet strings (each ≤280 chars) forming a viral thread.
  Style: punchy, opinionated, conversational — like a top AI influencer on X.
  Use short sentences. Sentence fragments OK. Strategic line breaks for readability.
  Tweet 1: A bold hook — lead with the most surprising or impactful angle. Use an emoji.
  Tweet 2-4: The key details, each tweet building on the last. Include concrete numbers,
    names, comparisons. Use phrases like "Here's why this matters:", "The wild part:",
    "Let that sink in.", "This changes everything for..."
  Tweet 5: A hot take or forward-looking angle — what this means for the industry.
  Final tweet: "Full breakdown → https://ainformed.dev" (not the article slug, just the site)
  Do NOT use hashtags. Do NOT be generic. Every tweet should make someone want to read the next.

- standaloneTweet: A single catchy tweet (≤280 chars) that could go viral on its own.
  Lead with the most interesting angle, not just the headline. Include a take or hook.
  End with the article URL: https://ainformed.dev/articles/{slug}
  where {slug} is the URL-safe version of the title.
  No hashtags.

Write factually. Do not hallucinate details not present in the input.
If the description is thin, stay close to what's stated.

Respond with ONLY valid JSON matching this schema:
{
  "title": string,
  "summary": string,
  "body": string,
  "category": string,
  "tags": string[],
  "twitterThread": string[],
  "standaloneTweet": string
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
    correct_url = f"https://ainformed.dev/articles/{slug}"

    def _fix_urls(text: str) -> str:
        """Replace any ainformed.dev article URL (including LLM-guessed slugs with dots)
        with the authoritative URL for this article."""
        text = re.sub(r"https?://ainformed\.dev/articles/[\w.-]+", correct_url, text)
        text = re.sub(r"https?://ainformed\.dev(?!/articles/)(?:\s|$)", correct_url + " ", text).rstrip()
        return text

    fixed_thread = [_fix_urls(t) for t in result.get("twitterThread", [])]
    fixed_standalone = _fix_urls(result.get("standaloneTweet", ""))

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
        "twitterThread": fixed_thread,
        "standaloneTweet": fixed_standalone,
    }

    # Generate article image
    image_url = generate_article_image(article)
    if image_url:
        article["imageUrl"] = image_url

    return article


IMAGE_PROMPT_SYSTEM = """\
You are a visual prompt engineer. Given an article title and summary about AI/tech news,
write a concise DALL-E / Stable Diffusion style image prompt (max 200 chars) for a
compelling hero image. Since every article is about AI, always incorporate AI-themed
visual concepts such as neural networks, glowing circuits, data streams, digital brains,
or machine learning nodes. The image should be abstract, futuristic, and tech-themed.
Do NOT include any text or letters in the image. No people's faces. No logos.
Respond with ONLY the image prompt text, nothing else."""


def generate_article_image(article: dict) -> str | None:
    """Generate a hero image for the article using Venice AI image generation."""
    try:
        # Use LLM to craft a good image prompt from the article
        image_prompt = chat(
            [
                {"role": "system", "content": IMAGE_PROMPT_SYSTEM},
                {"role": "user", "content": f"Title: {article['title']}\nSummary: {article['summary']}"},
            ],
            temperature=0.7,
            max_tokens=100,
            disable_thinking=True,
        )
        # Strip any residual thinking blocks and quotes
        image_prompt = re.sub(r"<think>.*?</think>", "", image_prompt, flags=re.DOTALL).strip().strip('"')
        print(f"  [IMG] Prompt: {image_prompt[:80]}...")

        # Generate image via Venice AI
        image_bytes = generate_image(image_prompt)

        # Save to public/images/articles/ — detect format from magic bytes
        ext = "png"
        if image_bytes[:4] == b"RIFF":
            ext = "webp"
        elif image_bytes[:3] == b"\xff\xd8\xff":
            ext = "jpg"
        image_filename = f"{article['slug']}.{ext}"
        image_path = IMAGES_DIR / image_filename
        image_path.write_bytes(image_bytes)
        print(f"  [IMG] Saved: {image_filename} ({len(image_bytes)//1024}KB)")

        return f"/images/articles/{image_filename}"
    except Exception as exc:
        print(f"  [IMG ERROR] {exc}")
        return None


def generate_all():
    if not INPUT_FILE.exists():
        print("ERROR: curated_stories.json not found. Run curate.py first.")
        sys.exit(1)

    curated: list[dict] = json.loads(INPUT_FILE.read_text())
    print(f"Generating articles for {len(curated)} stories...")

    # Build set of source URLs that already have articles
    existing_urls: set[str] = set()
    for f in CONTENT_DIR.iterdir():
        if f.suffix == ".json":
            try:
                existing_urls.add(json.loads(f.read_text()).get("sourceUrl", ""))
            except Exception:
                pass

    written = 0
    skipped = 0
    for i, story in enumerate(curated):
        print(f"\n[{i+1}/{len(curated)}] {story['title'][:80]}")

        # Skip if we already have an article for this source URL
        if story["url"] in existing_urls:
            print("  → Skipped (article already exists for this URL)")
            skipped += 1
            continue

        article = generate_article(story)
        if article is None:
            print("  → Skipped (generation failed)")
            continue

        out_path = CONTENT_DIR / f"{article['slug']}.json"
        out_path.write_text(json.dumps(article, indent=2, ensure_ascii=False))
        print(f"  → Saved: {out_path.name}")
        existing_urls.add(story["url"])
        written += 1

    print(f"\nDone. Generated {written}/{len(curated)} articles ({skipped} skipped as duplicates).")
    return written


if __name__ == "__main__":
    generate_all()

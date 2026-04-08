"""
post_twitter.py — Post today's AI digest as a Twitter/X thread.
Uses Twitter API v2 (OAuth 1.0a User Context).

Requires env vars:
  TWITTER_API_KEY, TWITTER_API_SECRET,
  TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
"""
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

CONTENT_DIR = Path(__file__).parent.parent / "content" / "articles"

# Twitter API v2 endpoints
TWEET_URL = "https://api.twitter.com/2/tweets"

# Env vars
API_KEY = os.environ.get("TWITTER_API_KEY", "")
API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")

DRY_RUN = os.environ.get("TWITTER_DRY_RUN", "false").lower() == "true"


def _percent_encode(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def _oauth_signature(method: str, url: str, params: dict) -> str:
    """Generate OAuth 1.0a signature."""
    sorted_params = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}"
        for k, v in sorted(params.items())
    )
    base_string = f"{method}&{_percent_encode(url)}&{_percent_encode(sorted_params)}"
    signing_key = f"{_percent_encode(API_SECRET)}&{_percent_encode(ACCESS_SECRET)}"
    signature = hmac.new(
        signing_key.encode(), base_string.encode(), hashlib.sha1
    ).digest()
    import base64
    return base64.b64encode(signature).decode()


def _oauth_header(method: str, url: str, extra_params: dict | None = None) -> str:
    """Build the OAuth Authorization header."""
    oauth_params = {
        "oauth_consumer_key": API_KEY,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": ACCESS_TOKEN,
        "oauth_version": "1.0",
    }
    all_params = {**oauth_params, **(extra_params or {})}
    oauth_params["oauth_signature"] = _oauth_signature(method, url, all_params)

    header_parts = ", ".join(
        f'{_percent_encode(k)}="{_percent_encode(v)}"'
        for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"


def post_tweet(text: str, reply_to: str | None = None) -> str | None:
    """
    Post a single tweet. Returns tweet ID on success, None on failure.
    """
    payload: dict = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}

    body = json.dumps(payload).encode("utf-8")
    auth_header = _oauth_header("POST", TWEET_URL)

    req = urllib.request.Request(
        TWEET_URL,
        data=body,
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            tweet_id = data.get("data", {}).get("id")
            return tweet_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  [ERROR] Twitter API {e.code}: {error_body[:300]}")
        return None


def post_thread(tweets: list[str]) -> list[str]:
    """Post a thread (list of tweet texts). Returns list of tweet IDs."""
    if not tweets:
        return []

    ids: list[str] = []
    prev_id: str | None = None
    for i, text in enumerate(tweets):
        print(f"  Tweet {i+1}/{len(tweets)}: {text[:60]}...")
        if DRY_RUN:
            print("    [DRY RUN] Would post tweet")
            ids.append(f"dry-run-{i}")
            continue

        tweet_id = post_tweet(text, reply_to=prev_id)
        if tweet_id:
            ids.append(tweet_id)
            prev_id = tweet_id
            print(f"    → Posted: {tweet_id}")
        else:
            print(f"    → FAILED. Stopping thread.")
            break

        # Rate-limit pause — Twitter v2 has 200 tweets/15min for user context
        if i < len(tweets) - 1:
            time.sleep(2)

    return ids


def get_todays_articles() -> list[dict]:
    """Load today's article JSONs."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    articles = []
    if not CONTENT_DIR.exists():
        return articles
    for f in sorted(CONTENT_DIR.iterdir()):
        if f.suffix == ".json" and f.name.startswith(today):
            articles.append(json.loads(f.read_text()))
    return articles


def main():
    if not API_KEY:
        print("Twitter credentials not set. Skipping Twitter posting.")
        return

    articles = get_todays_articles()
    if not articles:
        print("No articles for today. Nothing to tweet.")
        return

    print(f"Found {len(articles)} articles for today.")

    # Post thread for top article (first one, which is usually highest scored)
    top = articles[0]
    thread_tweets = top.get("twitterThread", [])

    if not thread_tweets:
        # Fallback: generate a simple thread from the article
        thread_tweets = [
            f"🤖 {top['title']}\n\n{top['summary']}",
            f"Read more → https://ainformed.dev/articles/{top['slug']}",
        ]

    print(f"\nPosting thread for: {top['title'][:70]}")
    if DRY_RUN:
        print("[DRY RUN MODE]")

    ids = post_thread(thread_tweets)
    print(f"\nThread posted: {len(ids)} tweets")

    # Post a standalone tweet for each remaining article
    for art in articles[1:5]:  # top 5 articles max
        tweet = art.get("standaloneTweet", "").strip()
        # Fallback if no standalone tweet was generated
        if not tweet:
            tweet = f"📰 {art['title']}\n\nhttps://ainformed.dev/articles/{art['slug']}"
        if len(tweet) > 280:
            tweet = tweet[:277] + "…"

        print(f"\nPosting: {art['title'][:60]}...")
        if DRY_RUN:
            print("  [DRY RUN] Would post tweet")
        else:
            tweet_id = post_tweet(tweet)
            if tweet_id:
                print(f"  → Posted: {tweet_id}")
            time.sleep(3)


if __name__ == "__main__":
    main()

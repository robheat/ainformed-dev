"""
venice_client.py — Thin wrapper around the Venice AI API (OpenAI-compatible).
"""
import os
import json
import http.client
import urllib.parse
from typing import Optional

VENICE_API_KEY = os.environ["VENICE_AI_API_KEY"]
VENICE_HOST = "api.venice.ai"
VENICE_BASE_PATH = "/api/v1"
# Default model — override via VENICE_MODEL env var
DEFAULT_MODEL = os.environ.get("VENICE_MODEL", "llama-3.3-70b")


def chat(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """
    Call Venice AI chat completions and return the assistant reply as a string.
    Raises RuntimeError on non-200 responses.
    """
    payload = json.dumps(
        {
            "model": model or DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")

    conn = http.client.HTTPSConnection(VENICE_HOST)
    conn.request(
        "POST",
        f"{VENICE_BASE_PATH}/chat/completions",
        body=payload,
        headers={
            "Authorization": f"Bearer {VENICE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()

    if resp.status != 200:
        raise RuntimeError(
            f"Venice AI API error {resp.status}: {body[:400]}"
        )

    data = json.loads(body)
    return data["choices"][0]["message"]["content"].strip()


def json_chat(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> dict | list:
    """
    Like chat(), but expects a JSON response and parses it.
    Raises ValueError if the response is not valid JSON.
    """
    content = chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(content)

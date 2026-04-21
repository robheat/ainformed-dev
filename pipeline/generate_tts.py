"""
generate_tts.py — Generate TTS audio for scripted YouTube Shorts using Kokoro ONNX.

Input:  content/.youtube-queue.json (entries with status == "scripted")
Output: pipeline/cache/youtube/<slug>.wav + updates queue status to "tts_done"

First run downloads the Kokoro model (~300MB) automatically.
Requires: pip install -r requirements-youtube.txt
"""
import json
import os
import sys
from pathlib import Path

QUEUE_FILE = Path(__file__).parent.parent / "content" / ".youtube-queue.json"
CACHE_DIR = Path(__file__).parent / "cache" / "youtube"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Kokoro voice name - see https://huggingface.co/hexgrad/Kokoro-82M for full list
# af_heart = American female (warm), am_fenrir = American male, bf_emma = British female
DEFAULT_VOICE = os.environ.get("KOKORO_VOICE", "af_heart")


def load_queue() -> dict:
    return json.loads(QUEUE_FILE.read_text())


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_tts():
    """Lazy-load Kokoro ONNX model. Downloads ~300MB on first run, then cached."""
    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        print("ERROR: kokoro-onnx not installed. Run: pip install -r requirements-youtube.txt")
        sys.exit(1)

    model_file = "kokoro-v1.0.fp16.onnx"
    print(f"  [TTS] Loading Kokoro ONNX ({model_file})...")
    kokoro = Kokoro(model_file, "voices-v1.0.bin")
    return kokoro


def synthesize(kokoro, text: str, output_path: Path) -> None:
    """Synthesize text to a WAV file using Kokoro ONNX."""
    import soundfile as sf

    samples, sample_rate = kokoro.create(text, voice=DEFAULT_VOICE, speed=1.0, lang="en-us")
    sf.write(str(output_path), samples, sample_rate)


def main() -> None:
    if not QUEUE_FILE.exists():
        print("ERROR: .youtube-queue.json not found. Run generate_shorts_script.py first.")
        sys.exit(1)

    queue = load_queue()
    pending = [item for item in queue["queue"] if item["status"] == "scripted"]

    if not pending:
        print("No scripted entries awaiting TTS.")
        return

    print(f"Generating TTS for {len(pending)} script(s)...")
    kokoro = get_tts()

    done = 0
    for item in pending:
        slug = item["slug"]
        text = item.get("scriptText", "")
        if not text:
            print(f"  [SKIP] {slug[:60]} -- no scriptText")
            continue

        output_path = CACHE_DIR / f"{slug}.wav"

        if output_path.exists():
            print(f"  [CACHED] {output_path.name}")
            item["audioFile"] = str(output_path)
            item["status"] = "tts_done"
            done += 1
            continue

        print(f"  -> {slug[:60]}")
        try:
            synthesize(kokoro, text, output_path)
            item["audioFile"] = str(output_path)
            item["status"] = "tts_done"
            size_kb = output_path.stat().st_size // 1024
            print(f"  [OK] {output_path.name} ({size_kb}KB)")
            done += 1
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            item["status"] = "failed"
            item["error"] = str(exc)

    save_queue(queue)
    print(f"\nTTS done for {done} script(s)")


if __name__ == "__main__":
    main()

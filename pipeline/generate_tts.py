"""
generate_tts.py — Generate TTS audio for scripted YouTube Shorts using Coqui XTTS v2.

Input:  content/.youtube-queue.json (entries with status == "scripted")
Output: pipeline/cache/youtube/<slug>.wav + updates queue status to "tts_done"

First run will download the XTTS v2 model (~2GB) and cache it automatically.
Requires: pip install -r requirements-youtube.txt
"""
import json
import os
import sys
from pathlib import Path

QUEUE_FILE = Path(__file__).parent.parent / "content" / ".youtube-queue.json"
CACHE_DIR = Path(__file__).parent / "cache" / "youtube"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Optional: path to a reference speaker WAV for voice cloning
# Set XTTS_SPEAKER_WAV=/path/to/voice.wav in env to use a custom voice
SPEAKER_WAV = os.environ.get("XTTS_SPEAKER_WAV", "")
SPEAKER_LANG = os.environ.get("XTTS_LANG", "en")
# Default built-in XTTS v2 speaker (good quality, no reference WAV needed)
DEFAULT_SPEAKER = os.environ.get("XTTS_SPEAKER", "Claribel Dervla")


def load_queue() -> dict:
    return json.loads(QUEUE_FILE.read_text())


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_tts():
    """Lazy-load Coqui XTTS v2 model. Downloads ~2GB on first run, then cached."""
    try:
        from TTS.api import TTS
        import torch
    except ImportError:
        print("ERROR: TTS not installed. Run: pip install -r requirements-youtube.txt")
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  [TTS] Loading XTTS v2 on {device} (first run downloads ~2GB)...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return tts


def synthesize(tts, text: str, output_path: Path) -> None:
    """Synthesize text to a WAV file using XTTS v2."""
    kwargs: dict = {
        "text": text,
        "language": SPEAKER_LANG,
        "file_path": str(output_path),
    }
    if SPEAKER_WAV and Path(SPEAKER_WAV).exists():
        # Voice cloning from reference audio
        kwargs["speaker_wav"] = SPEAKER_WAV
    else:
        # Use a named built-in speaker
        kwargs["speaker"] = DEFAULT_SPEAKER

    tts.tts_to_file(**kwargs)


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
    tts = get_tts()

    done = 0
    for item in pending:
        slug = item["slug"]
        text = item.get("scriptText", "")
        if not text:
            print(f"  [SKIP] {slug[:60]} — no scriptText")
            continue

        output_path = CACHE_DIR / f"{slug}.wav"

        if output_path.exists():
            print(f"  [CACHED] {output_path.name}")
            item["audioFile"] = str(output_path)
            item["status"] = "tts_done"
            done += 1
            continue

        print(f"  → {slug[:60]}")
        try:
            synthesize(tts, text, output_path)
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
    print(f"\n✓ TTS done for {done} script(s)")


if __name__ == "__main__":
    main()

"""
render_short.py — Render YouTube Shorts video (1080x1920) from TTS audio + article image.

Input:  content/.youtube-queue.json (entries with status == "tts_done")
Output: pipeline/cache/youtube/<slug>.mp4 + updates queue status to "rendered"

Resolution: 1080x1920 (9:16 vertical)
Composition: blurred article image background → dark overlay → branding header →
             article title → animated caption lines → CTA footer
"""
import json
import sys
import textwrap
from pathlib import Path

QUEUE_FILE = Path(__file__).parent.parent / "content" / ".youtube-queue.json"
CACHE_DIR = Path(__file__).parent / "cache" / "youtube"
PUBLIC_DIR = Path(__file__).parent.parent / "public"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# Brand colours (indigo / white)
BRAND_COLOR = (99, 102, 241)
WHITE = (255, 255, 255)
DARK_BG = (10, 10, 20)

# Windows system fonts (fallback to default if missing)
WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")
FONT_BOLD = str(WINDOWS_FONT_DIR / "arialbd.ttf")
FONT_REGULAR = str(WINDOWS_FONT_DIR / "arial.ttf")


def load_queue() -> dict:
    return json.loads(QUEUE_FILE.read_text())


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _get_font(path: str, size: int):
    """Load a TrueType font, falling back to PIL default."""
    from PIL import ImageFont
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def make_background(article_image_path: Path | None):
    """Build a 1080x1920 blurred background as a numpy array."""
    import numpy as np
    from PIL import Image, ImageFilter

    if article_image_path and article_image_path.exists():
        img = Image.open(article_image_path).convert("RGB")
        # Scale to fill 1080x1920, center-crop
        img_ratio = img.width / img.height
        target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
        if img_ratio > target_ratio:
            new_h = VIDEO_HEIGHT
            new_w = int(new_h * img_ratio)
        else:
            new_w = VIDEO_WIDTH
            new_h = int(new_w / img_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - VIDEO_WIDTH) // 2
        top = (new_h - VIDEO_HEIGHT) // 2
        img = img.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT))
        img = img.filter(ImageFilter.GaussianBlur(radius=28))
        # Dark semi-transparent overlay
        overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 10, 190))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    else:
        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), DARK_BG)

    return np.array(img)


def draw_frame(
    bg,
    title: str,
    caption_lines: list[str],
    caption_idx: int,
) -> "numpy.ndarray":
    """Compose one video frame with all text layers."""
    import numpy as np
    from PIL import Image, ImageDraw

    img = Image.fromarray(bg.copy())
    draw = ImageDraw.Draw(img)

    font_brand = _get_font(FONT_BOLD, 52)
    font_title = _get_font(FONT_BOLD, 62)
    font_caption = _get_font(FONT_REGULAR, 46)
    font_cta = _get_font(FONT_BOLD, 40)

    # ── Header: AInformed.dev branding ──────────────────────────────────────
    draw.text(
        (VIDEO_WIDTH // 2, 90),
        "AInformed.dev",
        font=font_brand,
        fill=BRAND_COLOR,
        anchor="mm",
    )

    # ── Article title (wrapped, max 3 lines) ────────────────────────────────
    wrapped_title = textwrap.wrap(title, width=24)[:3]
    title_y = 200
    for line in wrapped_title:
        draw.text(
            (VIDEO_WIDTH // 2, title_y),
            line,
            font=font_title,
            fill=WHITE,
            anchor="mm",
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )
        title_y += 80

    # ── Caption (current narration line, word-wrapped) ──────────────────────
    if caption_lines and caption_idx < len(caption_lines):
        line = caption_lines[caption_idx]
        wrapped = textwrap.wrap(line, width=28)
        cap_y = VIDEO_HEIGHT // 2 - (len(wrapped) * 60) // 2
        for wl in wrapped:
            draw.text(
                (VIDEO_WIDTH // 2, cap_y),
                wl,
                font=font_caption,
                fill=WHITE,
                anchor="mm",
                stroke_width=2,
                stroke_fill=(0, 0, 0),
            )
            cap_y += 64

    # ── Bottom CTA ──────────────────────────────────────────────────────────
    draw.text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT - 110),
        "More AI news → ainformed.dev",
        font=font_cta,
        fill=BRAND_COLOR,
        anchor="mm",
    )

    return np.array(img)


def render_video(item: dict) -> Path | None:
    """Render one Short video. Returns output path or None on failure."""
    try:
        from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
    except ImportError:
        print("ERROR: moviepy not installed. Run: pip install -r requirements-youtube.txt")
        sys.exit(1)

    slug = item["slug"]
    title = item["title"]
    audio_path = Path(item["audioFile"])
    output_path = CACHE_DIR / f"{slug}.mp4"

    if output_path.exists():
        print(f"  [CACHED] {output_path.name}")
        return output_path

    # Resolve article image from public/
    image_url = item.get("imageUrl", "")
    article_image_path = None
    if image_url and image_url.startswith("/"):
        article_image_path = PUBLIC_DIR / image_url.lstrip("/")

    # Build caption lines from script sections
    script = item.get("script", {})
    caption_lines = (
        [script.get("hook", "")]
        + script.get("narration_lines", [])
        + [script.get("cta", "")]
    )
    caption_lines = [l for l in caption_lines if l.strip()]

    # Get total audio duration to divide evenly across captions
    try:
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration
        audio_clip.close()
    except Exception as exc:
        print(f"  [ERROR] Cannot read audio duration: {exc}")
        return None

    bg = make_background(article_image_path)
    seg_duration = duration / len(caption_lines)

    try:
        clips = []
        for i in range(len(caption_lines)):
            frame = draw_frame(bg, title, caption_lines, i)
            clips.append(ImageClip(frame, duration=seg_duration))

        video = concatenate_videoclips(clips, method="compose")
        audio = AudioFileClip(str(audio_path))
        video = video.with_audio(audio)
        video.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        video.close()
        audio.close()
    except Exception as exc:
        print(f"  [ERROR] Render failed: {exc}")
        return None

    size_mb = output_path.stat().st_size // (1024 * 1024)
    print(f"  [OK] {output_path.name} — {duration:.1f}s, {size_mb}MB")
    return output_path


def main() -> None:
    if not QUEUE_FILE.exists():
        print("ERROR: .youtube-queue.json not found.")
        sys.exit(1)

    queue = load_queue()
    pending = [item for item in queue["queue"] if item["status"] == "tts_done"]

    if not pending:
        print("No TTS-ready entries to render.")
        return

    print(f"Rendering {len(pending)} Short(s)...")
    done = 0
    for item in pending:
        print(f"\n  → {item['slug'][:60]}")
        output = render_video(item)
        if output:
            item["videoFile"] = str(output)
            item["status"] = "rendered"
            done += 1
        else:
            item["status"] = "failed"

    save_queue(queue)
    print(f"\n✓ Rendered {done} Short(s)")


if __name__ == "__main__":
    main()

"""
render_short.py — Render YouTube Shorts video (1080x1920) from TTS audio + article image.

Input:  content/.youtube-queue.json (entries with status == "tts_done" or "rendered")
Output: pipeline/cache/youtube/<slug>.mp4 + updates queue status to "rendered"

Style: News ticker / TV chyron
  - Full-bleed article image fills frame (light blur only)
  - Strong gradient darkens bottom 45% for legibility
  - AInformed.dev logo bar top-left with indigo accent line
  - Article title bold in upper third
  - Category badge pill
  - Bottom chyron: dark bar with bright caption text, progress bar underneath
  - Subtle vignette around edges
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

# Palette
INDIGO       = (99, 102, 241)
INDIGO_DARK  = (55, 48, 163)
WHITE        = (255, 255, 255)
OFF_WHITE    = (230, 230, 240)
NEAR_BLACK   = (12, 10, 22)
CHYRON_BG    = (15, 12, 30, 230)   # near-black, semi-opaque
ACCENT_GOLD  = (251, 191, 36)

WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")
FONT_BLACK  = str(WINDOWS_FONT_DIR / "ariblk.ttf")   # Arial Black
FONT_BOLD   = str(WINDOWS_FONT_DIR / "arialbd.ttf")
FONT_ITALIC = str(WINDOWS_FONT_DIR / "ariali.ttf")
FONT_REG    = str(WINDOWS_FONT_DIR / "arial.ttf")


def load_queue() -> dict:
    return json.loads(QUEUE_FILE.read_text())


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _font(path: str, size: int):
    from PIL import ImageFont
    for p in [path, FONT_BOLD, FONT_REG]:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def make_background(article_image_path: Path | None):
    """Full-bleed image background with light blur + edge vignette."""
    import numpy as np
    from PIL import Image, ImageFilter, ImageDraw

    if article_image_path and article_image_path.exists():
        img = Image.open(article_image_path).convert("RGB")
        # Fill 1080x1920, center-crop
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
        top  = (new_h - VIDEO_HEIGHT) // 2
        img  = img.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT))
        # Light blur only — keep the image readable as atmosphere
        img  = img.filter(ImageFilter.GaussianBlur(radius=6))
    else:
        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), NEAR_BLACK)

    # Bottom gradient — darkens lower 55% for chyron readability
    grad = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(grad)
    grad_start = int(VIDEO_HEIGHT * 0.30)
    steps = VIDEO_HEIGHT - grad_start
    for i in range(steps):
        alpha = int(200 * (i / steps) ** 1.4)
        y = grad_start + i
        d.line([(0, y), (VIDEO_WIDTH, y)], fill=(NEAR_BLACK[0], NEAR_BLACK[1], NEAR_BLACK[2], alpha))

    # Top gradient — subtle darkening for logo area
    for i in range(220):
        alpha = int(160 * (1 - i / 220) ** 1.2)
        d.line([(0, i), (VIDEO_WIDTH, i)], fill=(0, 0, 0, alpha))

    result = Image.alpha_composite(img.convert("RGBA"), grad).convert("RGB")
    return np.array(result)


def draw_frame(
    bg,
    title: str,
    category: str,
    caption_lines: list[str],
    caption_idx: int,
    n_captions: int,
) -> "numpy.ndarray":
    """Compose one video frame — news ticker style."""
    import numpy as np
    from PIL import Image, ImageDraw

    img  = Image.fromarray(bg.copy()).convert("RGBA")
    draw = ImageDraw.Draw(img)

    f_logo    = _font(FONT_BOLD,  48)
    f_tag     = _font(FONT_BOLD,  34)
    f_title   = _font(FONT_BLACK, 72)
    f_caption = _font(FONT_BOLD,  56)
    f_cta     = _font(FONT_BOLD,  36)

    PAD = 52  # horizontal margin

    # ── TOP BAR: logo + accent line ─────────────────────────────────────────
    bar_h = 110
    bar = Image.new("RGBA", (VIDEO_WIDTH, bar_h), (0, 0, 0, 0))
    bd  = ImageDraw.Draw(bar)
    # Accent line on left
    bd.rectangle([(0, 0), (8, bar_h)], fill=INDIGO)
    # Logo text
    bd.text((PAD + 16, bar_h // 2), "AInformed", font=f_logo, fill=WHITE, anchor="lm")
    bd.text((PAD + 16 + f_logo.getlength("AInformed"), bar_h // 2), ".dev",
            font=f_logo, fill=INDIGO, anchor="lm")
    img.alpha_composite(bar, (0, 36))

    # ── CATEGORY BADGE ──────────────────────────────────────────────────────
    cat_text = category.upper()
    cat_w    = int(f_tag.getlength(cat_text)) + 40
    cat_h    = 52
    cat_y    = 170
    badge    = Image.new("RGBA", (cat_w, cat_h), (*INDIGO, 220))
    bd2      = ImageDraw.Draw(badge)
    bd2.text((cat_w // 2, cat_h // 2), cat_text, font=f_tag, fill=WHITE, anchor="mm")
    img.alpha_composite(badge, (PAD, cat_y))

    # ── TITLE (upper third) ─────────────────────────────────────────────────
    wrapped_title = textwrap.wrap(title, width=18)[:4]
    title_y = 260
    for line in wrapped_title:
        # Shadow
        draw.text((PAD + 3, title_y + 3), line, font=f_title,
                  fill=(0, 0, 0, 160), anchor="lm")
        draw.text((PAD, title_y), line, font=f_title, fill=WHITE, anchor="lm")
        title_y += 88

    # ── CHYRON BAR (bottom) ──────────────────────────────────────────────────
    chyron_h   = 260
    chyron_y   = VIDEO_HEIGHT - chyron_h - 20
    chyron     = Image.new("RGBA", (VIDEO_WIDTH, chyron_h), CHYRON_BG)
    cd         = ImageDraw.Draw(chyron)

    # Top accent line on chyron
    cd.rectangle([(0, 0), (VIDEO_WIDTH, 5)], fill=(*INDIGO, 255))

    # Caption text (current line)
    if caption_lines and caption_idx < len(caption_lines):
        line    = caption_lines[caption_idx]
        wrapped = textwrap.wrap(line, width=22)[:3]
        cap_y   = 30
        for wl in wrapped:
            cd.text((VIDEO_WIDTH // 2, cap_y), wl, font=f_caption,
                    fill=WHITE, anchor="mm",
                    stroke_width=0)
            cap_y += 68

    # CTA line
    cd.text((VIDEO_WIDTH // 2, chyron_h - 44),
            "More at ainformed.dev",
            font=f_cta, fill=(*INDIGO, 220), anchor="mm")

    img.alpha_composite(chyron, (0, chyron_y))

    # ── PROGRESS BAR (below chyron) ─────────────────────────────────────────
    prog_y = VIDEO_HEIGHT - 18
    prog_w = int(VIDEO_WIDTH * (caption_idx + 1) / max(n_captions, 1))
    draw.rectangle([(0, prog_y), (VIDEO_WIDTH, VIDEO_HEIGHT)], fill=(30, 30, 50))
    draw.rectangle([(0, prog_y), (prog_w, VIDEO_HEIGHT)], fill=(*INDIGO, 255))

    return np.array(img.convert("RGB"))


def render_video(item: dict, force: bool = False) -> Path | None:
    """Render one Short video. Returns output path or None on failure."""
    try:
        from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
    except ImportError:
        print("ERROR: moviepy not installed. Run: pip install -r requirements-youtube.txt")
        sys.exit(1)

    slug     = item["slug"]
    title    = item["title"]
    category = item.get("category", "general")
    audio_path  = Path(item["audioFile"])
    output_path = CACHE_DIR / f"{slug}.mp4"

    if output_path.exists() and not force:
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

    try:
        audio_clip = AudioFileClip(str(audio_path))
        duration   = audio_clip.duration
        audio_clip.close()
    except Exception as exc:
        print(f"  [ERROR] Cannot read audio duration: {exc}")
        return None

    bg           = make_background(article_image_path)
    n            = len(caption_lines)
    seg_duration = duration / n

    try:
        clips = []
        for i in range(n):
            frame = draw_frame(bg, title, category, caption_lines, i, n)
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
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Re-render even if MP4 already exists")
    args = parser.parse_args()

    if not QUEUE_FILE.exists():
        print("ERROR: .youtube-queue.json not found.")
        sys.exit(1)

    queue   = load_queue()
    # Accept tts_done OR rendered (--force re-renders existing)
    pending = [
        item for item in queue["queue"]
        if item["status"] in ("tts_done", "rendered")
    ] if args.force else [
        item for item in queue["queue"]
        if item["status"] == "tts_done"
    ]

    if not pending:
        print("No TTS-ready entries to render.")
        return

    print(f"Rendering {len(pending)} Short(s){'  [FORCE]' if args.force else ''}...")
    done = 0
    for item in pending:
        print(f"\n  -> {item['slug'][:60]}")
        output = render_video(item, force=args.force)
        if output:
            item["videoFile"] = str(output)
            item["status"]    = "rendered"
            done += 1
        else:
            item["status"] = "failed"

    save_queue(queue)
    print(f"\nRendered {done} Short(s)")


if __name__ == "__main__":
    main()

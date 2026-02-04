"""Thumbnail generation - Mr. Beast style thumbnails."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

from .analyzer import AnalysisResult
from .metadata import VideoMetadata


@dataclass
class ThumbnailResult:
    """Generated thumbnail result."""

    path: Path
    source_frame: Path
    style: str


def get_best_frame(
    frames: list[Path],
    suggested_index: int = 0,
) -> Path:
    """Select the best frame for thumbnail.

    For now, uses the AI-suggested index. Future: analyze frames for
    faces, expressions, action, etc.
    """
    if not frames:
        raise ValueError("No frames provided")

    index = min(suggested_index, len(frames) - 1)
    return frames[index]


def create_mrbeast_thumbnail(
    frame_path: Path,
    title: str,
    output_path: Path,
    text_color: str = "#FFFF00",  # Yellow
    stroke_color: str = "#000000",  # Black
    font_size: int = 80,
) -> Path:
    """Create a Mr. Beast-style thumbnail.

    Features:
    - Bold text overlay
    - High saturation
    - Thick black outline on text
    - Eye-catching colors
    """
    # Load frame
    img = Image.open(frame_path)

    # Resize to YouTube thumbnail size (1280x720)
    img = img.resize((1280, 720), Image.Resampling.LANCZOS)

    # Boost saturation and contrast for that "pop"
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.3)  # 30% more saturated

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)  # 20% more contrast

    # Add slight vignette effect
    img = add_vignette(img)

    # Draw text
    draw = ImageDraw.Draw(img)

    # Try to load a bold font, fall back to default
    try:
        # Common bold fonts on macOS
        font_paths = [
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
        ]
        font = None
        for fp in font_paths:
            if Path(fp).exists():
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Prepare text - use first few words for thumbnail
    words = title.upper().split()[:4]
    text = " ".join(words)

    # Calculate text position (center-bottom with some padding)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (1280 - text_width) // 2
    y = 720 - text_height - 80  # 80px from bottom

    # Draw text with thick outline (stroke)
    stroke_width = 4
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)

    # Draw main text
    draw.text((x, y), text, font=font, fill=text_color)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)

    return output_path


def add_vignette(img: Image.Image, intensity: float = 0.3) -> Image.Image:
    """Add a subtle vignette effect to the image."""
    width, height = img.size

    # Create radial gradient mask
    from math import sqrt

    mask = Image.new("L", (width, height), 255)
    center_x, center_y = width // 2, height // 2
    max_dist = sqrt(center_x**2 + center_y**2)

    for y in range(height):
        for x in range(width):
            dist = sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            # Normalize and apply curve
            norm_dist = dist / max_dist
            value = int(255 * (1 - intensity * norm_dist**2))
            mask.putpixel((x, y), value)

    # Apply mask
    mask = mask.filter(ImageFilter.GaussianBlur(radius=50))

    # Blend with darkened version
    dark = ImageEnhance.Brightness(img).enhance(0.5)
    img = Image.composite(img, dark, mask)

    return img


def create_minimal_thumbnail(
    frame_path: Path,
    output_path: Path,
) -> Path:
    """Create a minimal thumbnail - just the frame with color enhancement."""
    img = Image.open(frame_path)
    img = img.resize((1280, 720), Image.Resampling.LANCZOS)

    # Slight enhancement
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)

    return output_path


def create_ai_thumbnail_gemini(
    frame_path: Path,
    title: str,
    description: str,
    output_path: Path,
) -> Path:
    """Create an AI-generated Mr. Beast-style thumbnail using Gemini.

    Uses Gemini to generate a prompt, then creates thumbnail with
    image generation or enhanced frame processing.
    """
    from .config import get_settings
    settings = get_settings()

    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY not set in .env")

    genai.configure(api_key=settings.google_api_key)

    # Load the frame to use as reference
    img = Image.open(frame_path)
    img = img.resize((1280, 720), Image.Resampling.LANCZOS)

    # Use Gemini to analyze frame and suggest thumbnail enhancements
    model = genai.GenerativeModel(settings.thumbnail_ai_model or "gemini-2.0-flash-exp")

    prompt = f"""Analyze this video frame for a YouTube thumbnail. The video is titled: "{title}"

Suggest:
1. Best text to overlay (2-4 impactful words, Mr. Beast style - CAPS, exciting)
2. Text color that contrasts well with the image (hex code)
3. Where to place text (top, center, bottom)
4. Any visual enhancements needed

Respond in JSON format:
{{"overlay_text": "...", "text_color": "#FFFF00", "position": "bottom", "enhance_saturation": 1.3, "enhance_contrast": 1.2}}"""

    try:
        # Upload frame for analysis
        response = model.generate_content([prompt, img])
        import json
        suggestions = json.loads(response.text)

        # Apply AI suggestions
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(suggestions.get("enhance_saturation", 1.3))

        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(suggestions.get("enhance_contrast", 1.2))

        # Add vignette
        img = add_vignette(img)

        # Draw text with AI suggestions
        draw = ImageDraw.Draw(img)

        try:
            font_paths = [
                "/System/Library/Fonts/Supplemental/Impact.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
            font = None
            for fp in font_paths:
                if Path(fp).exists():
                    font = ImageFont.truetype(fp, 90)
                    break
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        text = suggestions.get("overlay_text", title.upper()[:20])
        text_color = suggestions.get("text_color", "#FFFF00")
        position = suggestions.get("position", "bottom")

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (1280 - text_width) // 2
        if position == "top":
            y = 50
        elif position == "center":
            y = (720 - text_height) // 2
        else:  # bottom
            y = 720 - text_height - 80

        # Draw stroke
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill="#000000")

        draw.text((x, y), text, font=font, fill=text_color)

    except Exception as e:
        print(f"AI enhancement failed, falling back to standard: {e}")
        # Fallback to standard mrbeast style
        return create_mrbeast_thumbnail(frame_path, title, output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)

    return output_path


def generate_thumbnail(
    analysis: AnalysisResult,
    metadata: VideoMetadata,
    output_path: Path,
    style: Optional[str] = None,
    custom_frame: Optional[Path] = None,
) -> ThumbnailResult:
    """Generate a thumbnail for the video.

    Args:
        analysis: Video analysis result with frames
        metadata: Generated metadata with suggested frame index
        output_path: Where to save the thumbnail
        style: Thumbnail style (mrbeast, minimal, ai). Uses config if None.
        custom_frame: Use this frame instead of auto-selected one

    Returns:
        ThumbnailResult with path and info
    """
    from .config import get_settings
    settings = get_settings()

    style = style or settings.thumbnail_style

    # Select frame
    if custom_frame:
        source_frame = custom_frame
    else:
        source_frame = get_best_frame(
            analysis.frames,
            metadata.suggested_thumbnail_index,
        )

    # Generate based on style
    if style == "ai":
        create_ai_thumbnail_gemini(
            source_frame,
            metadata.title,
            metadata.description,
            output_path,
        )
    elif style == "mrbeast":
        create_mrbeast_thumbnail(source_frame, metadata.title, output_path)
    elif style == "minimal":
        create_minimal_thumbnail(source_frame, output_path)
    else:
        # Default to mrbeast
        create_mrbeast_thumbnail(source_frame, metadata.title, output_path)

    return ThumbnailResult(
        path=output_path,
        source_frame=source_frame,
        style=style,
    )

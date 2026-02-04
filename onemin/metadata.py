"""AI-powered metadata generation for YouTube videos."""

from dataclasses import dataclass
from typing import Optional

from .analyzer import AnalysisResult
from .config import get_settings


@dataclass
class VideoMetadata:
    """Generated metadata for a YouTube video."""

    title: str
    description: str
    tags: list[str]
    category_id: str  # YouTube category ID
    suggested_thumbnail_index: int  # Which frame to use


METADATA_PROMPT = """You are a YouTube content optimization expert. Generate engaging metadata for a video based on its transcript.

VIDEO TRANSCRIPT:
{transcript}

VIDEO INFO:
- Duration: {duration:.1f} seconds ({minutes:.1f} minutes)
- Resolution: {width}x{height}
- Original filename: {filename}

Generate the following in JSON format:

1. **title**: A catchy, clickbait-style title (Mr. Beast style). Should be:
   - Under 60 characters
   - Include power words (INSANE, CRAZY, SHOCKING, etc.) where appropriate
   - Create curiosity/FOMO
   - Include relevant keywords for SEO

2. **description**: A YouTube description that:
   - First line is a hook (shows in search results)
   - Summarizes the video content
   - Includes relevant keywords naturally
   - Has a call to action (like, subscribe, comment)
   - About 150-300 words

3. **tags**: List of 10-15 relevant tags for SEO

4. **category_id**: YouTube category ID (use "28" for Science & Technology, "22" for People & Blogs, "24" for Entertainment, "26" for How-to & Style, "20" for Gaming)

5. **suggested_thumbnail_index**: Which frame (0-9) would make the best thumbnail based on transcript content (pick a moment with action, reaction, or key reveal)

Respond with ONLY valid JSON, no markdown code blocks:
{{"title": "...", "description": "...", "tags": [...], "category_id": "...", "suggested_thumbnail_index": 0}}
"""


def generate_metadata_anthropic(
    analysis: AnalysisResult,
    custom_instructions: Optional[str] = None,
) -> VideoMetadata:
    """Generate metadata using Anthropic Claude."""
    settings = get_settings()

    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic not installed. Run: pip install anthropic")

    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = METADATA_PROMPT.format(
        transcript=analysis.transcript[:8000],  # Limit transcript length
        duration=analysis.video_info.duration,
        minutes=analysis.video_info.duration / 60,
        width=analysis.video_info.width,
        height=analysis.video_info.height,
        filename=analysis.video_info.path.name,
    )

    if custom_instructions:
        prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"

    message = client.messages.create(
        model=settings.ai_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse JSON response
    import json
    response_text = message.content[0].text
    data = json.loads(response_text)

    return VideoMetadata(
        title=data["title"],
        description=data["description"],
        tags=data["tags"],
        category_id=data["category_id"],
        suggested_thumbnail_index=data.get("suggested_thumbnail_index", 0),
    )


def generate_metadata_openai(
    analysis: AnalysisResult,
    custom_instructions: Optional[str] = None,
) -> VideoMetadata:
    """Generate metadata using OpenAI GPT."""
    settings = get_settings()

    try:
        import openai
    except ImportError:
        raise ImportError("openai not installed. Run: pip install openai")

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in .env")

    client = openai.OpenAI(api_key=settings.openai_api_key)

    prompt = METADATA_PROMPT.format(
        transcript=analysis.transcript[:8000],
        duration=analysis.video_info.duration,
        minutes=analysis.video_info.duration / 60,
        width=analysis.video_info.width,
        height=analysis.video_info.height,
        filename=analysis.video_info.path.name,
    )

    if custom_instructions:
        prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    import json
    data = json.loads(response.choices[0].message.content)

    return VideoMetadata(
        title=data["title"],
        description=data["description"],
        tags=data["tags"],
        category_id=data["category_id"],
        suggested_thumbnail_index=data.get("suggested_thumbnail_index", 0),
    )


def generate_metadata_deepseek(
    analysis: AnalysisResult,
    custom_instructions: Optional[str] = None,
) -> VideoMetadata:
    """Generate metadata using DeepSeek."""
    settings = get_settings()

    try:
        import openai  # DeepSeek uses OpenAI-compatible API
    except ImportError:
        raise ImportError("openai not installed. Run: pip install openai")

    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY not set in .env")

    client = openai.OpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )

    prompt = METADATA_PROMPT.format(
        transcript=analysis.transcript[:8000],
        duration=analysis.video_info.duration,
        minutes=analysis.video_info.duration / 60,
        width=analysis.video_info.width,
        height=analysis.video_info.height,
        filename=analysis.video_info.path.name,
    )

    if custom_instructions:
        prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"

    response = client.chat.completions.create(
        model=settings.ai_model or "deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    import json
    data = json.loads(response.choices[0].message.content)

    return VideoMetadata(
        title=data["title"],
        description=data["description"],
        tags=data["tags"],
        category_id=data["category_id"],
        suggested_thumbnail_index=data.get("suggested_thumbnail_index", 0),
    )


def generate_metadata_gemini(
    analysis: AnalysisResult,
    custom_instructions: Optional[str] = None,
) -> VideoMetadata:
    """Generate metadata using Google Gemini."""
    settings = get_settings()

    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY not set in .env")

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(settings.ai_model or "gemini-1.5-flash")

    prompt = METADATA_PROMPT.format(
        transcript=analysis.transcript[:8000],
        duration=analysis.video_info.duration,
        minutes=analysis.video_info.duration / 60,
        width=analysis.video_info.width,
        height=analysis.video_info.height,
        filename=analysis.video_info.path.name,
    )

    if custom_instructions:
        prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    import json
    data = json.loads(response.text)

    return VideoMetadata(
        title=data["title"],
        description=data["description"],
        tags=data["tags"],
        category_id=data["category_id"],
        suggested_thumbnail_index=data.get("suggested_thumbnail_index", 0),
    )


def generate_metadata(
    analysis: AnalysisResult,
    custom_instructions: Optional[str] = None,
) -> VideoMetadata:
    """Generate metadata using configured AI provider."""
    settings = get_settings()

    if settings.ai_provider == "deepseek":
        return generate_metadata_deepseek(analysis, custom_instructions)
    elif settings.ai_provider == "anthropic":
        return generate_metadata_anthropic(analysis, custom_instructions)
    elif settings.ai_provider == "openai":
        return generate_metadata_openai(analysis, custom_instructions)
    elif settings.ai_provider == "gemini":
        return generate_metadata_gemini(analysis, custom_instructions)
    else:
        raise ValueError(f"Unknown AI provider: {settings.ai_provider}")

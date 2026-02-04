"""Video analysis module - extract frames and transcribe audio."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import get_settings


@dataclass
class VideoInfo:
    """Information about a video file."""

    path: Path
    duration: float  # seconds
    width: int
    height: int
    fps: float
    codec: str
    size_mb: float


@dataclass
class AnalysisResult:
    """Result of video analysis."""

    video_info: VideoInfo
    frames: list[Path]  # Paths to extracted frame images
    transcript: str  # Full transcript
    transcript_segments: list[dict]  # Timestamped segments


def get_video_info(video_path: Path) -> VideoInfo:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    import json
    data = json.loads(result.stdout)

    # Find video stream
    video_stream = next(
        (s for s in data["streams"] if s["codec_type"] == "video"),
        None
    )

    if not video_stream:
        raise ValueError(f"No video stream found in {video_path}")

    format_info = data["format"]

    # Parse frame rate (can be "30/1" or "29.97")
    fps_str = video_stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_str)

    return VideoInfo(
        path=video_path,
        duration=float(format_info.get("duration", 0)),
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        fps=fps,
        codec=video_stream.get("codec_name", "unknown"),
        size_mb=float(format_info.get("size", 0)) / (1024 * 1024),
    )


def extract_frames(
    video_path: Path,
    output_dir: Path,
    num_frames: Optional[int] = None,
) -> list[Path]:
    """Extract key frames from video.

    Extracts frames at even intervals throughout the video.
    """
    settings = get_settings()
    num_frames = num_frames or settings.max_frames

    video_info = get_video_info(video_path)
    duration = video_info.duration

    if duration <= 0:
        raise ValueError(f"Invalid video duration: {duration}")

    output_dir.mkdir(parents=True, exist_ok=True)
    frames = []

    # Calculate timestamps for even distribution
    # Skip first and last 5% to avoid intros/outros
    start_time = duration * 0.05
    end_time = duration * 0.95
    interval = (end_time - start_time) / (num_frames - 1) if num_frames > 1 else 0

    for i in range(num_frames):
        timestamp = start_time + (i * interval)
        output_path = output_dir / f"frame_{i:03d}.jpg"

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",  # High quality JPEG
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        frames.append(output_path)

    return frames


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """Extract audio from video as WAV for transcription."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",
        "-ar", "16000",  # 16kHz for Whisper
        "-ac", "1",  # Mono
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def transcribe_audio(audio_path: Path) -> tuple[str, list[dict]]:
    """Transcribe audio using Whisper.

    Returns:
        Tuple of (full_transcript, segments)
        where segments is a list of {"start": float, "end": float, "text": str}
    """
    settings = get_settings()

    try:
        import whisper
    except ImportError:
        raise ImportError(
            "whisper not installed. Run: pip install openai-whisper"
        )

    model = whisper.load_model(settings.transcribe_model)
    result = model.transcribe(str(audio_path))

    full_text = result["text"].strip()
    segments = [
        {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
        }
        for seg in result["segments"]
    ]

    return full_text, segments


def analyze_video(video_path: Path, work_dir: Optional[Path] = None) -> AnalysisResult:
    """Full video analysis: extract info, frames, and transcript.

    Args:
        video_path: Path to the video file
        work_dir: Working directory for temporary files. If None, uses temp dir.

    Returns:
        AnalysisResult with video info, frames, and transcript
    """
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Create work directory
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="1minautoyt_"))
    else:
        work_dir.mkdir(parents=True, exist_ok=True)

    # Get video info
    video_info = get_video_info(video_path)

    # Extract frames
    frames_dir = work_dir / "frames"
    frames = extract_frames(video_path, frames_dir)

    # Extract and transcribe audio
    audio_path = work_dir / "audio.wav"
    extract_audio(video_path, audio_path)
    transcript, segments = transcribe_audio(audio_path)

    return AnalysisResult(
        video_info=video_info,
        frames=frames,
        transcript=transcript,
        transcript_segments=segments,
    )

"""Main processing pipeline - ties everything together."""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .analyzer import analyze_video, AnalysisResult
from .metadata import generate_metadata, VideoMetadata
from .thumbnail import generate_thumbnail, ThumbnailResult
from .approval import create_approval_request, send_telegram_approval
from .uploader import upload_video, UploadResult
from .config import get_settings

console = Console()


@dataclass
class ProcessOptions:
    """Options for video processing."""

    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    custom_thumbnail: Optional[Path] = None
    custom_tags: Optional[list[str]] = None
    privacy: Optional[str] = None
    skip_approval: bool = False
    dry_run: bool = False


@dataclass
class ProcessResult:
    """Result of video processing."""

    video_path: Path
    analysis: AnalysisResult
    metadata: VideoMetadata
    thumbnail: ThumbnailResult
    upload_result: Optional[UploadResult] = None
    request_id: Optional[str] = None
    status: str = "pending"  # pending, uploaded, error


def process_video(
    video_path: Path,
    options: Optional[ProcessOptions] = None,
) -> ProcessResult:
    """Process a video through the full pipeline.

    Steps:
    1. Analyze video (extract frames, transcribe)
    2. Generate metadata (AI-powered)
    3. Create thumbnail
    4. Send for approval (or upload immediately if skip_approval)

    Args:
        video_path: Path to the video file
        options: Processing options

    Returns:
        ProcessResult with all generated data
    """
    options = options or ProcessOptions()
    settings = get_settings()

    console.print(f"\n[bold cyan]Processing:[/bold cyan] {video_path.name}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Analyze video
        task = progress.add_task("Analyzing video...", total=None)

        work_dir = Path(tempfile.mkdtemp(prefix="1minautoyt_"))
        analysis = analyze_video(video_path, work_dir)

        progress.update(task, description="[green]✓ Video analyzed[/green]")

        # Step 2: Generate metadata
        task = progress.add_task("Generating metadata...", total=None)

        metadata = generate_metadata(analysis)

        # Apply custom overrides
        if options.custom_title:
            metadata.title = options.custom_title
        if options.custom_description:
            metadata.description = options.custom_description
        if options.custom_tags:
            metadata.tags = options.custom_tags

        progress.update(task, description="[green]✓ Metadata generated[/green]")

        # Step 3: Create thumbnail
        task = progress.add_task("Creating thumbnail...", total=None)

        thumbnail_path = work_dir / "thumbnail.jpg"
        thumbnail = generate_thumbnail(
            analysis,
            metadata,
            thumbnail_path,
            custom_frame=options.custom_thumbnail,
        )

        progress.update(task, description="[green]✓ Thumbnail created[/green]")

    # Display generated metadata
    console.print(f"\n[bold]Title:[/bold] {metadata.title}")
    console.print(f"[bold]Tags:[/bold] {', '.join(metadata.tags[:5])}...")

    result = ProcessResult(
        video_path=video_path,
        analysis=analysis,
        metadata=metadata,
        thumbnail=thumbnail,
    )

    # Step 4: Dry run stops here
    if options.dry_run:
        console.print("\n[yellow]Dry run - not uploading[/yellow]")
        result.status = "dry_run"
        return result

    # Step 5: Upload or request approval
    if options.skip_approval:
        # Upload immediately
        console.print("\n[bold]Uploading to YouTube...[/bold]")
        upload_result = upload_video(
            video_path,
            metadata,
            thumbnail.path,
            privacy=options.privacy,
        )
        result.upload_result = upload_result
        result.status = "uploaded"

        console.print(f"\n[green]✓ Uploaded![/green]")
        console.print(f"[bold]URL:[/bold] {upload_result.url}")
    else:
        # Create approval request
        request = create_approval_request(
            video_path,
            metadata,
            thumbnail.path,
        )
        result.request_id = request.request_id

        # Send Telegram notification
        sent = send_telegram_approval(request, analysis)

        if sent:
            console.print(f"\n[yellow]📱 Approval request sent to Telegram[/yellow]")
            console.print(f"[bold]Request ID:[/bold] {request.request_id}")
        else:
            console.print(f"\n[yellow]Waiting for approval[/yellow]")
            console.print(f"[bold]Request ID:[/bold] {request.request_id}")
            console.print(f"Run: [cyan]1minautoyt approve {request.request_id}[/cyan]")

        result.status = "pending"

    return result


def execute_upload(request_data: dict) -> Optional[UploadResult]:
    """Execute an approved upload request.

    Args:
        request_data: The approved request data from approval system

    Returns:
        UploadResult if successful, None otherwise
    """
    from .metadata import VideoMetadata

    video_path = Path(request_data["video_path"])
    thumbnail_path = Path(request_data["thumbnail_path"])

    if not video_path.exists():
        console.print(f"[red]Error: Video not found: {video_path}[/red]")
        return None

    metadata = VideoMetadata(
        title=request_data["title"],
        description=request_data["description"],
        tags=request_data["tags"],
        category_id=request_data["category_id"],
        suggested_thumbnail_index=0,
    )

    console.print(f"\n[bold]Uploading:[/bold] {video_path.name}")
    console.print(f"[bold]Title:[/bold] {metadata.title}")

    try:
        result = upload_video(
            video_path,
            metadata,
            thumbnail_path if thumbnail_path.exists() else None,
        )

        console.print(f"\n[green]✓ Upload complete![/green]")
        console.print(f"[bold]URL:[/bold] {result.url}")

        return result

    except Exception as e:
        console.print(f"[red]Upload failed: {e}[/red]")
        return None

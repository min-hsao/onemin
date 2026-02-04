"""CLI interface for 1MinAutoYT."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table

app = typer.Typer(
    name="onemin",
    help="Upload YouTube videos in one minute. Automated metadata, thumbnails, and publishing.",
    add_completion=False,
)
console = Console()


def print_banner():
    """Print the app banner."""
    console.print(Panel.fit(
        "[bold cyan]OneMin[/bold cyan]\n"
        "[dim]Upload YouTube videos in one minute[/dim]",
        border_style="cyan",
    ))


@app.command()
def config(
    watch_folder: Optional[str] = typer.Option(None, "--watch-folder", "-w", help="Set watch folder path"),
    channel: Optional[str] = typer.Option(None, "--channel", "-c", help="Set YouTube channel"),
    privacy: Optional[str] = typer.Option(None, "--privacy", "-p", help="Set default privacy (unlisted, private, public)"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
):
    """Configure 1MinAutoYT settings."""
    from .config import get_settings, reload_settings

    settings = get_settings()

    if show:
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Watch Folder", settings.watch_folder)
        table.add_row("YouTube Channel", settings.youtube_channel)
        table.add_row("Default Privacy", settings.default_privacy)
        table.add_row("Thumbnail Style", settings.thumbnail_style)
        table.add_row("AI Provider", settings.ai_provider)
        table.add_row("Telegram Configured", "Yes" if settings.telegram_bot_token else "No")
        table.add_row("YouTube API Configured", "Yes" if settings.youtube_client_id else "No")

        console.print(table)
        return

    # Interactive config if no options provided
    if not any([watch_folder, channel, privacy]):
        print_banner()
        console.print("\n[bold]Configuration Setup[/bold]\n")

        watch_folder = Prompt.ask(
            "Watch folder path",
            default=settings.watch_folder,
        )

        channel = Prompt.ask(
            "YouTube channel name",
            default=settings.youtube_channel,
        )

        privacy = Prompt.ask(
            "Default privacy",
            choices=["unlisted", "private", "public"],
            default=settings.default_privacy,
        )

        telegram_token = Prompt.ask(
            "Telegram bot token (for approvals)",
            default=settings.telegram_bot_token or "",
        )

        telegram_chat_id = Prompt.ask(
            "Telegram chat ID",
            default=settings.telegram_chat_id or "",
        )

        if telegram_token:
            settings.telegram_bot_token = telegram_token
        if telegram_chat_id:
            settings.telegram_chat_id = telegram_chat_id

    # Apply settings
    if watch_folder:
        settings.watch_folder = watch_folder
    if channel:
        settings.youtube_channel = channel
    if privacy:
        settings.default_privacy = privacy

    settings.save()
    console.print("[green]✓ Configuration saved![/green]")


@app.command()
def watch(
    folder: Optional[str] = typer.Option(None, "--folder", "-f", help="Folder to watch"),
    process_existing: bool = typer.Option(False, "--existing", "-e", help="Process existing videos first"),
):
    """Watch folder for new videos and process automatically."""
    from .watcher import watch_folder as start_watching, process_existing_videos
    from .pipeline import process_video

    print_banner()

    if process_existing:
        console.print("[yellow]Processing existing videos...[/yellow]")
        count = process_existing_videos(process_video, folder)
        console.print(f"[green]Processed {count} existing videos[/green]")

    folder_path = Path(folder).expanduser() if folder else None
    start_watching(process_video, folder_path, blocking=True)


@app.command()
def upload(
    video: str = typer.Argument(..., help="Path to video file"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Custom title (skip AI generation)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Custom description"),
    thumbnail: Optional[str] = typer.Option(None, "--thumbnail", help="Custom thumbnail image"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    privacy: Optional[str] = typer.Option(None, "--privacy", "-p", help="Privacy status"),
    skip_approval: bool = typer.Option(False, "--yes", "-y", help="Skip approval, upload immediately"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Analyze and generate metadata only, don't upload"),
):
    """Upload a video to YouTube."""
    from .pipeline import process_video, ProcessOptions

    print_banner()

    video_path = Path(video).expanduser()
    if not video_path.exists():
        console.print(f"[red]Error: Video not found: {video}[/red]")
        raise typer.Exit(1)

    options = ProcessOptions(
        custom_title=title,
        custom_description=description,
        custom_thumbnail=Path(thumbnail).expanduser() if thumbnail else None,
        custom_tags=tags.split(",") if tags else None,
        privacy=privacy,
        skip_approval=skip_approval,
        dry_run=dry_run,
    )

    process_video(video_path, options)


@app.command()
def analyze(
    video: str = typer.Argument(..., help="Path to video file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output JSON file"),
):
    """Analyze a video and generate metadata (no upload)."""
    from .analyzer import analyze_video
    from .metadata import generate_metadata
    import json

    print_banner()

    video_path = Path(video).expanduser()
    if not video_path.exists():
        console.print(f"[red]Error: Video not found: {video}[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Analyze video
        task = progress.add_task("Analyzing video...", total=None)
        analysis = analyze_video(video_path)
        progress.update(task, description="[green]✓ Analysis complete[/green]")

        # Generate metadata
        task = progress.add_task("Generating metadata...", total=None)
        metadata = generate_metadata(analysis)
        progress.update(task, description="[green]✓ Metadata generated[/green]")

    # Display results
    console.print("\n[bold cyan]Generated Metadata:[/bold cyan]\n")

    console.print(f"[bold]Title:[/bold] {metadata.title}")
    console.print(f"\n[bold]Description:[/bold]\n{metadata.description}")
    console.print(f"\n[bold]Tags:[/bold] {', '.join(metadata.tags)}")
    console.print(f"\n[bold]Category ID:[/bold] {metadata.category_id}")
    console.print(f"[bold]Suggested Frame:[/bold] #{metadata.suggested_thumbnail_index}")

    # Save to JSON if requested
    if output:
        data = {
            "video": str(video_path),
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
            "category_id": metadata.category_id,
            "suggested_thumbnail_index": metadata.suggested_thumbnail_index,
            "transcript": analysis.transcript,
            "video_info": {
                "duration": analysis.video_info.duration,
                "width": analysis.video_info.width,
                "height": analysis.video_info.height,
            },
        }
        with open(output, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"\n[green]✓ Saved to {output}[/green]")


@app.command()
def approve(
    request_id: str = typer.Argument(..., help="Request ID to approve"),
):
    """Approve a pending upload request."""
    from .approval import approve_request, get_request
    from .pipeline import execute_upload

    request = get_request(request_id)
    if not request:
        console.print(f"[red]Request not found: {request_id}[/red]")
        raise typer.Exit(1)

    if request.get("status") != "pending":
        console.print(f"[yellow]Request is already {request.get('status')}[/yellow]")
        raise typer.Exit(1)

    approve_request(request_id)
    console.print(f"[green]✓ Approved request {request_id}[/green]")

    # Execute upload
    execute_upload(request)


@app.command()
def reject(
    request_id: str = typer.Argument(..., help="Request ID to reject"),
):
    """Reject a pending upload request."""
    from .approval import reject_request, get_request

    request = get_request(request_id)
    if not request:
        console.print(f"[red]Request not found: {request_id}[/red]")
        raise typer.Exit(1)

    reject_request(request_id)
    console.print(f"[yellow]✗ Rejected request {request_id}[/yellow]")


@app.command()
def status():
    """Show status of pending upload requests."""
    from .approval import list_pending, load_pending_requests

    all_requests = load_pending_requests()
    pending = list_pending()

    if not all_requests:
        console.print("[dim]No upload requests[/dim]")
        return

    table = Table(title="Upload Requests")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Created")

    for req in all_requests.values():
        status_style = {
            "pending": "yellow",
            "approved": "green",
            "rejected": "red",
        }.get(req.get("status", "unknown"), "white")

        table.add_row(
            req.get("request_id", "?"),
            req.get("title", "?")[:40] + "...",
            f"[{status_style}]{req.get('status', 'unknown')}[/{status_style}]",
            req.get("created_at", "?")[:10],
        )

    console.print(table)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """1MinAutoYT - Upload YouTube videos in one minute."""
    if ctx.invoked_subcommand is None:
        # Interactive mode when no command specified
        print_banner()
        console.print("\n[bold]Interactive Mode[/bold]")
        console.print("Use --help to see available commands\n")

        # Show quick menu
        console.print("What would you like to do?")
        console.print("  [cyan]1[/cyan] - Upload a video")
        console.print("  [cyan]2[/cyan] - Watch folder for videos")
        console.print("  [cyan]3[/cyan] - Configure settings")
        console.print("  [cyan]4[/cyan] - Check pending uploads")
        console.print("  [cyan]q[/cyan] - Quit")

        choice = Prompt.ask("\nChoice", choices=["1", "2", "3", "4", "q"], default="q")

        if choice == "1":
            video = Prompt.ask("Video path")
            ctx.invoke(upload, video=video)
        elif choice == "2":
            ctx.invoke(watch)
        elif choice == "3":
            ctx.invoke(config)
        elif choice == "4":
            ctx.invoke(status)
        else:
            console.print("[dim]Goodbye![/dim]")


if __name__ == "__main__":
    app()

"""Folder watcher for automatic video detection."""

import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from .config import get_settings


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


class VideoHandler(FileSystemEventHandler):
    """Handle new video files in the watch folder."""

    def __init__(
        self,
        callback: Callable[[Path], None],
        extensions: Optional[set[str]] = None,
    ):
        self.callback = callback
        self.extensions = extensions or VIDEO_EXTENSIONS
        self._processing: set[str] = set()

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        path = Path(event.src_path)

        if path.suffix.lower() not in self.extensions:
            return

        # Avoid processing the same file multiple times
        if str(path) in self._processing:
            return

        # Wait a bit for the file to finish copying
        self._wait_for_file_ready(path)

        if not path.exists():
            return

        self._processing.add(str(path))

        try:
            print(f"New video detected: {path.name}")
            self.callback(path)
        finally:
            self._processing.discard(str(path))

    def _wait_for_file_ready(
        self,
        path: Path,
        timeout: int = 300,
        check_interval: int = 2,
    ) -> bool:
        """Wait for a file to finish being written.

        Checks if file size is stable over time.
        """
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            if not path.exists():
                return False

            current_size = path.stat().st_size

            if current_size == last_size and current_size > 0:
                # Size hasn't changed, file is ready
                return True

            last_size = current_size
            time.sleep(check_interval)

        return False


def watch_folder(
    callback: Callable[[Path], None],
    folder: Optional[Path] = None,
    blocking: bool = True,
) -> Optional[Observer]:
    """Watch a folder for new video files.

    Args:
        callback: Function to call when a new video is detected
        folder: Folder to watch. Uses config watch_folder if None.
        blocking: If True, blocks until interrupted. If False, returns observer.

    Returns:
        Observer instance if blocking=False, None otherwise
    """
    settings = get_settings()
    watch_path = Path(folder) if folder else Path(settings.watch_folder).expanduser()

    if not watch_path.exists():
        print(f"Creating watch folder: {watch_path}")
        watch_path.mkdir(parents=True, exist_ok=True)

    handler = VideoHandler(callback)
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=False)
    observer.start()

    print(f"Watching for videos in: {watch_path}")
    print("Press Ctrl+C to stop")

    if blocking:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\nStopped watching")
        observer.join()
        return None
    else:
        return observer


def process_existing_videos(
    callback: Callable[[Path], None],
    folder: Optional[Path] = None,
) -> int:
    """Process any existing videos in the watch folder.

    Returns the number of videos processed.
    """
    settings = get_settings()
    watch_path = Path(folder) if folder else Path(settings.watch_folder).expanduser()

    if not watch_path.exists():
        return 0

    count = 0
    for ext in VIDEO_EXTENSIONS:
        for video in watch_path.glob(f"*{ext}"):
            print(f"Found existing video: {video.name}")
            callback(video)
            count += 1

    return count

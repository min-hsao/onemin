"""YouTube upload functionality."""

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import get_config_dir, get_settings
from .metadata import VideoMetadata


@dataclass
class UploadResult:
    """Result of a YouTube upload."""

    video_id: str
    url: str
    title: str
    privacy: str


def get_youtube_service():
    """Get authenticated YouTube API service."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Google API libraries not installed. Run: "
            "pip install google-api-python-client google-auth-oauthlib"
        )

    config_dir = get_config_dir()
    token_file = config_dir / "youtube_token.pickle"
    secrets_file = config_dir / "client_secrets.json"

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]

    credentials = None

    # Load existing token
    if token_file.exists():
        with open(token_file, "rb") as f:
            credentials = pickle.load(f)

    # Refresh or get new token
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
        else:
            if not secrets_file.exists():
                raise FileNotFoundError(
                    f"client_secrets.json not found at {secrets_file}. "
                    "Download it from Google Cloud Console."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(secrets_file),
                SCOPES,
            )
            credentials = flow.run_local_server(port=8080)

        # Save token
        with open(token_file, "wb") as f:
            pickle.dump(credentials, f)

    return build("youtube", "v3", credentials=credentials)


def upload_video(
    video_path: Path,
    metadata: VideoMetadata,
    thumbnail_path: Optional[Path] = None,
    privacy: Optional[str] = None,
    notify_subscribers: bool = False,
) -> UploadResult:
    """Upload a video to YouTube.

    Args:
        video_path: Path to the video file
        metadata: Video metadata (title, description, tags, etc.)
        thumbnail_path: Path to custom thumbnail image
        privacy: Privacy status (private, unlisted, public). Uses config default if None.
        notify_subscribers: Whether to notify channel subscribers

    Returns:
        UploadResult with video ID and URL
    """
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        raise ImportError("googleapiclient not installed")

    settings = get_settings()
    privacy = privacy or settings.default_privacy

    youtube = get_youtube_service()

    # Video metadata
    body = {
        "snippet": {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
            "categoryId": metadata.category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
        "notifySubscribers": notify_subscribers,
    }

    # Upload video
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/*",
        resumable=True,
        chunksize=1024 * 1024 * 10,  # 10MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"Upload progress: {progress}%")

    video_id = response["id"]

    # Upload thumbnail if provided
    if thumbnail_path and thumbnail_path.exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
        ).execute()

    return UploadResult(
        video_id=video_id,
        url=f"https://youtube.com/watch?v={video_id}",
        title=metadata.title,
        privacy=privacy,
    )


def update_video_metadata(
    video_id: str,
    metadata: VideoMetadata,
) -> None:
    """Update metadata for an existing video."""
    youtube = get_youtube_service()

    body = {
        "id": video_id,
        "snippet": {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
            "categoryId": metadata.category_id,
        },
    }

    youtube.videos().update(
        part="snippet",
        body=body,
    ).execute()


def set_video_privacy(video_id: str, privacy: str) -> None:
    """Update the privacy status of a video."""
    youtube = get_youtube_service()

    youtube.videos().update(
        part="status",
        body={
            "id": video_id,
            "status": {"privacyStatus": privacy},
        },
    ).execute()


def set_video_thumbnail(video_id: str, thumbnail_path: Path) -> None:
    """Set the thumbnail for an existing video."""
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        raise ImportError("googleapiclient not installed")

    youtube = get_youtube_service()

    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
    ).execute()

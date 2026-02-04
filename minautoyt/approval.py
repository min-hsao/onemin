"""Telegram-based approval workflow."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from .config import get_settings, get_config_dir
from .metadata import VideoMetadata
from .analyzer import AnalysisResult


@dataclass
class ApprovalRequest:
    """A pending approval request."""

    request_id: str
    video_path: Path
    metadata: VideoMetadata
    thumbnail_path: Path
    created_at: str
    status: str = "pending"  # pending, approved, rejected


def get_pending_requests_file() -> Path:
    """Get the path to the pending requests JSON file."""
    return get_config_dir() / "pending_requests.json"


def load_pending_requests() -> dict[str, dict]:
    """Load pending requests from disk."""
    path = get_pending_requests_file()
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_pending_requests(requests: dict[str, dict]) -> None:
    """Save pending requests to disk."""
    path = get_pending_requests_file()
    with open(path, "w") as f:
        json.dump(requests, f, indent=2, default=str)


def create_approval_request(
    video_path: Path,
    metadata: VideoMetadata,
    thumbnail_path: Path,
) -> ApprovalRequest:
    """Create a new approval request."""
    import uuid
    from datetime import datetime

    request_id = str(uuid.uuid4())[:8]

    request = ApprovalRequest(
        request_id=request_id,
        video_path=video_path,
        metadata=metadata,
        thumbnail_path=thumbnail_path,
        created_at=datetime.now().isoformat(),
    )

    # Save to pending requests
    requests = load_pending_requests()
    requests[request_id] = {
        "request_id": request_id,
        "video_path": str(video_path),
        "title": metadata.title,
        "description": metadata.description,
        "tags": metadata.tags,
        "category_id": metadata.category_id,
        "thumbnail_path": str(thumbnail_path),
        "created_at": request.created_at,
        "status": "pending",
    }
    save_pending_requests(requests)

    return request


def send_telegram_approval(
    request: ApprovalRequest,
    analysis: Optional[AnalysisResult] = None,
) -> bool:
    """Send approval request to Telegram.

    Returns True if message was sent successfully.
    """
    settings = get_settings()

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print("Telegram not configured. Skipping approval notification.")
        return False

    bot_token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    # Format message
    message = f"""🎬 **New Video Ready for Upload**

**Title:** {request.metadata.title}

**Description:**
{request.metadata.description[:500]}{'...' if len(request.metadata.description) > 500 else ''}

**Tags:** {', '.join(request.metadata.tags[:5])}{'...' if len(request.metadata.tags) > 5 else ''}

**Video:** `{request.video_path.name}`
"""

    if analysis:
        message += f"""
**Duration:** {analysis.video_info.duration / 60:.1f} minutes
**Resolution:** {analysis.video_info.width}x{analysis.video_info.height}
"""

    message += f"""
**Request ID:** `{request.request_id}`

Reply with:
✅ `approve {request.request_id}` to upload
❌ `reject {request.request_id}` to cancel
✏️ `edit {request.request_id} title <new title>` to change title
"""

    # Send message
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        response = httpx.post(url, json=payload, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

    # Send thumbnail
    if request.thumbnail_path.exists():
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        with open(request.thumbnail_path, "rb") as f:
            files = {"photo": f}
            data = {
                "chat_id": chat_id,
                "caption": f"Thumbnail preview for {request.request_id}",
            }
            try:
                response = httpx.post(url, data=data, files=files, timeout=60)
            except Exception as e:
                print(f"Failed to send thumbnail: {e}")

    return True


def approve_request(request_id: str) -> Optional[dict]:
    """Mark a request as approved and return its data."""
    requests = load_pending_requests()

    if request_id not in requests:
        return None

    requests[request_id]["status"] = "approved"
    save_pending_requests(requests)

    return requests[request_id]


def reject_request(request_id: str) -> Optional[dict]:
    """Mark a request as rejected."""
    requests = load_pending_requests()

    if request_id not in requests:
        return None

    requests[request_id]["status"] = "rejected"
    save_pending_requests(requests)

    return requests[request_id]


def update_request_metadata(
    request_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Optional[dict]:
    """Update metadata for a pending request."""
    requests = load_pending_requests()

    if request_id not in requests:
        return None

    if title:
        requests[request_id]["title"] = title
    if description:
        requests[request_id]["description"] = description
    if tags:
        requests[request_id]["tags"] = tags

    save_pending_requests(requests)

    return requests[request_id]


def get_request(request_id: str) -> Optional[dict]:
    """Get a request by ID."""
    requests = load_pending_requests()
    return requests.get(request_id)


def list_pending() -> list[dict]:
    """List all pending requests."""
    requests = load_pending_requests()
    return [r for r in requests.values() if r.get("status") == "pending"]

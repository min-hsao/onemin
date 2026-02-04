# OneMin

> Upload YouTube videos in one minute. Automated metadata, thumbnails, and publishing.

## Features

- 📁 **Watch folder** — Drop videos in iCloud Drive, auto-detected
- 🎯 **AI-powered metadata** — Catchy titles, descriptions, and tags generated automatically
- 🖼️ **Mr. Beast-style thumbnails** — Bold, eye-catching thumbnails from video frames
- ✅ **Approval workflow** — Review via Telegram before publishing
- 🚀 **One-click upload** — Unlisted to YouTube with full metadata

## Installation

```bash
pip install onemin
```

Or from source:

```bash
git clone https://github.com/min-hsao/onemin.git
cd onemin
pip install -e .
```

## Quick Start

### Interactive Mode (step-by-step)

```bash
onemin
```

### CLI Mode (automation)

```bash
# Process a specific video
onemin upload video.mp4

# Process with custom title
onemin upload video.mp4 --title "My Custom Title"

# Watch folder for new videos
onemin watch

# Generate metadata only (no upload)
onemin analyze video.mp4
```

## Configuration

On first run, you'll be prompted to configure:

```bash
1minautoyt config
```

Or create `config.json` in the script directory:

```json
{
  "watch_folder": "~/Library/Mobile Documents/com~apple~CloudDocs/Documents/Upload",
  "youtube_channel": "minhsao",
  "default_privacy": "unlisted",
  "thumbnail_style": "mrbeast",
  "telegram_bot_token": "your-bot-token",
  "telegram_chat_id": "your-chat-id"
}
```

### API Keys

Create `.env` in the script directory:

```env
YOUTUBE_CLIENT_ID=your-client-id
YOUTUBE_CLIENT_SECRET=your-client-secret
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

## Usage

### 1. Setup YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Download `client_secrets.json` to script directory

### 2. Configure Watch Folder

```bash
1minautoyt config --watch-folder "~/path/to/your/folder"
```

### 3. Drop Videos

Place `.mp4` or `.mov` files in your watch folder. The script will:

1. Detect the new video
2. Extract key frames
3. Transcribe audio
4. Generate title, description, tags
5. Create thumbnail
6. Send Telegram approval request
7. Upload on approval

## CLI Reference

```
Usage: 1minautoyt [OPTIONS] COMMAND [ARGS]...

Commands:
  config    Configure settings
  watch     Watch folder for new videos
  upload    Upload a specific video
  analyze   Analyze video and generate metadata (no upload)
  approve   Manually approve a pending video
  status    Check status of pending uploads

Options:
  --config PATH    Path to config file
  --verbose        Enable verbose logging
  --help           Show this message and exit
```

## Thumbnail Styles

### Mr. Beast Style (default)

- Bold, thick text overlay
- Bright colors (yellow, red)
- Expressive face/reaction frame
- High contrast

### Custom Thumbnail

Provide your own:

```bash
1minautoyt upload video.mp4 --thumbnail my-thumbnail.png
```

## License

MIT

## Author

Min-Hsao Chen (@min-hsao)

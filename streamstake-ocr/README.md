# StreamStake OCR System

A high-performance Python OCR system that monitors gaming streams OR video files and detects phased transitions for StreamStake.

## Features
- **Real-time Detection**: Captures screen at ~2Hz using `mss` or reads from video file.
- **Game Support**: Valorant, CS2, League of Legends.
- **Phase Detection**: Identifies BETTING, LOCKED, and RESULT phases.
- **Resolution Scaling**: Auto-scales ROIs for 720p, 1080p, and 1440p streams.
- **Firebase Integration**: Pushes phase updates to Firebase Realtime Database.

## Prerequisites
- Python 3.9+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and added to PATH.

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd streamstake-ocr
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Environment:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Update `.env` with your Firebase credentials and target game settings.

## Usage

### Screen Capture Mode
Default mode. Captures your primary display.
```bash
python main.py
```

### Video File Mode
To test with a pre-recorded gameplay video, add the path to your `.env` file:
```env
VIDEO_PATH=C:/path/to/gameplay.mp4
STREAM_RESOLUTION=1920x1080  # Ensure this matches video resolution
```
Or set it temporarily in the shell:
```bash
# Windows PowerShell
$env:VIDEO_PATH="match_recording.mp4"; python main.py
```

## Configuration

Edit `.env` to change settings:
- `TARGET_GAME`: `valorant`, `cs2`, or `league`
- `STREAM_RESOLUTION`: e.g., `1920x1080`
- `CAPTURE_FPS`: Capture rate (default: 2)
- `DEBUG_MODE`: Set to `true` for verbose logging
- `VIDEO_PATH`: Absolute path to video file (optional)

## Testing

Run the included test suite:
```bash
python test_ocr.py
```

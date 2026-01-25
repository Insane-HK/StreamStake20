# StreamStake OCR Setup Guide

## Prerequisites

- Python 3.9+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- **FFmpeg** (Required for reliable stream processing)

## Installing FFmpeg on Windows

FFmpeg is required for the system to read video streams from YouTube/Twitch reliably.

### Option 1: Using Winget (Recommended)
Open PowerShell as Administrator and run:
```powershell
winget install "FFmpeg (Essentials Build)"
```
Restart your terminal after installation.

### Option 2: Manual Installation
1. Download a build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z).
2. Extract the archive (e.g., to `C:\ffmpeg`).
3. Add `C:\ffmpeg\bin` to your System PATH environment variable.
4. Restart your terminal.

## Configuration

If you cannot add FFmpeg to your global PATH, you can set the path in your `.env` file:

```env
FFMPEG_PATH=path/to/ffmpeg.exe
```

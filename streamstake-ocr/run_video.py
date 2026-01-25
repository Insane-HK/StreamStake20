import os

# Set environment variables programmatically BEFORE importing main
# This ensures that when main imports config/ocr_detector, the env vars are already set.
os.environ['VIDEO_PATH'] = r"D:\Coding\Projects\SERIOUS\Ai go\videoplayback.mp4"
os.environ['TESSERACT_PATH'] = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

import main

if __name__ == "__main__":
    print(f"Running StreamStake OCR with video: {os.environ['VIDEO_PATH']}")
    try:
        main.main()
    except KeyboardInterrupt:
        print("\nStopped by user.")

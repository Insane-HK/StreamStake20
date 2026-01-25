import streamlink
import cv2
import numpy as np
import pytesseract
import pytesseract

# Explicitly point to the .exe you just found
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Test it immediately
print(f"Tesseract version: {pytesseract.get_tesseract_version()}")
# 1. Setup Streamlink for 1080p
yt_url = "https://www.youtube.com/watch?v=E2UhYSqLYzk"
streams = streamlink.streams(yt_url)

# Select 1080p specifically
if '1080p' in streams:
    stream_url = streams['1080p'].url
else:
    stream_url = streams['best'].url # Fallback if 1080p is unavailable

# 2. Open the Stream
cap = cv2.VideoCapture(stream_url)

# 1080p Coordinates for Valorant Timer (Approximate)
# Format: [y_start : y_end, x_start : x_end]
# These target the area just below the top score bar
TIMER_ROI = [35, 95, 880, 1040] 

print("Oracle is watching... Press 'q' to stop.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 3. Snippet: Crop to the Timer Region
    y1, y2, x1, x2 = TIMER_ROI
    roi = frame[y1:y2, x1:x2]

    # 4. Pre-processing for OCR Accuracy
    # Convert to grayscale and invert if necessary to make text pop
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY)

    # 5. Run Tesseract (PSM 7: Single line of text)
    text = pytesseract.image_to_string(thresh, config='--psm 7').strip().upper()

    # Log the detected state
    if text:
        print(f"Detected: {text}")

    # Visual Feedback
    cv2.imshow('1080p OCR Feed', thresh)
    
    # Process every 30th frame (1 frame per second) to keep it lightweight
    for _ in range(30):
        cap.grab()

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
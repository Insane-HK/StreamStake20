import cv2
import os

video_path = r"D:\Coding\Projects\SERIOUS\Ai go\videoplayback (2).mp4"

if not os.path.exists(video_path):
    print(f"File not found: {video_path}")
else:
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        print(f"Video Resolution: {width}x{height}")
        print(f"FPS: {fps}")
    else:
        print("Failed to open video.")
    cap.release()

import cv2
import os
import numpy as np
from dotenv import load_dotenv
from config import GAME_CONFIGS, Game, Phase
from ocr_detector import preprocess_for_ocr

load_dotenv()

def test_roi_extraction():
    """Visual test to verify ROI positioning"""
    video_path = os.getenv('VIDEO_PATH')
    if not video_path:
        print("Error: VIDEO_PATH not set in .env")
        return

    cap = cv2.VideoCapture(video_path)
    
    # Jump to a frame with "BUY PHASE" 
    # Attempt to find a good frame or just use 500 as suggested
    cap.set(cv2.CAP_PROP_POS_FRAMES, 500)
    ret, frame = cap.read()
    
    if not ret:
        print("Cannot read frame")
        return
    
    print(f"Testing ROIs on frame from {video_path}")
    
    # Get Valorant config
    valorant_config = GAME_CONFIGS[Game.VALORANT]
    
    # Check scaling (assume video might be 720p vs 1080p config)
    # But for this test, let's just use raw config and assume 1080p source or scaling logic logic
    # The config is based on 1080p. If video is 720p, we need to map.
    # We should use get_scale_factor from utils ideally, or just hardcode for valid test if we know video is 720p
    # Let's import get_scale_factor
    from utils import get_scale_factor
    resolution_str = cx = os.getenv('STREAM_RESOLUTION', '1920x1080')
    # Actually we need video resolution
    vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video Resolution: {vid_w}x{vid_h}")
    
    # Calculate scale factor relative to base 1080p
    scale_x = vid_w / 1920
    scale_y = vid_h / 1080
    scale_factor = min(scale_x, scale_y) # Preserve aspect ratio usually, or just scale_x?
    # Our system uses single scale_factor usually.
    print(f"Scale Factor: {scale_factor}")

    for phase_enum, config in valorant_config.items():
        phase_name = phase_enum.name
        roi = config['roi']
        x, y, w, h = roi['x'], roi['y'], roi['width'], roi['height']
        
        # Scale
        x = int(x * scale_factor)
        y = int(y * scale_factor)
        w = int(w * scale_factor)
        h = int(h * scale_factor)

        # Extract ROI
        roi_img = frame[y:y+h, x:x+w]
        
        if roi_img.size == 0:
            print(f"Empty ROI for {phase_name}")
            continue

        # Show original
        cv2.imshow(f'{phase_name} - Original', roi_img)
        
        # Show preprocessed
        processed = preprocess_for_ocr(roi_img, config.get('preprocess', 'default'))
        cv2.imshow(f'{phase_name} - Preprocessed', processed)
    
    print("Press any key to close windows...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_roi_extraction()

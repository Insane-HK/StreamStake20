
import cv2
import numpy as np
import os
import pytesseract
from ocr_detector import detect_text_in_roi, match_keywords, TEMPLATES, preprocess_for_ocr
from config import GAME_CONFIGS, Game, Phase

# Paths to user uploaded images (hardcoded for this run based on session context)
TEST_IMAGES = [
    r"C:/Users/honey/.gemini/antigravity/brain/1d98e02f-60cb-41e0-b3ff-47f485ca0c33/uploaded_media_0_1769231663127.png",
    r"C:/Users/honey/.gemini/antigravity/brain/1d98e02f-60cb-41e0-b3ff-47f485ca0c33/uploaded_media_1_1769231663127.png",
    r"C:/Users/honey/.gemini/antigravity/brain/1d98e02f-60cb-41e0-b3ff-47f485ca0c33/uploaded_media_2_1769231663127.png",
    r"C:/Users/honey/.gemini/antigravity/brain/1d98e02f-60cb-41e0-b3ff-47f485ca0c33/uploaded_media_1769232351675.png"
]

def test_on_image(img_path):
    if not os.path.exists(img_path):
        print(f"Skipping missing: {img_path}")
        return

    print(f"\n--- Testing: {os.path.basename(img_path)} ---")
    frame = cv2.imread(img_path)
    if frame is None:
        print("Failed to load image")
        return

    # Assuming 1080p geometry, calculate scale if image is different
    h, w = frame.shape[:2]
    scale_factor = w / 1920.0
    print(f"Resolution: {w}x{h} (Scale: {scale_factor:.2f})")

    game_config = GAME_CONFIGS[Game.VALORANT]

    # Test 1: Full Frame Template Search (Debug Misalignment)
    print("\n[Global Template Search]")
    if cv2.countNonZero(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)) > 0:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        for phase in [Phase.BETTING, Phase.RESULT]:
            if phase in TEMPLATES:
                template = TEMPLATES[phase]
                
                # Check multiple scales of template?
                # User's image is 0.53 scale. Template is 1.0.
                # We need to resize template to match image scale.
                t_h, t_w = template.shape[:2]
                target_w = int(t_w * scale_factor)
                target_h = int(t_h * scale_factor)
                
                if target_w > 0 and target_h > 0:
                    resized_template = cv2.resize(template, (target_w, target_h))
                    
                    # Match in FULL FRAME
                    res = cv2.matchTemplate(gray_frame, resized_template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    print(f"  {phase.name} Found at {max_loc} with Conf: {max_val:.4f}")
                    if max_val > 0.5:
                        print(f"    -> Expected ROI Start should be around: {max_loc}")
                else:
                    print(f"  {phase.name}: Template too small after scaling")

    # Test 2: OCR Threshold Sweeps
    print("\n[OCR Threshold Sweep]")
    
    phases_to_test = [Phase.BETTING, Phase.LOCKED, Phase.OWN_SCORE, Phase.ENEMY_SCORE]
    
    for phase in phases_to_test:
        print(f"  Checking {phase.name}...")
        config = game_config.get(phase)
        if not config: continue
        
        # Testing different fixed thresholds
        for thresh in [120, 150, 180, 200, 220, 'OTSU']:
            # Manually preprocessing to test threshold
            roi_def = config['roi']
            x = int(roi_def['x'] * scale_factor)
            y = int(roi_def['y'] * scale_factor)
            w_roi = int(roi_def['width'] * scale_factor)
            h_roi = int(roi_def['height'] * scale_factor)
            roi = frame[y:y+h_roi, x:x+w_roi]
            
            if roi.size == 0: continue
            
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            if thresh == 'OTSU':
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            else:
                _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
            
            inverted = cv2.bitwise_not(binary)
            
            # Upscale
            cleaned = inverted # skip morphological for raw test
            h_i, w_i = cleaned.shape
            upscaled = cv2.resize(cleaned, (w_i*3, h_i*3), interpolation=cv2.INTER_CUBIC)
            
            # Run Tesseract
            psm = config.get('psm', 7)
            wl = config.get('whitelist', '')
            tess_config = f'--psm {psm}'
            if wl: tess_config += f' -c tessedit_char_whitelist={wl}'
            
            try:
                text = pytesseract.image_to_string(upscaled, config=tess_config).strip()
                print(f"    Thresh {thresh}: '{text}'")
            except Exception as e:
                pass

if __name__ == "__main__":
    for img in TEST_IMAGES:
        test_on_image(img)

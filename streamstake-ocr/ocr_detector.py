
import cv2
import pytesseract
import numpy as np
import logging
from config import Game, Phase, GAME_CONFIGS
import os

logger = logging.getLogger('StreamStakeOCR')

# Set tesseract path from env if provided
tesseract_path = os.getenv('TESSERACT_PATH')
if tesseract_path:
    tesseract_path = tesseract_path.strip('"').strip("'")
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

def preprocess_for_ocr(image: np.ndarray, method: str) -> np.ndarray:
    """
    Preprocess ROI for optimal Tesseract detection
    """
    if method == 'white_text_on_dark':
        # For "BUY PHASE" banner
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # More aggressive contrast
        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Stronger threshold (Fixed high validation for UI)
        # Lowered to 150 to catch fainter white Text
        _, binary = cv2.threshold(enhanced, 150, 255, cv2.THRESH_BINARY)
        
        # Invert for Tesseract
        inverted = cv2.bitwise_not(binary)
        
        # More aggressive denoising
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(inverted, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        # Larger upscale (3x instead of 2x)
        height, width = cleaned.shape
        upscaled = cv2.resize(cleaned, (width*3, height*3), interpolation=cv2.INTER_CUBIC)
        
        return upscaled
    
    elif method == 'light_text':
        # For timer and scores
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Standard threshold for white text (Scoreboard digits are bright)
        # Lowered to 150 to avoid losing anti-aliased pixels
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Scores are usually white on dark/translucent. 
        # Tesseract needs black text on white background -> Invert
        inverted = cv2.bitwise_not(binary)
        
        # 4x upscale for small text
        height, width = inverted.shape
        upscaled = cv2.resize(inverted, (width*4, height*4), interpolation=cv2.INTER_CUBIC)
        
        return upscaled
    
    else:
        # Fallback
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

def match_keywords(detected_text: str, keywords: list) -> bool:
    """
    Check if detected text matches any expected keywords
    """
    detected_clean = detected_text.replace(' ', '').replace('\n', '').upper()
    
    for keyword in keywords:
        keyword_clean = keyword.replace(' ', '').upper()
        
        # Exact substring match
        if keyword_clean in detected_clean:
            return True
        
        # Fuzzy match for longer keywords (70% character overlap)
        if len(keyword_clean) > 3:
            matched = sum(1 for c in keyword_clean if c in detected_clean)
            if matched >= len(keyword_clean) * 0.7:
                return True
    
    return False

# Load templates
TEMPLATE_DIR = "templates"
TEMPLATES = {}
SCORE_TEMPLATES = {'own': {}, 'enemy': {}}
RESULT_TEMPLATES = {'win': [], 'loss': []}

def load_templates():
    # Load Phase Templates
    if not TEMPLATES:
        for phase in Phase:
            path = os.path.join(TEMPLATE_DIR, f"{phase.name}.png")
            if os.path.exists(path):
                img = cv2.imread(path)
                if img is not None:
                    TEMPLATES[phase] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    logger.info(f"Loaded template for {phase.name}")

    # Load Score Templates
    # Structure: templates/scores/own/0.png, 1.png...
    #            templates/scores/enemy/0.png, 1.png...
    score_base = os.path.join(TEMPLATE_DIR, "scores")
    for side in ['own', 'enemy']:
        side_dir = os.path.join(score_base, side)
        if os.path.exists(side_dir):
            for fname in os.listdir(side_dir):
                if fname.endswith('.png'):
                    try:
                        val = int(os.path.splitext(fname)[0])
                        path = os.path.join(side_dir, fname)
                        img = cv2.imread(path)
                        if img is not None:
                            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            SCORE_TEMPLATES[side][val] = gray
                    except ValueError:
                        pass
    
    # Load Result Templates
    # Structure: templates/results/win/xyz.png
    #            templates/results/loss/xyz.png
    result_base = os.path.join(TEMPLATE_DIR, "results")
    RESULT_TEMPLATES['win'] = []
    RESULT_TEMPLATES['loss'] = []
    
    for outcome in ['win', 'loss']:
        outcome_dir = os.path.join(result_base, outcome)
        if os.path.exists(outcome_dir):
            for fname in os.listdir(outcome_dir):
                if fname.endswith('.png'):
                    path = os.path.join(outcome_dir, fname)
                    img = cv2.imread(path)
                    if img is not None:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        RESULT_TEMPLATES[outcome].append(gray)

    logger.info(f"Loaded Templates: Score(Own={len(SCORE_TEMPLATES['own'])}, Enemy={len(SCORE_TEMPLATES['enemy'])}), Result(Win={len(RESULT_TEMPLATES['win'])}, Loss={len(RESULT_TEMPLATES['loss'])})")

load_templates()

def detect_template_in_roi(frame: np.ndarray, config: dict, scale_factor: float = 1.0, phase_enum: Phase = None) -> tuple[str, float]:
    """
    Check if the phase's template exists in the defined ROI.
    """
    if phase_enum not in TEMPLATES:
        return None, 0.0

    template = TEMPLATES[phase_enum]
    roi_def = config['roi']
    
    # Scale ROI
    x = int(roi_def['x'] * scale_factor)
    y = int(roi_def['y'] * scale_factor)
    w = int(roi_def['width'] * scale_factor)
    h = int(roi_def['height'] * scale_factor)
    
    # Boundary checks
    fh, fw = frame.shape[:2]
    x = max(0, min(x, fw-1))
    y = max(0, min(y, fh-1))
    w = max(1, min(w, fw-x))
    h = max(1, min(h, fh-y))
    
    # Extract ROI
    roi_image = frame[y:y+h, x:x+w]
    if roi_image.size == 0 or roi_image.shape[0] < template.shape[0] or roi_image.shape[1] < template.shape[1]:
        return None, 0.0

    # Convert ROI to gray
    if len(roi_image.shape) == 3:
        roi_gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
    else:
        roi_gray = roi_image

    # Match Template
    try:
        # Resize template if ROI is significantly different due to scaling
        # (Naive approach: assume template is built for 1080p, so if scale_factor != 1, resize template)
        # However, simpler to just run matchTemplate and rely on the fact that ROIs capture the area.
        # Ideally, we should resize the template by scale_factor too if the game UI scales.
        
        curr_template = template
        # Re-enable resizing for Phase templates (e.g. BETTING) as they might be 1080p originals.
        if scale_factor != 1.0:
            th, tw = template.shape
            curr_template = cv2.resize(template, (int(tw * scale_factor), int(th * scale_factor)))
            
        # Check size again after resize
        if roi_gray.shape[0] < curr_template.shape[0] or roi_gray.shape[1] < curr_template.shape[1]:
             return None, 0.0
             
        res = cv2.matchTemplate(roi_gray, curr_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        return "TEMPLATE_MATCH", max_val
        
    except Exception as e:
        logger.error(f"Template Matching Error for {phase_enum}: {e}")
        return None, 0.0

def detect_score_with_templates(frame: np.ndarray, config: dict, scale_factor: float, phase_enum: Phase) -> tuple[str, float]:
    """
    Match ROI against set of digit templates.
    """
    side = 'own' if phase_enum == Phase.OWN_SCORE else 'enemy'
    available_templates = SCORE_TEMPLATES.get(side, {})
    
    if not available_templates:
        return None, 0.0

    roi_def = config['roi']
    # Scale ROI
    x = int(roi_def['x'] * scale_factor)
    y = int(roi_def['y'] * scale_factor)
    w = int(roi_def['width'] * scale_factor)
    h = int(roi_def['height'] * scale_factor)
    
    # Extract ROI
    fh, fw = frame.shape[:2]
    x = max(0, min(x, fw-1))
    y = max(0, min(y, fh-1))
    w = max(1, min(w, fw-x))
    h = max(1, min(h, fh-y))
    
    roi_image = frame[y:y+h, x:x+w]
    if roi_image.size == 0: return None, 0.0
    
    if len(roi_image.shape) == 3:
        roi_gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
    else:
        roi_gray = roi_image
        
    best_match_val = -1
    best_score_conf = 0.0
    
    for score_val, tmpl in available_templates.items():
        # Handle Scaling (naive)
        curr_tmpl = tmpl
        # DISABLE RESIZING: Assumes templates are captured from the current resolution source.
        # This fixes the issue where 720p templates were being shrunk by 0.67x again.
        # if scale_factor != 1.0:
        #      th, tw = tmpl.shape
        #      curr_tmpl = cv2.resize(tmpl, (int(tw * scale_factor), int(th * scale_factor)))
             
        # Template match
        if roi_gray.shape[0] < curr_tmpl.shape[0] or roi_gray.shape[1] < curr_tmpl.shape[1]:
            continue
            
        res = cv2.matchTemplate(roi_gray, curr_tmpl, cv2.TM_CCOEFF_NORMED)
        min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
        
        if max_v > best_score_conf:
            best_score_conf = max_v
            best_match_val = score_val
            
    if best_match_val != -1:
        if best_score_conf > 0.85: # Increased threshold to 0.85 to strict match
            return str(best_match_val), best_score_conf
        else:
            # DEBUG: Log if we are close but rejected
            # if best_score_conf > 0.5:
            #    logger.debug(f"Rejected Score {side} '{best_match_val}' (Conf: {best_score_conf:.2f}) < 0.85")
            pass
        
    return None, 0.0

def detect_result_with_templates(frame: np.ndarray, config: dict, scale_factor: float) -> tuple[str, float]:
    """
    Match Result ROI against 'win' and 'loss' templates.
    Returns: ('WIN_TEMPLATE' | 'LOSS_TEMPLATE', confidence)
    """
    roi_def = config['roi']
    # Scale ROI
    x = int(roi_def['x'] * scale_factor)
    y = int(roi_def['y'] * scale_factor)
    w = int(roi_def['width'] * scale_factor)
    h = int(roi_def['height'] * scale_factor)
    
    # Extract ROI
    fh, fw = frame.shape[:2]
    x = max(0, min(x, fw-1))
    y = max(0, min(y, fh-1))
    w = max(1, min(w, fw-x))
    h = max(1, min(h, fh-y))
    
    roi_image = frame[y:y+h, x:x+w]
    if roi_image.size == 0: return None, 0.0
    
    if len(roi_image.shape) == 3:
        roi_gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
    else:
        roi_gray = roi_image
        
    best_outcome = None
    best_conf = 0.0
    
    # Check WIN templates
    for tmpl in RESULT_TEMPLATES['win']:
        curr_tmpl = tmpl
        # DISABLE RESIZING
        # if scale_factor != 1.0:
        #      th, tw = tmpl.shape
        #      curr_tmpl = cv2.resize(tmpl, (int(tw * scale_factor), int(th * scale_factor)))
        
        if roi_gray.shape[0] < curr_tmpl.shape[0] or roi_gray.shape[1] < curr_tmpl.shape[1]: continue
        
        res = cv2.matchTemplate(roi_gray, curr_tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_v, _, _ = cv2.minMaxLoc(res)
        if max_v > best_conf:
            best_conf = max_v
            best_outcome = "WIN_TEMPLATE"

    # Check LOSS templates
    for tmpl in RESULT_TEMPLATES['loss']:
        curr_tmpl = tmpl
        # DISABLE RESIZING
        # if scale_factor != 1.0:
        #      th, tw = tmpl.shape
        #      curr_tmpl = cv2.resize(tmpl, (int(tw * scale_factor), int(th * scale_factor)))
        
        if roi_gray.shape[0] < curr_tmpl.shape[0] or roi_gray.shape[1] < curr_tmpl.shape[1]: continue
        
        res = cv2.matchTemplate(roi_gray, curr_tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_v, _, _ = cv2.minMaxLoc(res)
        if max_v > best_conf:
            best_conf = max_v
            best_outcome = "LOSS_TEMPLATE"
            
    if best_outcome and best_conf > 0.65:
        return best_outcome, best_conf
        
    return None, 0.0

def detect_text_in_roi(frame: np.ndarray, config: dict, scale_factor: float = 1.0, phase_enum: Phase = None) -> tuple[str, float]:
    """
    Extract and recognize text from ROI.
    """
    roi_def = config['roi']
    
    # Scale ROI
    x = int(roi_def['x'] * scale_factor)
    y = int(roi_def['y'] * scale_factor)
    w = int(roi_def['width'] * scale_factor)
    h = int(roi_def['height'] * scale_factor)
    
    # Boundary checks
    fh, fw = frame.shape[:2]
    x = max(0, min(x, fw-1))
    y = max(0, min(y, fh-1))
    w = max(1, min(w, fw-x))
    h = max(1, min(h, fh-y))
    
    # Extract ROI
    roi_image = frame[y:y+h, x:x+w]
    if roi_image.size == 0:
        return "", 0.0
        
    # Preprocess
    processed = preprocess_for_ocr(roi_image, config.get('preprocess', 'default'))
    
    # Build Tesseract config
    psm = config.get('psm', 7)
    whitelist = config.get('whitelist', '')
    
    tess_config = f'--psm {psm}'
    if whitelist:
        tess_config += f' -c tessedit_char_whitelist={whitelist}'
    
    # DEBUG: Save preprocessed image for Scores to check visuals
    if phase_enum in [Phase.OWN_SCORE, Phase.ENEMY_SCORE]:
        cv2.imwrite(f"debug_prop_{phase_enum.name}.png", processed)
        logger.info(f"DEBUG: Saved debug_prop_{phase_enum.name}.png - Starting OCR...")

    try:
        # Get text AND confidence in one go to save time
        data = pytesseract.image_to_data(processed, config=tess_config, output_type=pytesseract.Output.DICT, timeout=2)
        
        # Parse results
        text_parts = []
        confidences = []
        
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > -1 and data['text'][i].strip():
                text_parts.append(data['text'][i])
                confidences.append(int(data['conf'][i]))
        
        text = " ".join(text_parts).strip().upper()
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Normalize confidence to 0.0 - 1.0
        return text, avg_confidence / 100.0
        
    except RuntimeError as e:
        logger.warning(f"OCR Timeout: {e}")
        return "", 0.0
    except Exception as e:
        logger.error(f"OCR Error: {e} | Config: {tess_config}")
        return "", 0.0

def analyze_frame(monitor, frame, game, scale_factor=1.0):
    """
    Detect game phases and scores from frame.
    Returns: (primary_phase, primary_confidence, all_detections_dict)
    """
    game_config = GAME_CONFIGS.get(game)
    if not game_config:
        return None, 0.0, {}
        
    all_detections = {}
    
    # Sort for primary phase determination
    phases_with_priority = []
    for phase_enum, p_config in game_config.items():
        priority = p_config.get('priority', 999)
        phases_with_priority.append((priority, phase_enum, p_config))
        
    phases_with_priority.sort(key=lambda x: x[0])
    
    # Run Detection on ALL configured phases
    for priority, phase_enum, config in phases_with_priority:
        detected_text = None
        confidence = 0.0
        is_match = False
        
        # 1. Try Template Matching FIRST (if available)
        if phase_enum in TEMPLATES:
            # We treat the template match as "Text" being the specific Phase name for consistency
            _, tm_conf = detect_template_in_roi(frame, config, scale_factor, phase_enum)
            if tm_conf > 0.65: # Strong threshold for image match
                detected_text = f"TEMPLATE:{phase_enum.name}"
                confidence = tm_conf
                is_match = True
                # logger.debug(f"Template Match {phase_enum.name}: ({confidence:.2f})")
        
        # 2a. Try Score Template Matching (if Phase is Score)
        if not is_match and phase_enum in [Phase.OWN_SCORE, Phase.ENEMY_SCORE]:
             score_text, score_conf = detect_score_with_templates(frame, config, scale_factor, phase_enum)
             if score_text:
                 detected_text = score_text
                 confidence = score_conf
                 is_match = True
                 # logger.debug(f"Score Template Match {phase_enum.name}: '{score_text}' ({confidence:.2f})")

        # 2b. Try Result Template Matching (if Phase is Result)
        if not is_match and phase_enum == Phase.RESULT:
             res_text, res_conf = detect_result_with_templates(frame, config, scale_factor)
             if res_text:
                 detected_text = res_text
                 confidence = res_conf
                 is_match = True
                 # logger.debug(f"Result Template Match: '{res_text}' ({confidence:.2f})")

        # 3. Fallback to OCR if no template match
        # DISABLE COMPLETELY to prevent crashes/hangs and rely on Templates + Flow.
        # if not is_match:
        #     if phase_enum in [Phase.BETTING, Phase.LOCKED]:
        #         detected_text, confidence = detect_text_in_roi(frame, config, scale_factor, phase_enum)
        #     else:
        #         pass
        
        # If no template match, we assume NO DETECTION for this phase.
        # This relies on main.py's "Auto-transition" logic to handle LOCKED (Playing) state when nothing is detected.
        
        
        # Log RAW detection for debugging if enabled
        # if detected_text:
        #     logger.debug(f"RAW {phase_enum.name}: '{detected_text}' ({confidence:.2f})")
        
        # Check match
        keywords = config.get('keywords', [])
        is_match = False
        
        if detected_text: # Fix: Ensure detected_text is not None before checking
            if keywords:
                if match_keywords(detected_text, keywords):
                    is_match = True
            
            # DEBUG: Log raw score text to see what's happening
            # if phase_enum in [Phase.OWN_SCORE, Phase.ENEMY_SCORE]:
            #     logger.debug(f"DEBUG SCORE {phase_enum.name}: '{detected_text}' ({confidence:.2f})")

            # Check for digits/validity
            if any(c.isdigit() for c in detected_text):
                is_match = True
        else:
            # detected_text is None (template failed and OCR skipped)
            is_match = False
        
        if is_match and confidence >= config.get('min_confidence', 0.5):
            # Store valid detection
            all_detections[phase_enum] = {
                'text': detected_text,
                'confidence': confidence
            }
            # logger.debug(f"Matches {phase_enum.name}: '{detected_text}' ({confidence:.2f})")
    
    # Determine Primary Phase
    primary_phase = None
    primary_conf = 0.0
    
    for priority, phase_enum, _ in phases_with_priority:
        if phase_enum in all_detections:
            if phase_enum in [Phase.BETTING, Phase.LOCKED, Phase.RESULT]:
                primary_phase = phase_enum
                primary_conf = all_detections[phase_enum]['confidence']
                break
    
    return primary_phase, primary_conf, all_detections

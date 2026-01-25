import logging
import sys
from config import ROI, BASE_WIDTH, BASE_HEIGHT

def setup_logging(debug_mode=False):
    """Configure logging to console and file"""
    level = logging.DEBUG if debug_mode else logging.INFO
    
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler('ocr_errors.log')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)
    
    logger = logging.getLogger('StreamStakeOCR')
    logger.setLevel(level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def get_scale_factor(current_res_str: str) -> float:
    """
    Get scale factor based on resolution string 'WxH'.
    Base is 1920x1080 (1.0).
    """
    try:
        width, height = map(int, current_res_str.lower().split('x'))
        # Calculate scale based on width ratio
        scale = width / BASE_WIDTH
        return scale
    except ValueError:
        return 1.0

def scale_roi(base_roi: ROI, scale_factor: float) -> dict:
    """Scale ROI coordinates"""
    return {
        'left': int(base_roi.x * scale_factor),
        'top': int(base_roi.y * scale_factor),
        'width': int(base_roi.w * scale_factor),
        'height': int(base_roi.h * scale_factor)
    }

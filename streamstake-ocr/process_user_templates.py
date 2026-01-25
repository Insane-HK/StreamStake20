import cv2
import os
import shutil
from config import Game, Phase, GAME_CONFIGS
from utils import get_scale_factor

# Paths provided by user
# Earliest = Betting, Middle = Locked, Latest = Result
SCREENSHOTS = [
    (r"D:\Coding\Projects\SERIOUS\Ai go\Screenshot 2026-01-24 023139.png", Phase.BETTING),
    (r"D:\Coding\Projects\SERIOUS\Ai go\Screenshot 2026-01-24 023146.png", Phase.LOCKED),
    (r"D:\Coding\Projects\SERIOUS\Ai go\Screenshot 2026-01-24 023313.png", Phase.RESULT)
]

OUTPUT_DIR = "templates"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_templates():
    game_config = GAME_CONFIGS[Game.VALORANT]
    
    for path, phase in SCREENSHOTS:
        if not os.path.exists(path):
            print(f"Error: File not found {path}")
            continue
            
        img = cv2.imread(path)
        if img is None:
            print(f"Error: Could not read image {path}")
            continue
            
        h, w = img.shape[:2]
        print(f"Processing {phase.name} from {os.path.basename(path)} ({w}x{h})")
        
        # Calculate scale factor relative to 1920x1080 BASE
        # If screenshot is 720p, scale = 0.66
        scale = w / 1920.0
        
        # Get ROI
        phase_conf = game_config[phase]
        roi = phase_conf['roi']
        
        x = int(roi['x'] * scale)
        y = int(roi['y'] * scale)
        r_w = int(roi['width'] * scale)
        r_h = int(roi['height'] * scale)
        
        # Crop
        template = img[y:y+r_h, x:x+r_w]
        
        # Save
        out_path = os.path.join(OUTPUT_DIR, f"{phase.name}.png")
        cv2.imwrite(out_path, template)
        print(f"  Saved template to {out_path}")

if __name__ == "__main__":
    process_templates()

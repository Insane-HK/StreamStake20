import cv2
import os
import time
from dotenv import load_dotenv
from config import Game, Phase, GAME_CONFIGS
# Reuse stream logic from main/browser_stream
from browser_stream import BrowserStreamManager
from stream_manager import StreamManager

load_dotenv()

# Setup Dirs
CACHE_DIR = "templates"
SCORE_DIR = os.path.join(CACHE_DIR, "scores")
RESULT_DIR = os.path.join(CACHE_DIR, "results")
os.makedirs(os.path.join(SCORE_DIR, "own"), exist_ok=True)
os.makedirs(os.path.join(SCORE_DIR, "enemy"), exist_ok=True)
os.makedirs(os.path.join(RESULT_DIR, "win"), exist_ok=True)
os.makedirs(os.path.join(RESULT_DIR, "loss"), exist_ok=True)

class VideoFileStream:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
             print(f"ERROR: Could not open video file at: {path}")
             print("Please check the path and try again.")
             import sys; sys.exit(1)
        
    def read_frame(self):
        return self.cap.read()
        
    def get(self, prop):
        return self.cap.get(prop)
        
    def release(self):
        self.cap.release()

def capture_templates_live(video_path=None):
    if video_path:
        print(f"Opening Video: {video_path}")
        stream_mgr = VideoFileStream(video_path)
        
        # Get dimensions manually
        width = int(stream_mgr.get(cv2.CAP_PROP_FRAME_WIDTH))
        stream_info = {'width': width}
    else:    
        stream_url = os.getenv('STREAM_URL')
        if not stream_url:
            print("Error: STREAM_URL not set in .env")
            return

        print(f"Connecting to stream: {stream_url}")
        
        # Try Browser Backend first as it's default for live
        try:
            stream_mgr = BrowserStreamManager(stream_url)
            cap, stream_info = stream_mgr.open()
        except:
            stream_mgr = StreamManager(stream_url)
            cap, stream_info = stream_mgr.open()
        
    width = stream_info.get('width', 1920)
    scale_factor = width / 1920.0
    config = GAME_CONFIGS[Game.VALORANT]
    
    target_score_mode = "OWN" # or ENEMY
    
    print("-" * 50)
    print("CONTROLS:")
    print(" [TAB]  : Toggle between OWN and ENEMY score capture")
    print(" 0-9    : Save SCORE template for digit 0-9")
    print(" a,b,c,d: Save SCORE template for 10, 11, 12, 13")
    print(" w      : Save RESULT template -> WIN")
    print(" l      : Save RESULT template -> LOSS")
    print(" q      : Quit")
    print("-" * 50)

    while True:
        ret, frame = stream_mgr.read_frame()
        if not ret or frame is None:
            time.sleep(0.1)
            continue
            
        display = frame.copy()
        
        # Draw ROIs
        # 1. Standard Phases
        for phase, p_conf in config.items():
            roi = p_conf['roi']
            x = int(roi['x'] * scale_factor)
            y = int(roi['y'] * scale_factor)
            w = int(roi['width'] * scale_factor)
            h = int(roi['height'] * scale_factor)
            
            color = (0, 255, 0)
            
            # Highlight active score target
            if phase == Phase.OWN_SCORE and target_score_mode == "OWN":
                color = (0, 255, 255) # Yellow
                cv2.putText(display, "TARGET: OWN", (x, y-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            elif phase == Phase.ENEMY_SCORE and target_score_mode == "ENEMY":
                color = (0, 0, 255) # Red
                cv2.putText(display, "TARGET: ENEMY", (x, y-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            elif phase == Phase.RESULT:
                cv2.putText(display, "RESULT (w/l)", (x, y-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                color = (255, 0, 255)
                
            cv2.rectangle(display, (x, y), (x+w, y+h), color, 1)
            if phase not in [Phase.OWN_SCORE, Phase.ENEMY_SCORE, Phase.RESULT]:
                cv2.putText(display, phase.name, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Scale down for viewing if 1080p
        view = cv2.resize(display, (1280, 720))
        cv2.imshow("StreamStake Template Capture", view)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
            
        elif key == 9: # Tab
            target_score_mode = "ENEMY" if target_score_mode == "OWN" else "OWN"
            print(f"Switched target to: {target_score_mode}")
            
        elif key in [ord(c) for c in "0123456789abcd"]:
            # Capture Score
            if key >= ord('0') and key <= ord('9'):
                val = chr(key)
            else:
                mapping = {'a': '10', 'b': '11', 'c': '12', 'd': '13'}
                val = mapping[chr(key)]
                
            phase_enum = Phase.OWN_SCORE if target_score_mode == "OWN" else Phase.ENEMY_SCORE
            folder = "own" if target_score_mode == "OWN" else "enemy"
            
            roi = config[phase_enum]['roi']
            x = int(roi['x'] * scale_factor)
            y = int(roi['y'] * scale_factor)
            w = int(roi['width'] * scale_factor)
            h = int(roi['height'] * scale_factor)
            
            # Save raw crop
            crop = frame[y:y+h, x:x+w]
            filename = f"{SCORE_DIR}/{folder}/{val}.png"
            cv2.imwrite(filename, crop)
            print(f"Saved {target_score_mode} score {val} to {filename}")
            
            # visual feedback
            cv2.rectangle(display, (x, y), (x+w, y+h), (255, 255, 255), 3)
            cv2.imshow("StreamStake Template Capture", cv2.resize(display, (1280, 720)))
            cv2.waitKey(200)

        elif key in [ord('w'), ord('l')]:
             # Capture Result Template
             result_type = "win" if key == ord('w') else "loss"
             phase_enum = Phase.RESULT
             
             roi = config[phase_enum]['roi']
             x = int(roi['x'] * scale_factor)
             y = int(roi['y'] * scale_factor)
             w = int(roi['width'] * scale_factor)
             h = int(roi['height'] * scale_factor)
             
             crop = frame[y:y+h, x:x+w]
             timestamp = int(time.time())
             filename = f"{RESULT_DIR}/{result_type}/{timestamp}.png"
             cv2.imwrite(filename, crop)
             print(f"Saved RESULT template ({result_type.upper()}) to {filename}")
             
             cv2.rectangle(display, (x, y), (x+w, y+h), (0, 0, 255), 3)
             cv2.imshow("StreamStake Template Capture", cv2.resize(display, (1280, 720)))
             cv2.waitKey(200)

    if hasattr(stream_mgr, 'release'):
        stream_mgr.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('video_path', nargs='?', help='Path to video file (optional)')
    args = parser.parse_args()
    
    capture_templates_live(args.video_path)

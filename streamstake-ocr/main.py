import time
import os
import logging
import mss
import numpy as np
import cv2
from dotenv import load_dotenv

# Load env variables locally immediately, before importing other modules that might use them
load_dotenv()

from config import Game, Phase, GAME_CONFIGS
from utils import setup_logging, get_scale_factor
from firebase_client import FirebaseClient
from ocr_detector import analyze_frame
from stream_manager import StreamManager
from browser_stream import BrowserStreamManager
from game_state import GameState

def main():
    # Setup
    # FORCE DEBUG MODE for diagnostics
    debug_mode = True # os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    logger = setup_logging(debug_mode)
    logger.info(f"DEBUG MODE FORCED: {debug_mode}")
    
    target_game_str = os.getenv('TARGET_GAME', 'valorant').lower()
    try:
        current_game = Game(target_game_str)
    except ValueError:
        logger.error(f"Invalid game specified: {target_game_str}. Supported: {[g.value for g in Game]}")
        return

    # Use STREAM_RESOLUTION for scale factor (default 1080p)
    resolution_str = os.getenv('STREAM_RESOLUTION', '1920x1080')
    scale_factor = get_scale_factor(resolution_str)
    
    # Init FPS
    capture_fps = int(os.getenv('CAPTURE_FPS', '2'))
    frame_interval = 1.0 / capture_fps
    
    # --- ARGUMENT PARSING ---
    # Moved up to allow Lobby ID to configure FirebaseClient
    import argparse
    parser = argparse.ArgumentParser(description='StreamStake OCR')
    parser.add_argument('--live', action='store_true', help='Force Live Stream Mode')
    parser.add_argument('--video', action='store_true', help='Force Video File Mode')
    parser.add_argument('--screen', action='store_true', help='Force Screen Capture Mode')
    parser.add_argument('--lobby', type=str, help='Attach to specific Lobby ID')
    args = parser.parse_args()

    # Initialize Firebase (Scoped if Lobby ID provided)
    fb_client = FirebaseClient(lobby_id=args.lobby)
    
    # State tracking
    round_id = f"round_{int(time.time())}" 
    
    # Broadcast active round
    fb_client.set_active_round_id(round_id)

    # Determine Mode
    mode = None
    
    # LOBBY OVERRIDE
    if args.lobby:
        logger.info(f"Attaching to Lobby: {args.lobby}")
        # Fetch Stream URL from Lobby
        lobby_url = fb_client.get_lobby_stream_url()
        
        if lobby_url:
            logger.info(f"Fetched Stream URL from Lobby: {lobby_url}")
            
            # --- SPECIAL OVERRIDE FOR LOCAL DEV ---
            target_override_url = "https://www.youtube.com/watch?v=2LnFuREmbpk"
            local_override_path = r"D:\Coding\Projects\SERIOUS\JODTOD\videoplayback (2).mp4"

            # Check for override
            if lobby_url.strip() == target_override_url and os.path.exists(local_override_path):
                logger.warning(f"SPECIAL OVERRIDE: Detected target URL. Switching to LOCAL VIDEO FILE: {local_override_path}")
                mode = 'video'
                os.environ['VIDEO_PATH'] = local_override_path
                # We still want the frontend to see the URL, so we don't change what's in Firebase.
            else:
                os.environ['STREAM_URL'] = lobby_url
                mode = 'live' # Force live mode for normal URLs
        else:
            logger.warning("Lobby has no stream URL set! Falling back to env URL if available.")
    
    if not mode:
        if args.live: mode = 'live'
        elif args.video: mode = 'video'
        elif args.screen: mode = 'screen'
        else:
            # Fallback to .env priority: Live -> Video -> Screen
            if os.getenv('STREAM_URL') and not os.getenv('VIDEO_PATH'): 
                mode = 'live'
            elif os.getenv('VIDEO_PATH'): 
                mode = 'video'
            elif os.getenv('STREAM_URL'): 
                mode = 'live'
            else: mode = 'screen'

    # --- Video Sync Logic (Split Source) ---
    public_stream_url = ""
    # If in Lobby mode, we don't need to push URL likely, but let's do it to keep sync 
    # if we are source of truth. Actually, Lobby host SETS the URL. 
    # Validating we are broadcasting correctly.
    
    if mode == 'video':
        # Scenario A: Local Processing, Public VOD
        public_stream_url = os.getenv('PUBLIC_STREAM_URL', 'https://youtu.be/2LnFuREmbpk?si=L0oK6upXZI4FsLBp')
    elif mode == 'live':
        # Scenario B: Live Stream Processing, Same URL
        public_stream_url = os.getenv('STREAM_URL', '')
    
    if public_stream_url:
        fb_client.set_active_stream(public_stream_url)
    
    logger.info(f"Selected Mode: {mode.upper()}")

    if mode == 'live':
        stream_url = os.getenv('STREAM_URL')
        if not stream_url:
            logger.error("STREAM_URL not set in .env")
            return
        quality = os.getenv('STREAM_QUALITY', '1080p')
        run_live_mode(stream_url, current_game, quality, fb_client, round_id)
        
    elif mode == 'video':
        video_path = os.getenv('VIDEO_PATH')
        if not video_path:
            logger.error("VIDEO_PATH not set in .env")
            return
        run_video_mode(video_path, current_game, scale_factor, frame_interval, fb_client, round_id)
        
    elif mode == 'screen':
        run_screen_mode(current_game, scale_factor, frame_interval, fb_client, round_id)

def run_live_mode(stream_url: str, game, quality: str, fb_client, round_id: str):
    """
    Live stream detection mode
    """
    logger = logging.getLogger('StreamStakeOCR')
    logger.info(f"[LIVE MODE] Starting stream detection")
    logger.info(f"Stream: {stream_url}")
    logger.info(f"Game: {game.value} | Quality: {quality}")
    
    # Initialize stream manager
    try:
        backend = os.getenv('STREAM_BACKEND', 'ffmpeg').lower()
        if backend == 'browser':
            logger.info("Using Browser Backend (Playwright)")
            stream_mgr = BrowserStreamManager(stream_url)
        else:
            stream_mgr = StreamManager(stream_url, quality=quality)
            
        cap, stream_info = stream_mgr.open()
    except Exception as e:
        logger.error(f"Failed to start stream: {e}")
        return
    
    # Calculate scale factor
    width = stream_info.get('width', 1920)
    height = stream_info.get('height', 1080)
    BASE_WIDTH = 1920
    scale_factor = width / BASE_WIDTH
    
    logger.info(f"Resolution: {width}x{height} | Scale: {scale_factor:.3f}")
    
    # Live stream: 2Hz
    capture_fps = 2.0
    frame_interval = 1.0 / capture_fps
    
    monitor = {}
    process_loop(stream_mgr, monitor, game, scale_factor, frame_interval, fb_client, round_id, is_video=False, is_stream=True)
    if hasattr(stream_mgr, 'release'):
        stream_mgr.release()

def run_video_mode(video_path, game, scale_factor, frame_interval, fb_client, round_id):
    logger = logging.getLogger('StreamStakeOCR')
    logger.info(f"Starting StreamStakeOCR in VIDEO MODE")
    logger.info(f"Target Game: {game.value} | Source: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Could not open video file: {video_path}")
        return
        
    vid_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    BASE_WIDTH = 1920
    
    if vid_width > 0:
        video_scale_factor = vid_width / BASE_WIDTH
        logger.info(f"Video Resolution: {vid_width}x{vid_height} | Scale Factor: {video_scale_factor:.2f}")
    else:
        video_scale_factor = scale_factor
        logger.warning(f"Could not determine video resolution, using default scale: {video_scale_factor}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0: video_fps = 30
    
    target_fps = 1.0 / frame_interval
    skip_frames = int(video_fps / target_fps) - 1
    if skip_frames < 0: skip_frames = 0
    
    logger.info(f"Video FPS: {video_fps:.2f} | Target FPS: {target_fps:.2f} | Skip Frames: {skip_frames}")
    
    monitor = {}
    process_loop(cap, monitor, game, video_scale_factor, frame_interval, fb_client, round_id, is_video=True, skip_frames=skip_frames)
    cap.release()

def run_screen_mode(game, scale_factor, frame_interval, fb_client, round_id):
    logger = logging.getLogger('StreamStakeOCR')
    logger.info(f"Starting StreamStakeOCR in SCREEN MODE")
    logger.info(f"Target Game: {game.value} | Scale: {scale_factor:.2f}")
    
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        process_loop(sct, monitor, game, scale_factor, frame_interval, fb_client, round_id, is_video=False)

def process_loop(source, monitor, game, scale_factor, frame_interval, fb_client, round_id, is_video=False, skip_frames=0, is_stream=False):
    """
    Common processing loop for both video, screen capture, and live streams.
    source: cv2.VideoCapture if is_video else mss instance else StreamManager
    """
    logger = logging.getLogger('StreamStakeOCR')
    current_phase = None
    phase_start_time = 0 
    last_heartbeat = time.time()
    consecutive_errors = 0
    
    # State for Score Comparison Logic
    game_state = GameState()
    score_buffer = {
        'own': -1, 'enemy': -1,
        'last_seen_own': 0, 'last_seen_enemy': 0
    }
    
    # Track last pushed state to prevent spamming Firebase
    last_pushed_scores = {'own': -1, 'enemy': -1}
    last_pushed_phase = None
    
    while True:
        loop_start = time.time()
        
        if is_stream:
            # StreamManager.read_frame returns (ret, frame)
            # It handles auto-reconnect internally
            ret, frame_bgr = source.read_frame()
            if not ret or frame_bgr is None:
                # Waiting for reconnect or stream packet
                time.sleep(0.1)
                continue
        elif is_video:
            if not source.isOpened(): break
            
            # Skip frames to maintain speed
            if skip_frames > 0:
                for _ in range(skip_frames):
                    source.grab()
            
            ret, frame_bgr = source.read()
            if not ret:
                logger.info("End of video stream")
                break
        else:
            try:
                screenshot = source.grab(monitor)
                frame = np.array(screenshot)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            except Exception as e:
                logger.error(f"Screen capture error: {e}")
                break

        try:
            # Draw debug visualization
            debug_frame = frame_bgr.copy()
            
            # Detect Phase
            try:
                detected_phase, confidence, all_detections = analyze_frame(monitor, frame_bgr, game, scale_factor)
                consecutive_errors = 0 
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors >= 10: break
                detected_phase, confidence, all_detections = None, 0.0, {}
            
            # Helper to get numeric scores safely
            def get_scores_from_detection(dets):
                o, e = -1, -1
                if Phase.OWN_SCORE in dets:
                    try: o = int(dets[Phase.OWN_SCORE]['text'])
                    except: pass
                if Phase.ENEMY_SCORE in dets:
                    try: e = int(dets[Phase.ENEMY_SCORE]['text'])
                    except: pass
                return o, e

            raw_own, raw_enemy = get_scores_from_detection(all_detections)
            
            # --- SCORE BUFFERING ---
            current_time = time.time()
            
            # Update Buffer if valid
            if raw_own >= 0:
                score_buffer['own'] = raw_own
                score_buffer['last_seen_own'] = current_time
            if raw_enemy >= 0:
                score_buffer['enemy'] = raw_enemy
                score_buffer['last_seen_enemy'] = current_time
                
            # Retrieve from buffer if fresh (< 3.0s)
            curr_own = score_buffer['own'] if (current_time - score_buffer['last_seen_own'] < 3.0) else -1
            curr_enemy = score_buffer['enemy'] if (current_time - score_buffer['last_seen_enemy'] < 3.0) else -1

            # Draw ROIs (Debug Mode)
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                game_config = GAME_CONFIGS.get(game)
                if game_config:
                    for phase, phase_config in game_config.items():
                        roi = phase_config['roi']
                        x = int(roi['x'] * scale_factor)
                        y = int(roi['y'] * scale_factor)
                        w = int(roi['width'] * scale_factor)
                        h = int(roi['height'] * scale_factor)
                        
                        if phase == detected_phase: color = (0, 255, 0)
                        elif phase in all_detections: color = (0, 255, 255)
                        elif phase == Phase.BETTING or phase == Phase.LOCKED: color = (200, 200, 200)
                        else: color = (100, 100, 100)
                            
                        cv2.rectangle(debug_frame, (x, y), (x+w, y+h), color, 2)
                        
                        label = f"{phase.name}"
                        if phase in all_detections:
                            info = all_detections[phase]
                            label += f": {info['text'][:10]}"
                        
                        # Show buffered score override in debug
                        if phase == Phase.OWN_SCORE and curr_own != -1:
                             label += f" [{curr_own}]"
                        if phase == Phase.ENEMY_SCORE and curr_enemy != -1:
                             label += f" [{curr_enemy}]"
                        
                        label_y = y + h + 20 if phase == Phase.RESULT else y - 5
                        cv2.putText(debug_frame, label, (x, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                if is_stream:
                     cv2.putText(debug_frame, "LIVE MODE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                view_h, view_w = debug_frame.shape[:2]
                if view_h > 800:
                    scale_view = 800 / view_h
                    debug_frame = cv2.resize(debug_frame, None, fx=scale_view, fy=scale_view)
                
                cv2.imshow('StreamStake Debug', debug_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # --- Phase Logic with Constraints & Score Tracking ---
            if detected_phase:
                if detected_phase != current_phase:
                    
                    can_switch = True
                    time_in_phase = time.time() - phase_start_time
                    
                    # SIMPLIFIED RULES:
                    # 1. Betting: Lock for 5s to avoid flicker (reduced from 15s)
                    if current_phase == Phase.BETTING and time_in_phase < 5.0:
                        can_switch = False
                    
                    # 2. Locked: Lock for 10s minimum, unless RESULT appears
                    elif current_phase == Phase.LOCKED:
                        if detected_phase == Phase.RESULT:
                            pass # Always allow switch to Result
                        elif time_in_phase < 10.0:
                            can_switch = False # Ignore flickering back to Betting immediately
                    
                    if can_switch:
                        logger.info(f"Phase transition: {current_phase} -> {detected_phase} ({confidence:.2f})")
                        
                        # CAPTURE START SCORES on entering LOCKED or BETTING (Reset)
                        if detected_phase in [Phase.LOCKED, Phase.BETTING]:
                            if curr_own >= 0 and curr_enemy >= 0:
                                game_state.start_round(round_id, curr_own, curr_enemy)
                        
                        previous_phase = current_phase
                        current_phase = detected_phase
                        phase_start_time = time.time()
                        
                        # --- REDUCED STREAM PAYLOAD ---
                        latest_state = {
                            "round_id": round_id,
                            "phase": detected_phase.name, # "WAITING", "BETTING", etc.
                            "scores": {"own": curr_own, "enemy": curr_enemy},
                            "result": None,
                            "winner": None,
                            "timestamp": int(time.time() * 1000)
                        }

                        # --- RESULT LOGIC ---
                        if detected_phase == Phase.RESULT:
                            # Use GameState to calculate WIN/LOSS and get SIGNAL
                            result_text = ""
                            if Phase.RESULT in all_detections:
                                result_text = all_detections[Phase.RESULT]['text'].upper()
                            
                            # Calculate Result
                            outcome = game_state.end_round_and_get_signal(curr_own, curr_enemy, result_text)
                            
                            winner = outcome['signal'] # WIN / LOSS / UNKNOWN
                            method = outcome['method']
                            
                            # Add to payload
                            latest_state["result"] = result_text # "VICTORY", "DEFEAT" etc.
                            latest_state["winner"] = winner
                            latest_state["determination_method"] = method
                            
                            logger.info(f"🏆 Round Signal: {winner} | Method: {method}")
                            
                            # Broadcast to Chat
                            team_winner = None
                            role_winner = ""
                            if winner == "WIN": 
                                team_winner = "BLUE"
                                role_winner = "STREAMER"
                            elif winner == "LOSS": 
                                team_winner = "RED"
                                role_winner = "OPPONENT"

                            if team_winner:
                                win_msg = f"🏆 {role_winner} ({team_winner}) WINS THE ROUND! [{method}]"
                                fb_client.send_chat_message(win_msg)
                        
                        logger.info(f"Broadcast: {latest_state['phase']} | Score: {latest_state['scores']['own']}-{latest_state['scores']['enemy']}")
                        fb_client.push_round_update(round_id, latest_state)
                        
                        # Update trackers
                        last_pushed_phase = detected_phase
                        last_pushed_scores = {'own': curr_own, 'enemy': curr_enemy}
            else:
                # No phase detected - Check for implied transitions
                time_in_phase = time.time() - phase_start_time
                if current_phase == Phase.BETTING and time_in_phase >= 15.0:
                    logger.info("Auto-transition: BETTING ended -> Assuming LOCKED")
                    current_phase = Phase.LOCKED
                    phase_start_time = time.time()
                    
                    # Capture scores if visible
                    if curr_own >= 0 and curr_enemy >= 0:
                        game_state.start_round(round_id, curr_own, curr_enemy)

                    latest_state = {
                        "round_id": round_id,
                        "phase": "LOCKED",
                        "scores": {"own": curr_own, "enemy": curr_enemy},
                        "result": None,
                        "winner": None,
                        "timestamp": int(time.time() * 1000)
                    }
                    fb_client.push_round_update(round_id, latest_state)
                    last_pushed_phase = Phase.LOCKED
                    if curr_own >= 0: last_pushed_scores['own'] = curr_own
                    if curr_enemy >= 0: last_pushed_scores['enemy'] = curr_enemy
                    
                    logger.info(f"Broadcast: LOCKED | Score: {curr_own}-{curr_enemy}")
            
            # Periodic Heartbeat & Score Update (Faster: Every 1.0s)
            current_time = time.time()
            if current_time - last_heartbeat > 1.0:
                score_str = f"Score: {curr_own}-{curr_enemy}" if (curr_own>=0 and curr_enemy>=0) else "Score: --"
                phase_name = f"Phase.{current_phase.name}" if current_phase else "Scanning"
                logger.info(f"Heartbeat: {phase_name} | {score_str}")
                
                # Push Live Score Update if we have valid scores AND they have changed
                if curr_own >= 0 and curr_enemy >= 0 and current_phase == Phase.LOCKED:
                     if (curr_own != last_pushed_scores['own']) or (curr_enemy != last_pushed_scores['enemy']):
                        # SCORE CHANGED -> PUSH
                        fb_client.push_round_update(round_id, {
                            "phase": "SCORE_UPDATE",
                            "scores": {"own": curr_own, "enemy": curr_enemy}, # Ensure consistent nested format
                            "timestamp": int(current_time * 1000),
                            "status": "active"
                        })
                        logger.info(f"Broadcast: SCORE UPDATE | {curr_own}-{curr_enemy}")
                        last_pushed_scores = {'own': curr_own, 'enemy': curr_enemy}
                    
                last_heartbeat = current_time
        
        except Exception as e:
            logger.error(f"Error in process loop: {e}")
            
        elapsed = time.time() - loop_start
        sleep_time = max(0, frame_interval - elapsed)
        time.sleep(sleep_time)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

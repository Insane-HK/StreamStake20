import firebase_admin
from firebase_admin import credentials, db
import os
import time
import subprocess
import sys
import logging
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MANAGER] - %(message)s')
logger = logging.getLogger('LobbyManager')

load_dotenv()

# Track active processes: { 'lobby_id': subprocess.Popen }
active_lobbies = {}

# SCRIPT START TIME (Epoch MS)
SCRIPT_START_TIME = int(time.time() * 1000)

def initialize_firebase():
    try:
        cred_dict = {
            "type": "service_account",
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": "some_id",
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        
        if not all([cred_dict["project_id"], cred_dict["private_key"], cred_dict["client_email"]]):
            logger.error("Missing Firebase Credentials in .env")
            return None

        cred = credentials.Certificate(cred_dict)
        app = firebase_admin.initialize_app(cred, {
            'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
        })
        logger.info("Firebase Manager Initialized")
        return app
    except Exception as e:
        logger.error(f"Failed to init Firebase: {e}")
        return None

def spawn_backend(lobby_id):
    if lobby_id in active_lobbies:
        # Check if still running
        if active_lobbies[lobby_id].poll() is None:
            logger.info(f"Backend already running for {lobby_id}")
            return
    
    logger.info(f"Invoking Backend for Lobby: {lobby_id}")
    
    # Spawn process
    # Uses the same python interpreter as this script
    cmd = [sys.executable, "main.py", "--lobby", lobby_id]
    
    try:
        # Popen allows it to run in background
        # We redirect stdout/stderr or let it flow to main console?
        # Let's let it flow to main console for now so user sees output, 
        # but prefixing might be hard.
        # Ideally we'd log to separate files, but for 'dev' sharing console is okay-ish 
        # provided not too many lobbies.
        proc = subprocess.Popen(cmd) 
        active_lobbies[lobby_id] = proc
        logger.info(f"Started PID {proc.pid} for {lobby_id}")
    except Exception as e:
        logger.error(f"Failed to spawn backend: {e}")

def monitor_lobbies():
    ref = db.reference('lobbies')
    
    logger.info("Listening for new lobbies...")
    
    # 1. Initial Listen (Get existing open lobbies??)
    # For simplicity, let's just listen for ANY update or child_added.
    # But usually we only want 'active' lobbies.
    # Let's just listen for child_added.
    
    def listener(event):
        # Python Admin SDK 'listen' sends 'put' or 'patch' events
        # event.path is relative to the reference.
        # event.data is the data at that path.
        
        if event.event_type == 'put':
            path = event.path
            data = event.data
            
            if path == '/':
                # Initial load or full replace of /lobbies
                if data and isinstance(data, dict):
                    logger.info(f"Loaded {len(data)} existing lobbies. Checking timestamps...")
                    for lid, lobby_data in data.items():
                        created_at = lobby_data.get('createdAt', 0)
                        if created_at > SCRIPT_START_TIME:
                            logger.info(f"Accepted NEW lobby: {lid}")
                            spawn_backend(lid)
                        else:
                            logger.debug(f"Ignored OLD lobby: {lid}")

            else:
                # Specific update: /LOBBY_ID or /LOBBY_ID/property
                # Extract LOBBY_ID
                parts = path.strip('/').split('/')
                if parts:
                    lobby_id = parts[0]
                    
                    # If this is a direct update to /LOBBY_ID, data is the dictionary
                    if len(parts) == 1:
                        if data and isinstance(data, dict):
                             created_at = data.get('createdAt', 0)
                             if created_at > SCRIPT_START_TIME:
                                spawn_backend(lobby_id)
                             else:
                                logger.debug(f"Ignored update for OLD lobby: {lobby_id}")
                    else:
                        # Update to property (e.g. /ABCD/chat), we assume if it's chatting it exists
                        # But we should only start if we determined it's new.
                        # This is tricky without fetching full data. 
                        # Simplification: Only spawn on Direct Lobby Creation or explicitly known events.
                        # Actually, if we stick to the initial load filter, and then only handle new /LOBBY_ID puts, we catch creation.
                        pass
        
    # Listen
    ref.listen(listener)
    
    # Keep main thread alive and monitor processes
    try:
        while True:
            time.sleep(5)
            # Cleanup dead processes
            dead_ids = []
            for lid, proc in active_lobbies.items():
                if proc.poll() is not None:
                    logger.info(f"Backend for {lid} exited with code {proc.returncode}")
                    dead_ids.append(lid)
            
            for lid in dead_ids:
                del active_lobbies[lid]
                
    except KeyboardInterrupt:
        logger.info("Shutting down manager...")
        for lid, proc in active_lobbies.items():
            proc.terminate()
        logger.info("All backends terminated.")

if __name__ == "__main__":
    app = initialize_firebase()
    if app:
        monitor_lobbies()

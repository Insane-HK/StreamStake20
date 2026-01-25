import firebase_admin
from firebase_admin import credentials, db
import os
import time
import logging

logger = logging.getLogger('StreamStakeOCR')

class FirebaseClient:
    def __init__(self, lobby_id=None):
        self.app = None
        self.rounds_ref = None
        self.lobby_id = lobby_id
        # Determine Base Path
        if self.lobby_id:
            self.base_path = f"lobbies/{self.lobby_id}"
        else:
            self.base_path = "streamstake" # Legacy/Global Fallback
            
        self._initialize()

    def _initialize(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if using service account file or individual env vars
            # For this simplified setup, we'll construct a dict from env vars
            # In production, a json file path is often used.
            
            cred_dict = {
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": "some_id", # Optional for some setups or if full JSON provided
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "token_uri": "https://oauth2.googleapis.com/token",
            }

            # Basic validation
            if not all([cred_dict["project_id"], cred_dict["private_key"], cred_dict["client_email"]]):
                logger.warning("Firebase credentials incomplete. Running in offline/mock mode.")
                return

            try:
                cred = credentials.Certificate(cred_dict)
                self.app = firebase_admin.initialize_app(cred, {
                    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
                })
                # Initialize generic rounds ref based on base path
                self.rounds_ref = db.reference(f'{self.base_path}/rounds')
                logger.info(f"Firebase initialized successfully. Scoped to: {self.base_path}")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase credentials: {e}. Running in offline/mock mode.")
                self.app = None
                self.rounds_ref = None

        except Exception as e:
            logger.error(f"Unexpected error initializing Firebase: {e}")
            self.app = None

    def push_round_update(self, round_id: str, data: dict, max_retries=3):
        """Push round update to Firebase with retries"""
        if not self.rounds_ref:
            logger.error("Firebase not initialized, cannot push update")
            return False

        attempt = 0
        while attempt < max_retries:
            try:
                self.rounds_ref.child(round_id).update(data)
                logger.debug(f"Firebase updated: {round_id}")
                return True
            except Exception as e:
                attempt += 1
                wait_time = 0.5 * (2 ** attempt) # Exponential backoff
                logger.warning(f"Firebase update failed (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        
        logger.error(f"Failed to update Firebase after {max_retries} attempts.")
        return False

    def send_chat_message(self, message: str, user: str = "SYSTEM"):
        """
        Send a message to the public chat room.
        """
        if not self.app:
            logger.warning("Firebase not initialized, cannot send chat")
            return

        try:
            # Pushing to /chat/messages list (Scoped)
            chat_ref = db.reference(f'{self.base_path}/chat') 
            # Note: Room.jsx listens to 'chat', but 'chat/messages' was old structure.
            # In update 220, Room.jsx listens to `lobbies/{id}/chat`. 
            # So here we append to that list. 
            # Actually, `push()` creates a list-like key.
            new_msg_ref = chat_ref.push()
            new_msg_ref.set({
                'user': user,
                'text': message,
                'timestamp': {'.sv': 'timestamp'} # Server timestamp
            })
            logger.info(f"[CHAT] Sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send chat: {e}")

    def set_active_round_id(self, round_id: str):
        """
        Sets the global active round ID so clients know which round to listen to.
        """
        if not self.app:
            return
            
        try:
            ref = db.reference(f'{self.base_path}/active_round')
            ref.set(round_id)
            logger.info(f"Active round ID set to: {round_id} at {self.base_path}/active_round")
        except Exception as e:
            logger.error(f"Failed to set active round ID: {e}")

    def set_active_stream(self, url: str):
        """
        Sets the global active stream URL.
        """
        if not self.app:
            return
            
        try:
            # Home.jsx sets 'streamUrl', Room.jsx reads 'streamUrl'. 
            # In global mode it was 'streamstake/active_stream'.
            # To align, let's use 'streamUrl' for Lobby mode.
            
            target_path = f'{self.base_path}/streamUrl' if self.lobby_id else 'streamstake/active_stream/url'
            # Wait, for consistency let's stick to simple key for lobby
            
            ref = db.reference(target_path)
            ref.set(url) # Direct string for lobby, object for global (based on legacy) - fixing to direct check
            # Actually, let's just force the Lobby structure to be simple.
            
            logger.info(f"Active stream URL set to: {url}")
        except Exception as e:
            logger.error(f"Failed to set active stream URL: {e}")
    
    def get_lobby_stream_url(self):
        """Fetches the stream URL from the Lobby metadata"""
        if not self.app or not self.lobby_id:
            return None
        try:
            val = db.reference(f'{self.base_path}/streamUrl').get()
            return val
        except Exception as e:
            logger.error(f"Failed to fetch lobby stream URL: {e}")
            return None

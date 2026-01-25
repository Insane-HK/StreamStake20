"""
API handler for receiving stream URLs from frontend
"""
import os
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger('StreamStakeOCR')

class StreamStakeAPI:
    """
    Handles API requests from frontend
    """
    
    @staticmethod
    def start_detection(stream_url: str, game: str = 'valorant', 
                       quality: str = '1080p') -> Dict[str, Any]:
        """
        Start detection on a live stream
        Called by frontend with dynamic URL
        
        Args:
            stream_url: YouTube/Twitch URL from user
            game: Target game (valorant, csgo, league)
            quality: Stream quality preference
            
        Returns:
            Status dictionary
        """
        logger.info(f"API Request: Start detection")
        logger.info(f"URL: {stream_url}")
        logger.info(f"Game: {game} | Quality: {quality}")
        
        # Validate URL
        if not stream_url or not stream_url.startswith(('http://', 'https://')):
            return {
                'success': False,
                'error': 'Invalid stream URL'
            }
        
        # Validate game
        valid_games = ['valorant', 'csgo', 'league']
        if game not in valid_games:
            return {
                'success': False,
                'error': f'Invalid game. Must be one of: {valid_games}'
            }
        
        try:
            # Update environment variables
            os.environ['STREAM_URL'] = stream_url
            os.environ['TARGET_GAME'] = game
            os.environ['STREAM_QUALITY'] = quality
            os.environ['VIDEO_PATH'] = ''  # Clear video mode
            
            # Update .env file for persistence
            update_env_file({
                'STREAM_URL': stream_url,
                'TARGET_GAME': game,
                'STREAM_QUALITY': quality,
                'VIDEO_PATH': ''
            })
            
            # Start detection process
            # In a real app, you might spawn a subprocess or thread here.
            # For this MVP, we return success and expect main.py to be run/restarted.
            
            return {
                'success': True,
                'message': 'Detection configured. Please restart main process.',
                'stream_url': stream_url,
                'game': game,
                'quality': quality
            }
            
        except Exception as e:
            logger.error(f"Failed to start detection: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def update_env_file(updates: Dict[str, str]):
    """
    Update .env file with new values
    """
    env_path = '.env'
    
    # Read existing .env
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    
    # Update values
    updated_keys = set()
    new_lines = []
    
    # Map existing keys
    key_map = {}
    for i, line in enumerate(lines):
        if '=' in line and not line.startswith('#'):
            key = line.split('=')[0].strip()
            key_map[key] = i
            
    # Copy lines
    new_lines = list(lines)
    
    for key, value in updates.items():
        if key in key_map:
            # Update existing
            idx = key_map[key]
            new_lines[idx] = f"{key}={value}\n"
        else:
            # Append new
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
            new_lines.append(f"{key}={value}\n")
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)

"""
Live stream manager using Streamlink
Handles YouTube/Twitch streams dynamically
"""
import streamlink
import cv2
import time
import logging
import subprocess
import threading
import numpy as np
import os
from typing import Optional, Tuple

logger = logging.getLogger('StreamStakeOCR')

class StreamManager:
    """
    Manages live stream connections with automatic reconnection
    """
    
    def __init__(self, stream_url: str, quality: str = '1080p'):
        """
        Initialize stream manager
        """
        self.stream_url = stream_url
        self.quality = quality
        self.cap: Optional[cv2.VideoCapture] = None
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.backend_url: Optional[str] = None
        self.consecutive_failures = 0
        self.max_failures = 20
        self.width = 1920
        self.height = 1080
        self.mode = "opencv" # or "ffmpeg_subprocess"
        
        # Load backend preference
        self.preferred_backend = os.getenv('STREAM_BACKEND', 'ffmpeg').lower()
        self.stream_headers = {}
        logger.info(f"Preferred Backend: {self.preferred_backend}")
        
    def get_stream_url(self) -> str:
        """
        Extract direct stream URL using yt-dlp (better for YouTube)
        
        Returns:
            Direct HLS/DASH stream URL
        """
        try:
            import yt_dlp
            
            logger.info(f"Resolving stream with yt-dlp: {self.stream_url}")
            
            ydl_opts = {
                'format': f'best[height<={self.height}]', # Dynamic based on init
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.stream_url, download=False)
                
                if not info:
                    raise ValueError("No stream info found")
                
                # Store headers
                self.stream_headers = info.get('http_headers', {})

                # Get the best format
                if 'url' in info:
                    stream_url = info['url']
                elif 'formats' in info:
                    # Find best video+audio format
                    formats = info['formats']
                    
                    # Prefer formats with both video and audio
                    video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                    
                    if not video_formats:
                        # Fallback to video-only
                        video_formats = [f for f in formats if f.get('vcodec') != 'none']
                    
                    if not video_formats:
                        raise ValueError("No suitable video format found")
                    
                    # Sort by height (resolution)
                    video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                    
                    # Get the URL of the best format
                    stream_url = video_formats[0]['url']
                else:
                    raise ValueError("Could not extract stream URL")
                
                logger.info(f"Title: {info.get('title', 'Unknown')}")
                logger.info(f"Resolution: {info.get('width', '?')}x{info.get('height', '?')}")
                
                return stream_url
                
        except Exception as e:
            logger.error(f"yt-dlp failed: {e}")
            logger.info("Falling back to streamlink...")
            
            # Fallback to original streamlink method
            try:
                import streamlink
                streams = streamlink.streams(self.stream_url)
                
                if not streams:
                    raise ValueError(f"No streams found")
                
                if self.quality in streams:
                    stream = streams[self.quality]
                else:
                    stream = streams['best']
                
                return stream.url
                
            except Exception as e2:
                logger.error(f"Both yt-dlp and streamlink failed: {e2}")
                raise ValueError(f"Could not resolve stream: {self.stream_url}")
    
    def open_with_ffmpeg_subprocess(self) -> Tuple[object, dict]:
        """
        Open stream using ffmpeg subprocess (most reliable for YouTube)
        """
        logger.info("Using ffmpeg subprocess method...")
        self.mode = "ffmpeg_subprocess"
        
        # Get stream URL
        if not self.backend_url:
            self.backend_url = self.get_stream_url()
        
        # Check for custom FFmpeg path
        ffmpeg_bin = os.getenv('FFMPEG_PATH', 'ffmpeg')
        
        # Format headers for FFmpeg
        # FFmpeg expects headers with -headers "Key: Value\r\nKey2: Value2"
        ffmpeg_input_args = []
        if self.stream_headers:
            header_str = ""
            for k, v in self.stream_headers.items():
                header_str += f"{k}: {v}\r\n"
            
            if header_str:
                ffmpeg_input_args.extend(['-headers', header_str])

        # FFmpeg command to convert stream to raw video
        # Added low latency flags
        ffmpeg_cmd = [
            ffmpeg_bin,
            '-y'
        ]
        
        # Add headers BEFORE input file (-i)
        ffmpeg_cmd.extend(ffmpeg_input_args)
        
        ffmpeg_cmd.extend([
            '-i', self.backend_url,
            '-f', 'image2pipe',
            '-pix_fmt', 'bgr24',
            '-vcodec', 'rawvideo',
            '-an',  # No audio
            '-'
        ])
        
        # Start ffmpeg process
        try:
            logger.info(f"Starting FFmpeg: {' '.join(ffmpeg_cmd)}")
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=None, # Allow stderr to pass through to console for debugging
                bufsize=10**8
            )
        except FileNotFoundError:
            logger.error(f"FFmpeg binary not found at '{ffmpeg_bin}'.")
            logger.error("Please install FFmpeg and add to PATH, or set FFMPEG_PATH in .env")
            logger.error("See SETUP.md for instructions.")
            raise
        
        # Read first frame to get dimensions
        self.width = 1920
        self.height = 1080
        frame_size = self.width * self.height * 3
        
        # Blocking read for first frame
        try:
            raw_frame = self.ffmpeg_process.stdout.read(frame_size)
        except Exception as e:
             logger.error(f"Error reading from FFmpeg: {e}")
             raise
        
        if len(raw_frame) != frame_size:
            logger.error(f"Read partial frame: {len(raw_frame)} bytes (Expected {frame_size})")
            raise RuntimeError("Failed to read initial frame from FFmpeg pipe (Stream might be down)")
        
        # Consume first frame
        _ = np.frombuffer(raw_frame, dtype=np.uint8).reshape((self.height, self.width, 3))
        
        logger.info("✅ FFmpeg subprocess stream ready")
        
        stream_info = {
            'width': self.width,
            'height': self.height,
            'fps': 30.0, # Assumed
            'resolution': f'{self.width}x{self.height}',
            'backend': 'ffmpeg-subprocess'
        }
        
        return None, stream_info

    def open(self) -> Tuple[cv2.VideoCapture, dict]:
        """
        Open stream - Respects STREAM_BACKEND preference
        """
        try:
            # If preference is ffmpeg, skip OpenCV attempt
            if self.preferred_backend == 'ffmpeg':
                return self.open_with_ffmpeg_subprocess()

            # Otherwise try Standard OpenCV First
            self.backend_url = self.get_stream_url()
            self.mode = "opencv"
            
            logger.info("Attempting OpenCV connection...")
            self.cap = cv2.VideoCapture(self.backend_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000) # 5s timeout
            
            if self.cap.isOpened():
                ret, _ = self.cap.read()
                if ret:
                    w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    logger.info(f"✅ Stream ready (OpenCV): {w}x{h}")
                    return self.cap, {
                        'width': w, 'height': h, 'resolution': f'{w}x{h}', 
                        'fps': self.cap.get(cv2.CAP_PROP_FPS), 'backend': 'opencv'
                    }
            
            # Fallback to FFmpeg Subprocess
            logger.warning("OpenCV open failed, falling back to FFmpeg subprocess...")
            if self.cap: self.cap.release()
            return self.open_with_ffmpeg_subprocess()
            
        except Exception as e:
            logger.error(f"Failed to open stream: {e}")
            if self.preferred_backend != 'ffmpeg': # Only try fallback if we haven't tried it yet
                try:
                    logger.info("Attempting FFmpeg fallback after error...")
                    return self.open_with_ffmpeg_subprocess()
                except Exception:
                    pass
            raise e

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from active backend"""
        if self.mode == "ffmpeg_subprocess":
            if not self.ffmpeg_process: return False, None
            
            frame_size = self.width * self.height * 3
            raw_frame = self.ffmpeg_process.stdout.read(frame_size)
            
            if len(raw_frame) != frame_size:
                return False, None
            
            frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((self.height, self.width, 3))
            return True, frame
            
        else:
            # OpenCV mode
            if not self.cap:
                return False, None
            
            ret, frame = self.cap.read()
            if not ret:
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.max_failures:
                    logger.warning("Stream lost, reconnecting...")
                    if self.reconnect():
                        self.consecutive_failures = 0
                        return self.read_frame()
                    return False, None
                return False, None
            
            self.consecutive_failures = 0
            return True, frame

    def reconnect(self, max_attempts: int = 3) -> bool:
        """
        Reconnect to stream after failure
        """
        logger.warning(f"Stream disconnected, attempting reconnection...")
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Reconnection attempt {attempt}/{max_attempts}")
                
                # Release old connection
                self.release()
                
                # Wait before retrying (exponential backoff)
                wait_time = min(2 ** attempt, 10)  # Max 10 seconds
                time.sleep(wait_time)
                
                # Try to reopen
                self.open()
                
                logger.info(f"Reconnection successful on attempt {attempt}")
                return True
                
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt} failed: {e}")
                
                if attempt == max_attempts:
                    logger.critical("All reconnection attempts failed")
                    return False
        
        return False
    
    def release(self):
        """Clean up resources"""
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process = None
        logger.info("Stream released")

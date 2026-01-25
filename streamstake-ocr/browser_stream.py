
import logging
import time
import os
import numpy as np
import cv2
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, Page, BrowserContext

logger = logging.getLogger('StreamStakeOCR')

class BrowserStreamManager:
    """
    Manages live stream capture using a headless browser (Playwright)
    to bypass anti-bot detection.
    """
    
    def __init__(self, stream_url: str, width: int = 1920, height: int = 1080):
        self.stream_url = stream_url
        self.width = width
        self.height = height
        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Optional[Page] = None
        self.is_running = False
        
    def open(self) -> Tuple[object, dict]:
        """
        Launch browser and navigate to stream.
        Returns: (None, stream_info)
        """
        logger.info(f"Opening browser stream: {self.stream_url}")
        
        try:
            self.playwright = sync_playwright().start()
            
            # Launch chromium (headless=True for background operation)
            # Using basic args to enable media and window size
            self.browser = self.playwright.chromium.launch(
                headless=True,
                # Basic stealth args
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized',
                    '--kiosk', # Forces Fullscreen (F11 style)
                    '--no-sandbox',
                    '--disable-infobars',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                ]
            )
            
            # Create context with viewport size (Ephemeral / Incognito)
            self.context = self.browser.new_context(
                viewport={'width': self.width, 'height': self.height},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-US'
            )
            
            # Load cookies if they exist
            cookie_file = os.path.join(os.getcwd(), 'cookies.json')
            if os.path.exists(cookie_file):
                try:
                    import json
                    with open(cookie_file, 'r') as f:
                        cookies = json.load(f)
                    
                    # SANITIZE COOKIES for Playwright
                    sanitized_cookies = []
                    for c in cookies:
                        # Playwright only accepts "Strict", "Lax", "None"
                        if 'sameSite' in c:
                            if c['sameSite'] not in ['Strict', 'Lax', 'None']:
                                c['sameSite'] = 'None'
                                c['secure'] = True # None requires Secure
                        
                        # Remove fields Playwright rejects
                        c.pop('hostOnly', None)
                        c.pop('session', None)
                        c.pop('storeId', None)
                        c.pop('id', None)
                        sanitized_cookies.append(c)

                    self.context.add_cookies(sanitized_cookies)
                    logger.info(f"Loaded {len(sanitized_cookies)} cookies from cookies.json")
                except Exception as e:
                    logger.warning(f"Failed to load cookies: {e}")
            else:
                logger.warning("No cookies.json found. Bot detection likely.")
            
            self.page = self.context.new_page()
            
            # Navigate
            logger.info("Navigating to URL...")
            self.page.goto(self.stream_url, timeout=60000)
            
            # Ensure video element exists or just wait a bit
            # 'networkidle' is too strict for YouTube, use 'domcontentloaded'
            self.page.wait_for_load_state('domcontentloaded', timeout=30000)
            
            # Inject CSS persistently and periodically ensure it's applied
            css = """
                /* Hide Chat */
                #chat, #chat-container, ytd-live-chat-frame { display: none !important; }
                
                /* Hide Sidebar/Recommendations */
                #secondary, #related { display: none !important; }
                
                /* Hide Comments */
                #comments { display: none !important; }
                
                /* Clean up player overlays */
                .ytp-chrome-top, .ytp-show-cards-title, .ytp-ce-element { display: none !important; }
                
                /* Force video to centered/large if not full screen (backup) */
                ytd-watch-flexy[flexy] #primary.ytd-watch-flexy { max-width: 100% !important; min-width: 100% !important; }
                
                /* ULTRA FORCE VIDEO FULLSCREEN (Fixes ROI alignment) */
                video {
                    position: fixed !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100vw !important;
                    height: 100vh !important;
                    z-index: 99999 !important;
                    object-fit: cover !important;
                }
            """
            
            # 1. Initial Injection
            logger.info("Injecting CSS to hide chat and distractions...")
            self.page.add_style_tag(content=css)
            
            # 2. Add init script to re-inject on navigation/reload
            self.page.add_init_script(f"""
                const style = document.createElement('style');
                style.innerHTML = `{css}`;
                document.head.appendChild(style);
            """)

            # Simple check for cookie banner (optional, generic Google selector)
            try:
                self.page.get_by_text("Reject all").click(timeout=2000)
                logger.info("Clicked 'Reject all' cookie button")
            except:
                pass

            # Wait for video player to initialize
            time.sleep(5)
            
            # Try to enter full screen (keyboard shortcut)
            try:
                logger.info("Toggling full screen (press 'f')...")
                self.page.keyboard.press("f")
                time.sleep(2) # Wait for animation
            except Exception as e:
                logger.warning(f"Could not toggle full screen: {e}")
            
            self.is_running = True
            logger.info("✅ Browser stream ready")
            
            stream_info = {
                'width': self.width,
                'height': self.height,
                'fps': 2.0, # Effective screenshot FPS
                'resolution': f'{self.width}x{self.height}',
                'backend': 'playwright'
            }
            
            return None, stream_info
            
        except Exception as e:
            logger.error(f"Failed to open browser stream: {e}")
            self.release()
            raise e

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Capture screenshot from browser page.
        """
        if not self.is_running or not self.page:
            return False, None
            
        try:
            # Re-inject CSS periodically? No, that's heavy.
            # But we can assume InitScript handles updates.
            
            # Capture screenshot as raw bytes
            screenshot_bytes = self.page.screenshot(type='png')
            
            # Convert to numpy array
            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return True, frame_bgr
            
        except Exception as e:
            # Suppress closed loop errors during shutdown
            if "Event loop is closed" not in str(e):
                logger.error(f"Browser capture error: {e}")
            return False, None

    def release(self):
        """Cleanup browser resources"""
        self.is_running = False
        try:
            if self.context:
                self.context.close()
                self.context = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
        except Exception as e:
            # Ignore errors during cleanup (common with asyncio/playwright interaction)
            pass
        logger.info("Browser stream released")

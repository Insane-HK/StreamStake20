"""Test Browser Stream"""
from browser_stream import BrowserStreamManager
from dotenv import load_dotenv
import logging
import time
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)

def test_browser():
    url = "https://www.youtube.com/watch?v=en-KABsEKeE"
    
    print("Testing Browser Stream...")
    print(f"URL: {url}")
    
    mgr = BrowserStreamManager(url)
    
    try:
        _, info = mgr.open()
        print(f"✅ Stream Info: {info}")
        
        for i in range(10):
            ret, frame = mgr.read_frame()
            if ret and frame is not None:
                print(f"Frame {i}: {frame.shape}")
            else:
                print(f"Frame {i}: Failed")
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        mgr.release()

if __name__ == "__main__":
    test_browser()

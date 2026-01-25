"""Test YouTube live stream opening"""
from stream_manager import StreamManager
import time
import logging

from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Setup basic logging to see the stream manager output
logging.basicConfig(level=logging.INFO)

def test_youtube():
    # Use the URL the user was testing with
    url = "https://www.youtube.com/watch?v=en-KABsEKeE"
    
    print("Testing YouTube stream...")
    print(f"URL: {url}\n")
    
    try:
        # Start with 720p to be safe/fast
        mgr = StreamManager(url, quality='720p')  
        cap, info = mgr.open()
        
        print(f"✅ SUCCESS!")
        print(f"Resolution: {info['resolution']}")
        print(f"FPS: {info['fps']}")
        print(f"Backend: {info.get('backend', 'unknown')}")
        
        # Read 5 frames
        print("Reading 5 frames...")
        for i in range(5):
            ret, frame = mgr.read_frame()
            if ret and frame is not None:
                print(f"✅ Frame {i+1}: {frame.shape}")
            else:
                print(f"❌ Frame {i+1}: FAILED")
            time.sleep(0.5)
        
        mgr.release()
        
    except Exception as e:
        print(f"❌ FAILED: {e}")

if __name__ == "__main__":
    test_youtube()

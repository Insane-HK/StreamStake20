"""
Test live stream integration
"""
from stream_manager import StreamManager
import cv2
import time
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)

def test_stream(stream_url: str):
    """Quick test of stream connection"""
    
    print(f"Testing stream: {stream_url}")
    
    try:
        # Initialize
        stream_mgr = StreamManager(stream_url, quality='720p') # Use 720p for faster test or 'worst'
        cap, info = stream_mgr.open()
        
        print(f"✅ Stream opened: {info['resolution']} @ {info['fps']} FPS")
        
        # Read 10 frames
        for i in range(10):
            ret, frame = stream_mgr.read_frame()
            if ret:
                h, w = frame.shape[:2]
                print(f"✅ Frame {i+1}: {w}x{h}")
            else:
                print(f"❌ Frame {i+1}: FAILED")
            
            time.sleep(0.5)
        
        stream_mgr.release()
        print("✅ Test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    # Test with a known live URL or ask user
    print("Paste a YouTube Live URL to test (or press Enter to skip):")
    test_url = input().strip()
    if test_url:
        test_stream(test_url)
    else:
        print("No URL provided. Skipping test.")

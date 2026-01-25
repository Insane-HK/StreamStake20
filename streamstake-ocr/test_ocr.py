import unittest
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Game, Phase, GAME_CONFIGS, ROI
from utils import get_scale_factor, scale_roi
from ocr_detector import analyze_frame

class TestStreamStakeOCR(unittest.TestCase):

    def test_scale_factor(self):
        self.assertAlmostEqual(get_scale_factor("1920x1080"), 1.0)
        self.assertAlmostEqual(get_scale_factor("1280x720"), 0.6666666666666666)
        self.assertAlmostEqual(get_scale_factor("2560x1440"), 1.3333333333333333)
        self.assertEqual(get_scale_factor("invalid"), 1.0)

    def test_roi_scaling(self):
        base_roi = ROI(100, 100, 200, 50)
        scale = 0.5
        scaled = scale_roi(base_roi, scale)
        self.assertEqual(scaled['left'], 50)
        self.assertEqual(scaled['top'], 50)
        self.assertEqual(scaled['width'], 100)
        self.assertEqual(scaled['height'], 25)

    def test_config_integrity(self):
        # Ensure all games have the 3 required phases
        for game in Game:
            config = GAME_CONFIGS[game]
            self.assertIn(Phase.BETTING, config)
            self.assertIn(Phase.LOCKED, config)
            self.assertIn(Phase.RESULT, config)

    @patch('ocr_detector.detect_text_in_roi')
    def test_analyze_frame_mock(self, mock_detect):
        # Mock OCR to return a specific keyword
        mock_detect.return_value = ("VICTORY", 0.9)
        
        # Create a dummy frame (black image)
        dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # Test detection
        # Logic: It should check ROIs. If it finds "VICTORY" in one of them, it returns Phase.RESULT
        # Note: Our mock returns "VICTORY" for ANY calls to detect_text()
        # So it might match the first one checked if keywords overlap, or the specific one.
        # But Phase.RESULT for Valorant expects "VICTORY".
        
        monitor = {} # Unused in function logic for now, just coordinates
        phase, confidence, dets = analyze_frame(monitor, dummy_frame, Game.VALORANT, 1.0)
        
        # Since loop order is RESULT, LOCKED, BETTING, it should find RESULT first if it matches
        self.assertEqual(phase, Phase.RESULT)
        self.assertGreater(confidence, 0.0)

    @patch('cv2.VideoCapture')
    @patch('main.process_loop') # Mocking the loop so we don't actually run forever
    def test_video_mode_init(self, mock_loop, mock_video_capture):
        from main import run_video_mode
        
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        # Mock get needs to return values for width, height, FPS
        # Props: WIDTH=3, HEIGHT=4, FPS=5 (cv2 constants usually)
        # We can just use side_effect or return_value if we don't care about specific prop IDs for now,
        # but main.py calls it multiple times.
        mock_cap.get.return_value = 30.0 # Return 30 for everything (width, height, fps)
        mock_video_capture.return_value = mock_cap
        
        run_video_mode("dummy.mp4", Game.VALORANT, 1.0, 0.5, MagicMock(), "round123")
        
        # Verify VideoCapture was called with path
        mock_video_capture.assert_called_with("dummy.mp4")
        # Verify loop was started
        mock_loop.assert_called_once()

    @patch('ocr_detector.TEMPLATES')
    def test_template_matching_logic(self, mock_templates):
        # Setup mock template
        # Create a small 10x10 white square as template
        template = np.ones((10, 10), dtype=np.uint8) * 255
        mock_templates.__contains__.return_value = True
        mock_templates.__getitem__.return_value = template
        
        # Create a frame that HAS the template at the expected ROI
        # ROI for Betting in Valorant is roughly x=700, y=100
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # Place the white square at 700, 100
        cv2.rectangle(frame, (700, 100), (710, 110), (255, 255, 255), -1)
        
        # We need to manually inject the template into the module's global TEMPLATES dict if we weren't mocking it so heavily
        # But analyze_frame uses the global TEMPLATES. 
        # The easiest way to test this without complex mocking of the module-level variable is to rely on detect_template_in_roi returning high confidence
        
        from ocr_detector import detect_template_in_roi
        
        # Test helper directly
        conf_roi = GAME_CONFIGS[Game.VALORANT][Phase.BETTING]
        
        # We need to mock TEMPLATES inside the function. 
        # Since we patched 'ocr_detector.TEMPLATES', it should work.
        
        # But wait, we need to ensure the ROI extracted matches the template logic.
        # The ROI defined in config is huge (520x250).
        # The template we made is 10x10.
        # detect_template_in_roi will extract the huge ROI.
        # Then matchTemplate will try to find the 10x10 inside the huge ROI.
        # This should work perfectly.
        
        name, conf = detect_template_in_roi(frame, conf_roi, 1.0, Phase.BETTING)
        
        self.assertEqual(name, "TEMPLATE_MATCH")
        self.assertGreater(conf, 0.9)


if __name__ == '__main__':
    unittest.main()

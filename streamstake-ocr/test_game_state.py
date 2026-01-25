import unittest
from game_state import GameState

class TestGameState(unittest.TestCase):
    def setUp(self):
        self.game = GameState()
        
    def test_win_by_score(self):
        # Round Start: 0-0
        self.game.start_round("r1", 0, 0)
        
        # Round End: 1-0 (We won)
        res = self.game.end_round_and_get_signal(1, 0)
        
        self.assertEqual(res['signal'], "WIN")
        self.assertEqual(res['method'], "SCORE_DELTA")
        
    def test_loss_by_score(self):
        # Round Start: 0-0
        self.game.start_round("r2", 0, 0)
        
        # Round End: 0-1 (Enemy won)
        res = self.game.end_round_and_get_signal(0, 1)
        
        self.assertEqual(res['signal'], "LOSS")
        self.assertEqual(res['method'], "SCORE_DELTA")
        
    def test_win_by_text_fallback(self):
        # Round Start: 0-0
        self.game.start_round("r3", 0, 0)
        
        # Round End: 0-0 (Score OCR failed)
        # But Banner says VICTORY
        res = self.game.end_round_and_get_signal(0, 0, "ROUND WIN VICTORY")
        
        self.assertEqual(res['signal'], "WIN")
        self.assertEqual(res['method'], "TEXT_OCR")
        
    def test_history_logging(self):
        self.game.start_round("r1", 0, 0)
        self.game.end_round_and_get_signal(1, 0)
        
        self.assertEqual(len(self.game.rounds), 1)
        self.assertEqual(self.game.rounds[0]['signal'], "WIN")


if __name__ == '__main__':
    unittest.main()

import logging
import time

logger = logging.getLogger('StreamStakeOCR')

class GameState:
    def __init__(self):
        self.rounds = [] # History of rounds: {start_scores, end_scores, winner, signal}
        self.current_round = {
            'id': None,
            'start_own': -1,
            'start_enemy': -1,
            'active': False
        }
        
    def start_round(self, round_id: str, own: int, enemy: int):
        """
        Called when transitioning into LOCKED/BETTING when scores are stable.
        """
        # Only reset if we are not already active or if it's a new round ID
        # Actually, main.py generates round_id on startup. We might want to track 'phases' instead.
        # But assuming the bot runs continuously, we treat 'start_round' as 'locking in start scores'.
        
        self.current_round['active'] = True
        self.current_round['id'] = round_id
        self.current_round['start_own'] = own
        self.current_round['start_enemy'] = enemy
        
        logger.info(f"[GAME STATE] Round Started/Updated. Start Scores -> Own: {own}, Enemy: {enemy}")

    def end_round_and_get_signal(self, current_own: int, current_enemy: int, text_result: str = "") -> dict:
        """
        Calculate winner based on score delta.
        Returns dict with 'signal' ("WIN", "LOSS", "DRAW", "UNKNOWN") and 'method'
        """
        start_o = self.current_round['start_own']
        start_e = self.current_round['start_enemy']
        
        signal = "UNKNOWN"
        method = "NONE"
        
        # 1. Check Score Delta (Primary Source of Truth)
        if start_o != -1 and start_e != -1 and current_own != -1 and current_enemy != -1:
            if current_own > start_o and current_enemy == start_e:
                signal = "WIN" # Blue Team Won
                method = "SCORE_DELTA"
            elif current_enemy > start_e and current_own == start_o:
                signal = "LOSS" # Red Team Won
                method = "SCORE_DELTA"
                
        # 2. STRICT: Only use Score Delta - User Request
        # If score delta didn't determine a winner, we return UNKNOWN.
        # We do NOT use templates or text fallbacks anymore.
        
        pass 
        # (Templates and Text logic removed to ensure "only scores" determines result)

        # Record History
        if signal != "UNKNOWN":
            outcome = {
                'timestamp': time.time(),
                'start': {'own': start_o, 'enemy': start_e},
                'end': {'own': current_own, 'enemy': current_enemy},
                'signal': signal,
                'method': method
            }
            self.rounds.append(outcome)
            
            # Log Table
            self._log_history_table()
            
        return {'signal': signal, 'method': method}

    def _log_history_table(self):
        logger.info("\n" + "="*40)
        logger.info("       MATCH SCORE HISTORY       ")
        logger.info("="*40)
        logger.info(f"{'#':<3} | {'START':<7} | {'END':<7} | {'RESULT':<6}")
        logger.info("-" * 40)
        for i, r in enumerate(self.rounds[-5:]): # Show last 5
            s = f"{r['start']['own']}-{r['start']['enemy']}"
            e = f"{r['end']['own']}-{r['end']['enemy']}"
            res = r['signal']
            logger.info(f"{i+1:<3} | {s:<7} | {e:<7} | {res:<6}")
        logger.info("="*40 + "\n")

import logging
import time

logger = logging.getLogger('StreamStakeOCR')

class GameState:
    def __init__(self):
        self.rounds = [] 
        self.current_round = {
            'id': None,
            'start_own': -1,
            'start_enemy': -1,
            'active': False
        }
        
    def start_round(self, round_id: str, own: int, enemy: int):
        self.current_round['active'] = True
        self.current_round['id'] = round_id
        self.current_round['start_own'] = own
        self.current_round['start_enemy'] = enemy
        
        logger.info(f"[GAME STATE] Round Started. Baseline Scores -> Own: {own}, Enemy: {enemy}")

    def end_round_and_get_signal(self, current_own: int, current_enemy: int, text_result: str = "") -> dict:
        """
        Determines winner using Score Delta first, then Text Fallback.
        """
        start_o = self.current_round['start_own']
        start_e = self.current_round['start_enemy']
        
        signal = "UNKNOWN"
        method = "NONE"
        
        # 1. PRIMARY CHECK: Score Delta
        # We only trust scores if they are valid integers
        if start_o != -1 and start_e != -1 and current_own != -1 and current_enemy != -1:
            if current_own > start_o:
                signal = "WIN"
                method = "SCORE_DELTA"
            elif current_enemy > start_e:
                signal = "LOSS"
                method = "SCORE_DELTA"
                
        # 2. SECONDARY CHECK: Text Fallback (If scores were too slow to update)
        if signal == "UNKNOWN" and text_result:
            clean_text = text_result.upper()
            
            # Words indicating the Streamer WON
            if any(x in clean_text for x in ["VICTORY", "WIN", "WON", "MVP", "DEFUSED"]):
                signal = "WIN"
                method = "TEXT_FALLBACK"
                
            # Words indicating the Streamer LOST
            elif any(x in clean_text for x in ["DEFEAT", "LOSS", "LOST", "ELIMINATED", "DETONATED"]):
                signal = "LOSS"
                method = "TEXT_FALLBACK"

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
            self._log_history_table()
            
        return {'signal': signal, 'method': method}

    def _log_history_table(self):
        logger.info("\n" + "="*40)
        logger.info(f"{'#':<3} | {'START':<7} | {'END':<7} | {'RESULT':<6}")
        logger.info("-" * 40)
        for i, r in enumerate(self.rounds[-5:]): 
            s = f"{r['start']['own']}-{r['start']['enemy']}"
            e = f"{r['end']['own']}-{r['end']['enemy']}"
            res = r['signal']
            logger.info(f"{i+1:<3} | {s:<7} | {e:<7} | {res:<6}")
        logger.info("="*40 + "\n")
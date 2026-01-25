from enum import Enum
from dataclasses import dataclass

class Game(Enum):
    VALORANT = "valorant"
    CS2 = "cs2"
    LEAGUE = "league"

class Phase(Enum):
    BETTING = "BETTING"
    LOCKED = "LOCKED"
    RESULT = "RESULT"
    OWN_SCORE = "OWN_SCORE"
    ENEMY_SCORE = "ENEMY_SCORE"

@dataclass
class ROI:
    x: int
    y: int
    w: int
    h: int

# Base resolution 1920x1080
BASE_WIDTH = 1920
BASE_HEIGHT = 1080

GAME_CONFIGS = {
    Game.VALORANT: {
        # BUY PHASE - Large center banner
        # BUY PHASE - Large center banner
        # WIDENED ROI for 4:3 / Misaligned resolutions
        Phase.BETTING: {
            'roi': {'x': 700, 'y': 100, 'width': 520, 'height': 250}, # Original: 800, 132, 317, 145
            'keywords': ['BUY', 'PHASE', 'BUYPHASE', 'PRESS', 'TO BUY', 'B'],
            'preprocess': 'white_text_on_dark',
            'psm': 7,
            'min_confidence': 0.4,
            'priority': 1
        },
        
        # ROUND TIMER - Top center
        Phase.LOCKED: {
            'roi': {'x': 850, 'y': 0, 'width': 220, 'height': 100}, # Original: 886, 14, 141, 47
            'keywords': [':', '1:', '0:', '2:', '1.45', '145'],
            'preprocess': 'light_text',
            'psm': 7,
            'whitelist': '0123456789:.',
            'min_confidence': 0.3,
            'priority': 3
        },
        
        # VICTORY/DEFEAT - Center banner
        Phase.RESULT: {
            'roi': {'x': 700, 'y': 100, 'width': 520, 'height': 250}, # Same broad center area as Betting
            'keywords': ['VICTORY', 'DEFEAT', 'WIN', 'LOSS', 'VICTOR', 'WON', 'FLAWLESS', 'THRIFTY', 'ACE', 'TEAM ACE', 'CLUTCH'],
            'preprocess': 'white_text_on_dark',
            'psm': 6,
            'min_confidence': 0.30,
            'priority': 0
        },
        
        # OWN SCORE - Adjusted for standard 1080p HUD
        Phase.OWN_SCORE: {
            'roi': {'x': 800, 'y': 15, 'width': 80, 'height': 60}, 
            'keywords': [], 
            'preprocess': 'light_text',
            'psm': 7, # Single line
            'whitelist': '0123456789',
            'min_confidence': 0.2,
            'priority': 4
        },
        
        # ENEMY_SCORE - Adjusted for standard 1080p HUD
        Phase.ENEMY_SCORE: {
            'roi': {'x': 1040, 'y': 15, 'width': 80, 'height': 60}, 
            'keywords': [],
            'preprocess': 'light_text',
            'psm': 7,
            'whitelist': '0123456789',
            'min_confidence': 0.2,
            'priority': 5
        }
    },
    Game.CS2: {
        Phase.BETTING: {
            "roi": ROI(50, 850, 150, 60),
            "keywords": ["BUY ZONE", "$"]
        },
        Phase.LOCKED: {
            "roi": ROI(920, 50, 80, 50),
            "keywords": ["1:", "0:"]
        },
        Phase.RESULT: {
            "roi": ROI(660, 400, 600, 200),
            "keywords": ["TERRORISTS WIN", "COUNTER-TERRORISTS WIN"]
        }
    },
    Game.LEAGUE: {
        Phase.BETTING: {
            "roi": ROI(1700, 950, 200, 80),
            "keywords": ["00:", "Minions spawn"]
        },
        Phase.LOCKED: {
            "roi": ROI(920, 10, 80, 40),
            "keywords": ["01:", "02:", "03:"]
        },
        Phase.RESULT: {
            "roi": ROI(660, 300, 600, 300),
            "keywords": ["VICTORY", "DEFEAT"]
        }
    }
}

@echo off
echo Starting StreamStake Lobby Manager...
echo This service will auto-detect new lobbies and spawn OCR backends.
call venv\Scripts\activate
python lobby_manager.py
pause

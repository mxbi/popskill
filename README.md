# popskill
Custom CS:GO 10-man skill rating system, based on [TrueSkill](https://trueskill.org/). This repo contains the backend rating, API and discord code.

**`app.py`**: The main guts - contains the rating system, as well as the REST API  
**`popflash_api.py`**: Web scraper for popflash, which provides an API for getting user info and match info  
**`popflash_match_screenshot.py`**: Selenium screenshotter for popflash match pages. Uses a supporter session ID in `sid.txt` to capture all stats  
**`discord_app.py`**: Discord bot client - pretty minimal, most things happen in `app.py`. Uses a bot token in `discord_token.txt`  
**`collect_seed_matches.py`**: This collects seed matches which are not user-submitted into `seedmatches4.pkl`.

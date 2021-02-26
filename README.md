# popskill
Custom competitive skill rating system for CS:GO, based on [TrueSkill](https://trueskill.org/), integrated with [Popflash](https://popflash.site/) games. This is used to track the skill of University of Cambridge players across internal matches, much like an ELO system.

This repo contains the backend rating, API and discord code.

**`app.py`**: The main guts - contains the rating system, as well as the REST API  
**`popflash_api.py`**: Web scraper for popflash, which provides an API for getting user info and match info  
**`popflash_match_screenshot.py`**: Selenium screenshotter for popflash match pages. Uses a supporter session ID in `sid.txt` to capture all stats  
**`discord_app.py`**: Discord bot client - pretty minimal, most things happen in `app.py`. Uses a bot token in `discord_token.txt`  
**`collect_seed_matches.py`**: This collects seed matches which are not user-submitted into `seedmatches4.pkl`.

**Front-end: https://github.com/cameron-robey/popskill-frontend**

Thanks to [@cameron-robey](https://github.com/cameron-robey), [@theo-brown](https://github.com/theo-brown) and [@speedstyle](https://github.com/speedstyle) for their help.  

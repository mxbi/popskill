# popskill
Custom competitive skill rating system for CS:GO, based on [TrueSkill](https://trueskill.org/), integrated with [Popflash](https://popflash.site/) games. This is used to track the skill of University of Cambridge players across internal matches, much like an ELO system.

This repo contains the backend rating, API and discord code.

**`app.py`**: The main guts - contains the rating system, as well as the REST API  
**`match_db.py`**: Connects to a MongoDB database storing match info. Uses `MONGO_URI` from `.env`, with database `MONGO_DB`  
**`popflash_api.py`**: Web scraper for popflash, which provides an API for getting user info and match info  
**`popflash_match_screenshot.py`**: Selenium screenshotter for popflash match pages. Use a supporter's session ID `POPFLASH_SID` in `.env` to capture all stats  
**`discord_app.py`**: Discord bot client - pretty minimal, most things happen in `app.py`. Uses `DISCORD_TOKEN` in `.env`  
**`collect_seed_matches.py`**: This collects seed matches which are not user-submitted into `seedmatches4.pkl`.

**Front-end: https://github.com/cameron-robey/popskill-frontend**  
**Live site: https://sandb.ga**

Thanks to [@cameron-robey](https://github.com/cameron-robey), [@theo-brown](https://github.com/theo-brown) and [@speedstyle](https://github.com/speedstyle) for their help.  

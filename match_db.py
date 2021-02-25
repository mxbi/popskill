import pandas as pd

from typing import Union
import popflash_api as pf
import pymongo
import datetime

class MatchDB():
    def __init__(self):

        from popflash_api import API_VERSION
        self.API_VERSION = API_VERSION
        
        # yes jamal i know this is insecure
        self.client = pymongo.MongoClient("mongodb+srv://popskill:popskill@cluster0.imry2.mongodb.net/popskill?retryWrites=true&w=majority")
        self.db = self.client.popskill
        self.matches = self.db['matches']
        self.matches.create_index("match_id", unique=True)
        self.match_cache = self.db['match_cache_v' + str(API_VERSION)]
        self.match_cache.create_index("match_id", unique=True)

    def _df_dictify(self, inp: dict):
        for k, v in inp.items():
            if isinstance(v, pd.DataFrame):
                df = "PANDAS+" + v.to_json(orient='split')
                # df['pandas'] = True
                inp[k] = df
        print(inp)
        return inp

    def _df_undictify(self, inp: dict):
        for k, v in inp.items():
            if isinstance(v, str) and v.startswith("PANDAS+"):
                inp[k] = pd.read_json(v[7:], orient='split')
        print(inp)
        return inp

    def add_match(self, match_id: Union[str, int], season: int, cache: Union[bool, dict]=True) -> Union[bool, dict]:
        # cache: False to avoid caching, True to fetch cache using Popskill API, or dict to provide 
        if isinstance(match_id, str):
            match_id = int(match_id.split('/')[-1])
        match = {"match_id": match_id, "add_time": datetime.datetime.utcnow(), 'season': season}

        try:
            res = self.matches.insert_one(match)
            assert res.acknowledged
        except pymongo.errors.DuplicateKeyError:
            raise Exception("[MatchDB] Tried adding match that already exists to DB")

        if isinstance(cache, bool) and cache:
                cache = pf.get_match(match_id)
        if isinstance(cache, dict):
            assert cache['v'] == self.API_VERSION, "[MatchDB] Tried saving cache from outdated API version"
            assert cache['match_id'] == match['match_id'], "[MatchDB] Tried saving cache from wrong game!"

        if cache:
            cache['season'] = season
            res = self.match_cache.insert_one(self._df_dictify(cache))
            assert res.acknowledged

    # Note: Match MUST be in matches
    def get_match(self, match_id: int, cache_if_missing=True):
        if isinstance(match_id, str):
            match_id = int(match_id.split('/')[-1])

        res = self.match_cache.find_one({"match_id": match_id})

        if not res:
            res = pf.get_match(match_id)
            res['season'] = self.matches.find_one({"match_id": match_id})['season']
            res = self.match_cache.insert_one(self._df_dictify(res))
            assert res.acknowledged

        return res

    def get_matches(self, season=None):
        if season:
            return list(self.matches.find({"season": season}))
        else:
            return list(self.matches.find({}))
        
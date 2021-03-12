import pandas as pd

from typing import Union
import popflash_api as pf
import pymongo
import datetime
import time

import os
import dotenv
dotenv.load_dotenv()

class MatchDBException(Exception):
    pass

class MatchAlreadyAdded(MatchDBException):
    pass

class MatchDoesNotExist(MatchDBException):
    pass

class MatchDB():
    def __init__(self, seasons, cache_get_matches=True):
        self.API_VERSION = pf.API_VERSION
        
        self.client = pymongo.MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("MONGO_DB")]
        print(f'[MatchDB] using DB {os.getenv("MONGO_DB")}')
        self.matches = self.db['matches']
        self.matches.create_index("match_id", unique=True)
        self.match_cache = self.db['match_cache_v' + str(self.API_VERSION)]
        self.match_cache.create_index("match_id", unique=True)

        self.users = self.db['user_links']

        self.seasons = seasons


    def _df_dictify(self, inp: dict):
        for k, v in inp.items():
            if isinstance(v, pd.DataFrame):
                df = "PANDAS+" + v.to_json(orient='split')
                # df['pandas'] = True
                inp[k] = df
        return inp

    def _df_undictify(self, inp: dict):
        for k, v in inp.items():
            if isinstance(v, str) and v.startswith("PANDAS+"):
                inp[k] = pd.read_json(v[7:], orient='split')
        return inp

    def _normalise_match_id(self, match_id: Union[str]) -> int:
        if isinstance(match_id, str):
            match_id = int(match_id.split('/')[-1])
        return match_id
        

    def build_cache(self):
        all_matches = list(self.matches.find({}))
        ids = [m['match_id'] for m in all_matches]
        cache_ids = [m['match_id'] for m in list(self.match_cache.find({}, projection=["match_id"]))]

        rem_ids = set(ids) - set(cache_ids)
        if len(rem_ids) > 0:
            print(f"[MatchDB] Cache v{self.API_VERSION} missing games {rem_ids}, rebuilding...")
            for match_id in rem_ids:
                self.cache_match(match_id)
        else:
            print(f'[MatchDB] Cache v{self.API_VERSION} verified, {len(ids)} matches.')

        self.matches_cache = {}

        
    def cache_match(self, match_id: Union[str, int], cache: dict=None, ignore_existing: bool=False) -> Union[bool, dict]:
        match_id = self._normalise_match_id(match_id)

        if cache is None:
            cache = pf.get_match(match_id)
        if isinstance(cache, dict):
            assert cache['v'] == self.API_VERSION, "[MatchDB] Tried saving cache from outdated API version"
            assert cache['match_id'] == match_id, "[MatchDB] Tried saving cache from wrong game!"

        try:
            res = self.match_cache.insert_one(self._df_dictify(cache))
            assert res.acknowledged
        except pymongo.errors.DuplicateKeyError:
            if not ignore_existing:
                raise MatchAlreadyAdded(str(match_id) + " in match_cache")
            print('[MatchDB][WARN] Match {} already in cache DB, ignoring'.format(match_id))

        self.matches_cache = {}

        return cache

    def add_match(self, match_id: Union[str, int], cache: dict=None, ignore_existing: bool=False) -> Union[bool, dict]:
        # cache: Can provide manually a game object, but otherwise this will be fetched
        # ignore_existing: If match is already in database, ignore it
        match_id = self._normalise_match_id(match_id)
        match = {"match_id": match_id, "add_time": datetime.datetime.utcnow()}

        try:
            res = self.matches.insert_one(match)
            assert res.acknowledged
        except pymongo.errors.DuplicateKeyError:
            if not ignore_existing:
                raise MatchAlreadyAdded(str(match_id) + " in matches")
            print('[MatchDB][WARN] Match {} already in DB, ignoring'.format(match_id))

        self.matches_cache = {}

        return self.cache_match(match_id=match_id, cache=cache, ignore_existing=ignore_existing)

    # Note: Match MUST be in matches
    def get_match(self, match_id: Union[str,int]):
        match_id = self._normalise_match_id(match_id)
        m = self.match_cache.find_one({"match_id": match_id})
        if not m:
            raise MatchDoesNotExist(match_id)
        del m['_id']
        return m

    def get_matches(self, season=None, user_id: int=None):
        query = {}

        if season is not None:
            start, end = self.seasons[season]
            query["date"] = {"$gte": start, "$lt": end}
        
        if user_id is not None:
            query["$or"] = [{f"team1table.{user_id}": {"$exists": True}}, {f"team2table.{user_id}": {"$exists": True}}]

        matches = list(self.match_cache.find(query))
        
        matches = [self._df_undictify(m) for m in sorted(matches, key=lambda x: x['date'])]

        for m in matches:
            del m['_id']
            if season is None:
                for s, (start, end) in self.seasons.items():
                    if start < m['date'].replace(tzinfo=None) < end:
                        m['season'] = s
            else:
                m['season'] = season

        # print(matches)
        return matches

    def get_optout_players(self):
        players = self.users.find({"optout": True})
        return [p['popflash_id'] for p in players]
        
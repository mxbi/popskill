import pandas as pd

from typing import Union
import popflash_api as pf
import pymongo
import datetime
import time

class MatchDBException(Exception):
    pass

class MatchAlreadyAdded(MatchDBException):
    pass

class MatchDB():
    def __init__(self, cache_get_matches=True):

        from popflash_api import API_VERSION
        self.API_VERSION = API_VERSION
        
        # yes jamal i know this is insecure
        self.client = pymongo.MongoClient("mongodb+srv://popskill:popskill@cluster0.imry2.mongodb.net/popskill?retryWrites=true&w=majority")
        self.db = self.client.popskill
        self.matches = self.db['matches']
        self.matches.create_index("match_id", unique=True)
        self.match_cache = self.db['match_cache_v' + str(API_VERSION)]
        self.match_cache.create_index("match_id", unique=True)

        self.seasons = {0: (datetime.datetime(2019, 1, 1, 0, 0, 0), datetime.datetime(2020, 3, 1, 0, 0, 0)),
                        1: (datetime.datetime(2020, 3, 1, 0, 0, 0), datetime.datetime(2020, 5, 1, 0, 0, 0))}

        self.cache_get_matches = cache_get_matches
        self.matches_cache = {}

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
        # print(cache_ids)

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
        #  ignore_existing: If match is already in database, ignore it
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
        return m

    def get_matches(self, season=None):
        # if self.cache_get_matches and
        print('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA') 
        
        if season is not None:
            start, end = self.seasons[season]
            t0 = time.time()
            # matches = list(self.match_cache.find({"date": {"$gte": start, "$lt": end}}))
            matches = list(self.match_cache.find({}))
            print("time", time.time() - t0, "time")
        else:
            print("no season")
            matches = list(self.match_cache.find({}))
        
        t0 = time.time()
        matches = [self._df_undictify(m) for m in sorted(matches, key=lambda x: x['date'])]
        print([m['date'] for m in matches])
        for m in matches:
            del m['_id']
        print("time", time.time() - t0, "time")
        return matches
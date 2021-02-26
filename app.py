import popflash_api as pf
import mlcrate as mlc
import dateparser
from collections import defaultdict
import numpy as np
from itertools import groupby
import os
import discord
import asyncio
from threading import Thread
import copy
from datetime import datetime

from flask import Flask, jsonify
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS

from skill_tracker import TrueSkillTracker, Player
from match_db import MatchDB
import match_db

app = Flask(__name__)
CORS(app)
# api = Api(app)

seasons = {0: (datetime(2020, 1, 1, 0, 0, 0), datetime(2021, 3, 1, 0, 0, 0)),
           1: (datetime(2021, 3, 1, 0, 0, 0), datetime(2021, 5, 1, 0, 0, 0))}

# Launch database
db = MatchDB(seasons)
db.build_cache()

ts = {}
for season in seasons.keys():
  ts[season] = TrueSkillTracker()

  for match in db.get_matches(season=season):
    ts[season].process_match(match)

################ WEB API

class Matches(Resource):
  def get(self):
    ret_matches = db.get_matches(season=0)

    for match in ret_matches:
      match['date'] = match['date'].isoformat()

    return ret_matches

@app.route('/v2/leaderboard', defaults={'season': max(seasons.keys())})
@app.route('/v2/leaderboard/<int:season>')
class Leaderboard(Resource):
  def get(self, season: int):

    rankings = []
    for user, skill in ts[season].skills.items():
      if ts[season].player_counts[user] < ts[season].min_ranked_matches: 
        continue

      user_last_diff = ts[season].skill_history[-1][user].mu - ts[season].skill_history[-2][user].mu 
      
      user_rwp = (ts[season].player_rounds_won[user] / ts[season].player_rounds_played[user])
      user_hltv = np.mean(ts[season].player_hltv_history[user])
      user_adr = np.mean(ts[season].player_adr_history[user])

      rankings.append({'username': user.name, 'SR': int(skill.mu), 'SRvar': int(skill.sigma), 'matches_played': ts[season].player_counts[user], 'user_id': user.id, 
                  'last_diff': int(user_last_diff), 'rwp': user_rwp, 'hltv': user_hltv, 'adr': user_adr})


    resp = {'config_string': 'TODO', 'season_id': season, 'season_start': seasons[season][0].isoformat(), 'season_end': seasons[season][1].isoformat(), 'rankings': rankings}
    return jsonify(flask.resp)


class PlayerRankings(Resource):
  def get(self):
    season = 0
    ret = []

    matches = db.get_matches(season=season)

    for user, skill in ts[season].skills.items():
      if ts[season].player_counts[user] < ts[season].min_ranked_matches: 
        continue

      user_skill_history = [{'SR': h[user].mu, 'date': '' if i==0 else matches[i-1]['date'].isoformat(), 'match_id': 0 if i==0 else matches[i-1]['match_id']} for i,h in enumerate(ts[season].skill_history)]
      user_skill_history = [list(g)[0] for k,g in groupby(user_skill_history, lambda x: x['SR'])]

      user_last_diff = user_skill_history[-1]['SR'] - user_skill_history[-2]['SR']
      
      user_rwp = (ts[season].player_rounds_won[user] / ts[season].player_rounds_played[user])
      user_hltv = np.mean(ts[season].player_hltv_history[user])
      user_adr = np.mean(ts[season].player_adr_history[user])

      ret.append({'username': user.name, 'SR': int(skill.mu), 'SRvar': int(skill.sigma), 'matches_played': ts[season].player_counts[user], 'user_id': user.id, 
                  'last_diff': int(user_last_diff), 'user_skill_history': user_skill_history, 'rwp': user_rwp, 'hltv': user_hltv, 'adr': user_adr})
    return ret

parser = reqparse.RequestParser()
parser.add_argument('match_url')

class SubmitMatch(Resource):
  def post(self):
    args = parser.parse_args()
    match_id = args['match_url'].split('/')[-1]
    if not match_id.isnumeric():
      return "Bad popflash match url provided", 400

    try:
      match = db.add_match(match_id)
    except match_db.MatchAlreadyAdded:
      return "Match already processed", 400

    match_season = None
    for s, (start, end) in seasons.items():
      if start < match['date'].replace(tzinfo=None) < end:
        match_season = s

    skills_before = ts[match_season].skills.copy()

    # Will do nothing if match has already been processed
    ts[match_season].process_match(match)

    # Response stuff for discord
    resp = {}
    t1,t2 = 'WL' if match['team1score']>match['team2score'] else 'LW' if match['team1score']<match['team2score'] else 'TT'
    resp = {
        'team1status': "{} - {}".format(t1, match['team1score']),
        'team2status': "{} - {}".format(t2, match['team2score'])
    }

    t1stats = []
    for row in match['team1table'].values():
      player = Player(row['Name'], row['id'])
      oldskill = skills_before[player].mu
      newskill = ts[match_season].skills[player].mu
      diff = newskill - oldskill
      t1stats.append('{} - {} **({}{})**'.format(player.name, int(newskill), '+' if diff>0 else '', int(diff)))

    t2stats = []
    for row in match['team2table'].values():
      player = Player(row['Name'], row['id'])
      oldskill = skills_before[player].mu
      newskill = ts[match_season].skills[player].mu
      diff = newskill - oldskill
      t2stats.append('{} - {} **({}{})**'.format(player.name, int(newskill), '+' if diff>0 else '', int(diff)))

    resp['team1stats'] = '\n'.join(t1stats)
    resp['team2stats'] = '\n'.join(t2stats)

    resp['time'] = match['date'].isoformat()
    resp['image'] = match['map_image']

    return resp, 200

# api.add_resource(PlayerRankings, '/rankings')
# api.add_resource(SubmitMatch, '/submit_match')
# api.add_resource(Matches, '/matches')

# api.add_resource(Leaderboard, '/v2/leaderboard/<int:season>')
# api.add_resource(Leaderboard, '/v2/leaderboard/')

# ronan = ([h[Player('Porkypus', '758084')].mu for h in ts.skill_history])
# ronan_var = np.array([h[Player('Porkypus', '758084')].sigma for h in ts.skill_history])
# ronan = np.array([k for k, g in groupby(ronan)])
# ronan_var = np.array([k for k, g in groupby(ronan_var)])
# import matplotlib.pyplot as plt
# plt.plot(ronan)
# plt.fill_between(np.arange(len(ronan)), ronan-ronan_var, ronan+ronan_var, alpha=0.2)
# plt.ylim(800, 2000)
# plt.show()
# print(ronan)

if __name__ == '__main__':
    app.run(debug=False, port=7355)
    

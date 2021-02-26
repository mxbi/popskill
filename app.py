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

from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS

from skill_tracker import TrueSkillTracker, Player
from match_db import MatchDB

app = Flask(__name__)
CORS(app)
api = Api(app)

if not os.path.exists('matches/'):
  os.mkdir('matches/')



# Load seed matches from before we had user submissions. From collect_seed_matches.py
# matches = mlc.load('seedmatches4.pkl')
# print(len(matches), 'seed matches')

# Add matches submitted by users
# for match_id in [x for x in open('submitted_matches.txt').read().split('\n') if x]:
#   try:
#     match = mlc.load('matches/{}.pkl'.format(match_id))
#   except:
#     match = pf.get_match(match_id)
#     mlc.save(match, 'matches/{}.pkl'.format(match_id))

#   matches.append(match)

# Bring forward old dates from before the format was updated
# for m in matches:
#   if isinstance(m['date'], str):
#     print('updating date', m['match_id'])
#     m['date'] = dateparser.parse(m['date'])
#     mlc.save(m, 'matches/{}.pkl'.format(m['match_id']))

# matches = sorted(matches, key=lambda x: x['date'])

# print('Loaded', len(matches), 'Matches')

ts = TrueSkillTracker()

db = MatchDB()
db.build_cache()


for match in db.get_matches(season=0):
  ts.process_match(match)

################ WEB API

class Matches(Resource):
  def get(self):
    # ret_matches = copy.deepcopy(db.get_matches(season=0))
    ret_matches = db.get_matches(season=0)

    for match in ret_matches:
      # match['team1table'].index = match['team1table']['player_link'].apply(lambda x: x.split('/')[-1])
      # match['team2table'].index = match['team2table']['player_link'].apply(lambda x: x.split('/')[-1])
      # match['team1table'] = match['team1table'].to_dict(orient='index')
      # match['team2table'] = match['team2table'].to_dict(orient='index')
      match['date'] = match['date'].isoformat()

    return ret_matches


class PlayerRankings(Resource):
  def get(self):
    ret = []

    matches = db.get_matches(season=0)

    for user, skill in ts.skills.items():
      if ts.player_counts[user] < ts.min_ranked_matches: 
        continue

      user_skill_history = [{'SR': h[user].mu, 'date': '' if i==0 else matches[i-1]['date'].isoformat(), 'match_id': 0 if i==0 else matches[i-1]['match_id']} for i,h in enumerate(ts.skill_history)]
      user_skill_history = [list(g)[0] for k,g in groupby(user_skill_history, lambda x: x['SR'])]

      user_last_diff = user_skill_history[-1]['SR'] - user_skill_history[-2]['SR']
      
      user_rwp = (ts.player_rounds_won[user] / ts.player_rounds_played[user])
      user_hltv = np.mean(ts.player_hltv_history[user])

      ret.append({'username': user.name, 'SR': int(skill.mu), 'SRvar': int(skill.sigma), 'matches_played': ts.player_counts[user], 'user_id': user.id, 
                  'last_diff': int(user_last_diff), 'user_skill_history': user_skill_history, 'rwp': user_rwp, 'hltv': user_hltv})
    return ret

parser = reqparse.RequestParser()
parser.add_argument('match_url')

class SubmitMatch(Resource):
  def post(self):
    args = parser.parse_args()
    match_id = args['match_url'].split('/')[-1]
    if not match_id.isnumeric():
      return "Bad popflash match url provided", 400

    if match_id in ts.match_ids:
      return "Match already processed", 400

    match_url = 'https://popflash.site/match/' + match_id

    match = pf.get_match(match_url)
    matches.append(match)
    
    open('submitted_matches.txt', 'a').write(match_id + '\n')
    mlc.save(match, 'matches/{}.pkl'.format(match_id))

    skills_before = ts.skills.copy()

    # Will do nothing if match has already been processed
    ts.process_match(match)

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
      newskill = ts.skills[player].mu
      diff = newskill - oldskill
      t1stats.append('{} - {} **({}{})**'.format(player.name, int(newskill), '+' if diff>0 else '', int(diff)))

    t2stats = []
    for row in match['team2table'].values():
      player = Player(row['Name'], row['id'])
      oldskill = skills_before[player].mu
      newskill = ts.skills[player].mu
      diff = newskill - oldskill
      t2stats.append('{} - {} **({}{})**'.format(player.name, int(newskill), '+' if diff>0 else '', int(diff)))

    resp['team1stats'] = '\n'.join(t1stats)
    resp['team2stats'] = '\n'.join(t2stats)

    resp['time'] = match['date'].isoformat()
    resp['image'] = match['map_image']

    return resp, 200

api.add_resource(PlayerRankings, '/rankings')
api.add_resource(SubmitMatch, '/submit_match')
api.add_resource(Matches, '/matches')


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
    

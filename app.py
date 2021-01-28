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

from trueskill import Rating, TrueSkill

from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
api = Api(app)

if not os.path.exists('matches/'):
  os.mkdir('matches/')

class Player:
  def __init__(self, name, id):
    self.name = name
    self.id = id
    self.games = 0

  def __repr__(self):
    return self.name

  def __eq__(self, other):
    return self.id.__eq__(other.id)

  def __hash__(self):
    return self.id.__hash__()

class TrueSkillTracker:
  def __init__(self, default_rating=25):
    self.ts = TrueSkill(mu=1000, sigma=8.33*40/5, beta=4.16*40, tau=0.083*40)
    self.skills = defaultdict(lambda: self.ts.create_rating())
    self.hltv = defaultdict(int)
    self.player_counts = defaultdict(int)
    self.skill_history = [self.skills.copy()]
    self.match_ids = [] # To avoid repeating matches

  def process_match(self, match):
    if match['match_id'] in self.match_ids:
      print('Warning: tried to process the same match twice')
      return

    self.match_ids.append(match['match_id'])
    
    trace = False #match['match_id'] == '1141099'
    if trace:
      print('TRACING MATCH', match['match_id'])
    
    t1table = match['team1table']
    t2table = match['team2table']
    t1players = [Player(p['Name'], p['id']) for _, p in t1table.iterrows()]
    t2players = [Player(p['Name'], p['id']) for _, p in t2table.iterrows()]

    if trace:
      print('* before match:')
      trace_skill1 = {p: int(self.skills[p].mu) for p in t1players}
      trace_skill2 = {p: int(self.skills[p].mu) for p in t2players}
      print('team1:', trace_skill1)
      print('team2:', trace_skill2)

    for p in t1players:
      if p.id == '1666369':
        print(match)
      self.player_counts[p] += 1
    for p in t2players:
      if p.id == '1666369':
        print(match)
      self.player_counts[p] += 1

    rounds = [1]*match['team1score'] + [2]*match['team2score']
    np.random.seed(42)
    rounds = np.random.permutation(rounds)

    if trace:
      print('Generated round sequence:', rounds)

    # print(t1weights.sum(), t2weights.sum())
    
    for i, r in enumerate(rounds):
      if trace:
        print('* round', i, 'winner team', r)

      t1skills = [self.skills[p] for p in t1players]
      t2skills = [self.skills[p] for p in t2players]

      t1weights = np.array([p['HLTV'] for _, p in t1table.iterrows()])**1
      t2weights = np.array([p['HLTV'] for _, p in t2table.iterrows()])**1

      # Popflash games can't be drawn
      ranks = [1, 0] if r==2 else [0, 1] 

      if r==1:
        t2weights = 1/t2weights
      else:
        t1weights = 1/t1weights

      t1weights **= 0.75
      t2weights **= 0.75

      t1weights /= (t1weights.sum() / 5)
      t2weights /= (t2weights.sum() / 5)
      # print(t1weights.sum(), t2weights.sum())

      if trace:
        print('weights:', np.around(t1weights, 1), np.around(t2weights, 1))

      newt1skills, newt2skills = self.ts.rate([t1skills, t2skills], ranks, weights=[t1weights, t2weights])

      if trace:
        print('team1:', {p: round(newt1skills[i].mu - self.skills[p].mu, 2) for i, p in enumerate(t1players)})
        print('team2:', {p: round(newt2skills[i].mu - self.skills[p].mu, 2) for i, p in enumerate(t2players)})

      for p, n in zip(t1players, newt1skills):
        self.skills[p] = n
      for p, n in zip(t2players, newt2skills):
        self.skills[p] = n

    self.skill_history.append(self.skills.copy())

    if trace:
      print('* OVERALL CHANGE:')
      print('team1:', {p: round(self.skills[p].mu - self.skill_history[-2][p].mu, 2) for i, p in enumerate(t1players)})
      print('team2:', {p: round(self.skills[p].mu - self.skill_history[-2][p].mu, 2) for i, p in enumerate(t2players)})



    


GET_MATCHES = 0

if GET_MATCHES:
  matches = '1146703,1146629,1142428,1142326,1135008,1134907,1094886,1094757,1092480,1088135,1088067,1087975,1142520,1142428,1142326,1133930,1131132,1128002,1125764,1123980,1123292,1123133,1120870,1118333,1109606,1101715,1101607,1094886,1094757,1094696,1092480,1092336,1147353,1147236,1147113,1146703,1146629,1146522,1146408,1144625,1144458,1143208,1143041,1142520,1142428,1142326,1142244,1141099,1140989,1140501,1135008,1134907,1147353,1147236,1147113,1146703,1146629,1146522,1146408,1145704,1145612,1144316,1142244,1141745,1141659,1140989,1140501,1135008,1109606,1101715,1101607,1094886'.split(',')

  user_urls = [x for x in open('popflash_ids.txt').read().split('\n') if x]

  users = [pf.get_profile(u) for u in user_urls]
  print(users)

  for u in users:
    match = u['match_table']
    match = match[match['DATE'].str.contains('Jan')] # TODO: Fix
    matches.extend(match['match_link'].values)

  print(len(matches))
  matches = [m.split('/')[-1] for m in matches]
  matches = set(matches)
  print(len(matches))

  matches = [pf.get_match(m) for m in matches]
  mlc.save(matches, 'matches3.pkl')
else:
  matches = mlc.load('matches3.pkl')

# Users that are not part of CUDGS. Matches will not be considered if they contain any of these users
user_blacklist = ['1123980', '1640115', '1642207', '1640116', '1640119', '1642471', '1640128']

matches = [m for m in matches if not (set(m['team1table']['id']).intersection(user_blacklist) or set(m['team2table']['id']).intersection(user_blacklist))]

# Add matches submitted by users
for match_id in [x for x in open('submitted_matches.txt').read().split('\n') if x]:
  try:
    match = mlc.load('matches/{}.pkl'.format(match_id))
  except:
    match = pf.get_match(match_id)
    mlc.save(match, 'matches/{}.pkl'.format(match_id))

  matches.append(match)

matches = sorted(matches, key=lambda x: x['date'])

# Bring forward old dates from before the format was updated
for m in matches:
  if isinstance(m['date'], str):
    m['date'] = dateparser.parse(m['date'])


ts = TrueSkillTracker()

for match in matches:
  ts.process_match(match)

# for x in sorted(ts.skills.items(), key=lambda x: x[1].mu, reverse=True):
#   if x[1].sigma < 1000 and ts.player_counts[x[0]] >= 3:
#     print(x, ts.player_counts[x[0]])

class PlayerRankings(Resource):
  def get(self):
    ret = []
    for user, skill in ts.skills.items():
      user_skill_history = [{'SR': h[user].mu, 'date': '' if i==0 else matches[i-1]['date'].isoformat(), 'match_id': 0 if i==0 else matches[i-1]['match_id']} for i,h in enumerate(ts.skill_history)]
      user_skill_history = [list(g)[0] for k,g in groupby(user_skill_history, lambda x: x['SR'])]
      user_last_diff = user_skill_history[-1]['SR'] - user_skill_history[-2]['SR']
      ret.append({'username': user.name, 'SR': int(skill.mu), 'SRvar': int(skill.sigma), 'matches_played': ts.player_counts[user], 'user_id': user.id, 'last_diff': int(user_last_diff), 'user_skill_history': user_skill_history})
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
    resp['team1status'] = '{} - {}'.format('W' if match['team1score'] > match['team2score'] else 'L', match['team1score'])
    resp['team2status'] = '{} - {}'.format('W' if match['team2score'] > match['team1score'] else 'L', match['team2score'])

    t1stats = []
    for _, row in match['team1table'].iterrows():
      player = Player(row['Name'], row['id'])
      oldskill = skills_before[player].mu
      newskill = ts.skills[player].mu
      diff = newskill - oldskill
      t1stats.append('{} - {} **({}{})**'.format(player.name, int(newskill), '+' if diff>0 else '', int(diff)))

    t2stats = []
    for _, row in match['team2table'].iterrows():
      player = Player(row['Name'], row['id'])
      oldskill = skills_before[player].mu
      newskill = ts.skills[player].mu
      diff = newskill - oldskill
      t2stats.append('{} - {} **({}{})**'.format(player.name, int(newskill), '+' if diff>0 else '', int(diff)))

    resp['team1stats'] = '\n'.join(t1stats)
    resp['team2stats'] = '\n'.join(t2stats)

    resp['time'] = match['date']
    resp['image'] = match['map_image']

    return resp, 200

api.add_resource(PlayerRankings, '/rankings')
api.add_resource(SubmitMatch, '/submit_match')


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
    app.run(debug=True, port=7355)
    

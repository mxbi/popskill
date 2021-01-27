import popflash_api as pf
import mlcrate as mlc
import dateparser
from collections import defaultdict
import numpy as np
from itertools import groupby

from trueskill import Rating, TrueSkill

from flask import Flask
from flask_restful import Resource, Api
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
api = Api(app)

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
    self.ts = TrueSkill()
    self.skills = defaultdict(lambda: self.ts.create_rating(default_rating))
    self.hltv = defaultdict(int)
    self.player_counts = defaultdict(int)
    self.skill_history = [self.skills.copy()]

  def process_match(self, match):
    t1table = match['team1table']
    t2table = match['team2table']
    t1players = [Player(p['Name'], p['id']) for _, p in t1table.iterrows()]
    t2players = [Player(p['Name'], p['id']) for _, p in t2table.iterrows()]

    for p in t1players:
      if p.id == '1666369':
        print(match)
      self.player_counts[p] += 1
    for p in t2players:
      if p.id == '1666369':
        print(match)
      self.player_counts[p] += 1

    t1weights = np.array([p['HLTV'] for _, p in t1table.iterrows()])
    t2weights = np.array([p['HLTV'] for _, p in t2table.iterrows()])

    rounds = [1]*match['team1score'] + [2]*match['team2score']
    np.random.seed(42)
    rounds = np.random.permutation(rounds)

    # print(t1weights.sum(), t2weights.sum())
    
    for r in rounds:

      t1skills = [self.skills[p] for p in t1players]
      t2skills = [self.skills[p] for p in t2players]

      # Popflash games can't be drawn
      ranks = [1, 0] if r==2 else [0, 1]

      if r==1:
        t2weights = 1/t2weights
      else:
        t1weights = 1/t1weights

      t1weights /= (t1weights.sum() / 5)
      t2weights /= (t2weights.sum() / 5)
      # print(t1weights.sum(), t2weights.sum())

      newt1skills, newt2skills = self.ts.rate([t1skills, t2skills], ranks, weights=[t1weights, t2weights])
      for p, n in zip(t1players, newt1skills):
        self.skills[p] = n
      for p, n in zip(t2players, newt2skills):
        self.skills[p] = n

    self.skill_history.append(self.skills.copy())

    


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

  # for m in matches:
    # print(m)
    # pf.get_match('/match/' + m)
  matches = [pf.get_match(m) for m in matches]
  mlc.save(matches, 'matches3.pkl')
else:
  matches = mlc.load('matches3.pkl')

# Users that are not part of CUDGS. Matches will not be considered if they contain any of these users
user_blacklist = ['1123980', '1640115', '1642207', '1640116', '1640119', '1642471', '1640128']

matches = [m for m in matches if not (set(m['team1table']['id']).intersection(user_blacklist) or set(m['team2table']['id']).intersection(user_blacklist))]

for m in matches:
  m['date'] = dateparser.parse(m['date'])

matches = sorted(matches, key=lambda x: x['date'])

ts = TrueSkillTracker()


for match in matches:
  ts.process_match(match)

for x in sorted(ts.skills.items(), key=lambda x: x[1].mu, reverse=True):
  if x[1].sigma < 10 and ts.player_counts[x[0]] >= 5:
    print(x, ts.player_counts[x[0]])

class PlayerRankings(Resource):
  def get(self):
    ret = []
    for user, skill in ts.skills.items():
      user_skill_history = [h[user].mu*40 for h in ts.skill_history]
      user_skill_history = [k for k,g in groupby(user_skill_history)]
      user_last_diff = user_skill_history[-1] - user_skill_history[-2]
      ret.append({'username': user.name, 'SR': int(skill.mu*40), 'SRvar': int(skill.sigma*40), 'matches_played': ts.player_counts[user], 'user_id': user.id, 'last_diff': int(user_last_diff), 'user_skill_history': user_skill_history})
    return ret


    # return [ for user, skill in ts.skills.items()]



api.add_resource(PlayerRankings, '/rankings')

# ronan = ([h[Player('Porkypus', '1610522')].mu*40 for h in ts.skill_history])
# ronan_var = np.array([h[Player('Porkypus', '1610522')].sigma*40 for h in ts.skill_history])
# import matplotlib.pyplot as plt
# plt.plot(ronan)
# plt.fill_between(np.arange(len(ronan)), ronan-ronan_var, ronan+ronan_var, alpha=0.2)
# plt.ylim(800, 1300)
# plt.show()
# print(ronan)

if __name__ == '__main__':
    app.run(debug=True)
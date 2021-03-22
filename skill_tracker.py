from trueskill import Rating, TrueSkill
from collections import defaultdict
import numpy as np
 
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
  def __init__(self, username_tracker, mu=1000, sigma=8.33*40/2, beta=4.16*40, tau=0.083*40*4, mode='match', min_ranked_matches=2):
    self.min_ranked_matches = min_ranked_matches
    assert mode in ['round', 'match']
    self.mode = mode
    self.ts = TrueSkill(mu=mu, sigma=sigma, beta=beta, tau=tau, draw_probability=0) #, backend=(logistic.cdf, logistic.pdf, logistic.ppf))
    
    self.skills = defaultdict(lambda: self.ts.create_rating())
    self.hltv = defaultdict(int)
    self.player_counts = defaultdict(int)
    self.skill_history = [self.skills.copy()]
    self.match_ids = [] # To avoid repeating matches
    self.hltv = 0.75
    self.user_names = username_tracker

    self.user_last_diffs = {}

    self.player_rounds_played = defaultdict(int)
    self.player_rounds_won = defaultdict(int)
    self.player_matches_played = defaultdict(int)
    self.player_matches_won = defaultdict(int)
    self.player_hltv_history = defaultdict(list)
    self.player_adr_history = defaultdict(list)
    #print(f'RATING mu={mu} sigma={sigma} beta={beta}, tau={tau}, hltv={hltv}, mode=GAME')

  def process_match(self, match):
    if match['match_id'] in self.match_ids:
      print('Warning: tried to process the same match twice')
      return

    self.match_ids.append(match['match_id'])
    
    trace = match['match_id'] == '1149271'
    if trace:
      print('TRACING MATCH', match['match_id'])
    
    t1table = match['team1table']
    t2table = match['team2table']
    t1players = [Player(p['Name'], p['id']) for p in t1table.values()]
    t2players = [Player(p['Name'], p['id']) for p in t2table.values()]

    if trace:
      print('* before match:')
      trace_skill1 = {p: int(self.skills[p].mu) for p in t1players}
      trace_skill2 = {p: int(self.skills[p].mu) for p in t2players}
      print('team1:', trace_skill1)
      print('team2:', trace_skill2)

    for p in t1players:
      self.player_counts[p] += 1
      self.player_rounds_played[p] += match['team1score'] + match['team2score']
      self.player_rounds_won[p] += match['team1score']
      self.player_matches_played[p] += 1
      if match['team1score'] > match['team2score']:
        self.player_matches_won[p] += 1
        
    for p in t2players:
      self.player_counts[p] += 1
      self.player_rounds_played[p] += match['team1score'] + match['team2score']
      self.player_rounds_won[p] += match['team2score']
      self.player_matches_played[p] += 1
      if match['team2score'] > match['team1score']:
        self.player_matches_won[p] += 1

    # Calculate number of wins each team got
    if self.mode == 'match':
      round_diff = match['team1score'] - match['team2score']
      rounds = [1] if round_diff >= 0 else [2]
      if match['team1score'] == match['team2score']:
        rounds = [0] # special case!!

    elif self.mode == 'round':
      rounds = [1]*match['team1score'] + [2]*match['team2score']

    elif self.mode == 'round_diff':
      round_diff = match['team1score'] - match['team2score']
      rounds = [1]*round_diff if round_diff > 0 else [2]*(-round_diff)
      if round_diff == 0: # draw
        rounds = [0]

    np.random.seed(42)
    rounds = np.random.permutation(rounds)

    if trace:
      print('Generated round sequence:', rounds)

    # Keep track of HLTVs
    table = {**t1table, **t2table}
    for p in t1players + t2players:
        hltv = table[p.id]['HLTV']
        adr = table[p.id]['ADR']
        self.user_names[p.id] = p
        self.player_hltv_history[p].append(hltv)
        self.player_adr_history[p].append(adr)
    
    for i, r in enumerate(rounds):
      if trace:
        print('* round', i, 'winner team', r)

      t1skills = [self.skills[p] for p in t1players]
      t2skills = [self.skills[p] for p in t2players]

      t1weights = np.array([p['HLTV'] for p in t1table.values()])
      t2weights = np.array([p['HLTV'] for p in t2table.values()])
      
      #### Calculating ratings (weighted by HLTV)

      if r == 0: # draw
        ranks = [0, 0]
        t1weights = [1, 1, 1, 1, 1] # Not sure how to do ratings on a draw
        t2weights = [1, 1, 1, 1, 1]

      else:
        ranks = [1, 0] if r==2 else [0, 1] 

        if r==1:
          t2weights = 1/t2weights
        else:
          t1weights = 1/t1weights

        t1weights **= self.hltv
        t2weights **= self.hltv

        t1weights /= (t1weights.sum() / 5)
        t2weights /= (t2weights.sum() / 5)

      if trace:
        print('weights:', np.around(t1weights, 1), np.around(t2weights, 1))

      newt1skills, newt2skills = self.ts.rate([t1skills, t2skills], ranks, weights=[t1weights, t2weights])

      if trace:
        print('team1:', {p: round(newt1skills[i].mu - self.skills[p].mu, 2) for i, p in enumerate(t1players)})
        print('team2:', {p: round(newt2skills[i].mu - self.skills[p].mu, 2) for i, p in enumerate(t2players)})

      for p, n, old in zip(t1players, newt1skills, t1skills):
        self.skills[p] = n
        self.user_last_diffs[p] = n.mu - old.mu
      for p, n, old in zip(t2players, newt2skills, t2skills):
        self.skills[p] = n
        self.user_last_diffs[p] = n.mu - old.mu

    self.skill_history.append(self.skills.copy())

    if trace:
      print('* OVERALL CHANGE:')
      print('team1:', {p: round(self.skills[p].mu - self.skill_history[-2][p].mu, 2) for i, p in enumerate(t1players)})
      print('team2:', {p: round(self.skills[p].mu - self.skill_history[-2][p].mu, 2) for i, p in enumerate(t2players)})
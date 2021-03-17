from collections import defaultdict
from datetime import datetime, date
from itertools import groupby, combinations

import flask
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

import match_db
from match_db import MatchDB
from skill_tracker import TrueSkillTracker, Player

app = Flask(__name__)
CORS(app)
# api = Api(app)

seasons = {0: (datetime(2020, 1, 1, 0, 0, 0), datetime(2021, 3, 1, 0, 0, 0)),
           1: (datetime(2021, 3, 1, 0, 0, 0), datetime(2021, 5, 1, 0, 0, 0))}
default_season = 1

# Launch database
db = MatchDB(seasons)
db.build_cache()

username_tracker = {}

ts = {}
ts[0] = TrueSkillTracker(username_tracker=username_tracker)
ts[1] = TrueSkillTracker(username_tracker=username_tracker, min_ranked_matches=1)

for season in seasons.keys():
    matches = db.get_matches(season=season)
    for match in matches:
        ts[season].process_match(match)

################ WEB API

@app.route('/v2/leaderboard/<int:season>', methods=['GET'])
@app.route('/v2/leaderboard', methods=['GET'])
def get_leaderboard(season: int=default_season):
    if season not in seasons:
        return "Response", 400

    optout = db.get_optout_players()

    rankings = []
    for user, skill in ts[season].skills.items():
        if ts[season].player_counts[user] < ts[season].min_ranked_matches: 
            continue
        
        if int(user.id) in optout:
            continue

        # user_last_diff = ts[season].skill_history[-1][user].mu - ts[season].skill_history[-2][user].mu
        user_last_diff = ts[season].user_last_diffs[user]
        
        user_rwp = (ts[season].player_rounds_won[user] / ts[season].player_rounds_played[user])
        user_hltv = np.mean(ts[season].player_hltv_history[user])
        user_adr = np.mean(ts[season].player_adr_history[user])

        rankings.append({'username': user.name, 'SR': int(skill.mu), 'SRvar': int(skill.sigma), 'matches_played': ts[season].player_counts[user], 'user_id': user.id, 
                                'last_diff': int(user_last_diff), 'rwp': user_rwp, 'hltv': user_hltv, 'adr': user_adr})


    resp = {'config_string': 'TODO', 'season_id': season, 'season_start': seasons[season][0].isoformat(), 'season_end': seasons[season][1].isoformat(), 'rankings': rankings}
    return resp

@app.route('/v2/seasons')
def get_seasons():
    return seasons

@app.route('/v2/user/<int:user_id>/<int:season>', methods=['GET'])
@app.route('/v2/user/<int:user_id>', methods=['GET'])
def get_user(user_id: int, season: int=None):
    username = '[unknown]'

    user_matches = db.get_matches(user_id=user_id, season=season)
    season_matches = defaultdict(list)
    max_season = -1
    for m in user_matches:
        season_matches[m['season']].append(m)
        max_season = max(max_season, m['season'])

    user = username_tracker[str(user_id)]
    # DEPRECATED
    _seasons = [season] if season else seasons.keys()
    user_skill_histories = defaultdict(int)
    for s in _seasons:
        matches = db.get_matches(season=s)


        user_skill_history = [{'SR': h[user].mu, 'date': '' if i==0 else matches[i-1]['date'].isoformat(), 'match_id': 0 if i==0 else matches[i-1]['match_id']} for i,h in enumerate(ts[s].skill_history)]
        user_skill_history = [list(g)[0] for k,g in groupby(user_skill_history, lambda x: x['SR'])]
        user_skill_histories[s] = user_skill_history
    # /DEPRECATED

    # We want empty seasons instead of missing seasons where the user has never played
    if season:
        season_matches[season]
    else:
        for season in seasons:
            season_matches[season]
    
    # We do a bit of a dance to get the user's username
    username = user.name
    resp = {"user_id": user_id, 'seasons': season_matches, 'username': username, "user_skill_history": user_skill_histories}
    return resp

@app.route('/v2/match/<int:match_id>', methods=['GET'])
def get_match(match_id: int):
    try:
        return db.get_match(match_id)
    except match_db.MatchDoesNotExist:
        return "Match does not exist (or is not in cache)", 200

@app.route('/v2/balance', methods=['POST'])
def balance(season: int=default_season):
    # print(request.json['match1'])
    users = [x.split('/')[-1] for x in request.json['team1'] + request.json['team2'] if x]
    print(users)
    users = [username_tracker[_id] for _id in users]
    print(users)

    players = [(u, ts[season].skills[u]) for u in users]

    def team2(team1):
        return (u for u in players if u not in team1)

    def drawprob(team1):
        return ts[season].ts.quality(
            [(sr for u,sr in t) for t in (team1, team2(team1))]
        )

    best_team1 = max(
        combinations(players, len(players) // 2),
        key=drawprob
    )
    best_team2 = team2(best_team1)

    resp = {
        "team1": '\n'.join(f"{u.name} ({int(sr.mu)})" for u,sr in best_team1),
        "team2": '\n'.join(f'{u.name} ({int(sr.mu)})' for u,sr in best_team2),
        "t1rating": sum(sr.mu for u,sr in best_team1),
        "t2rating": sum(sr.mu for u,sr in best_team2),
    }
    resp['diff'] = abs(resp['t2rating'] - resp['t1rating'])
    resp['print'] = f"SUGGESTED TEAM 1:\n{resp['team1']}\n\nSUGGESTED TEAM 2:\n{resp['team2']}\n\nELO DIFF: f{resp['diff']}"
    print(resp)
    return resp, 200

############ COMPAT
@app.route('/matches')
def get_matches_v1():
    return jsonify(db.get_matches(season=default_season))

@app.route('/rankings')
def get_rankings_v1():
    season = 0
    ret = []

    matches = db.get_matches(season=default_season)

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
    return jsonify(ret) # list must be jsonifyed manually :(

@app.route('/submit_match', methods=['POST'])
def post_submit_match_v1():
    match_id = request.json['match_url'].split('/')[-1]
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

    optout = db.get_optout_players()

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
        if int(player.id) in optout:
            t1stats.append('{}'.format(player.name))
        else:
            t1stats.append('{} - {} **({}{})**'.format(player.name, int(newskill), '+' if diff>0 else '', int(diff)))

    t2stats = []
    for row in match['team2table'].values():
        player = Player(row['Name'], row['id'])
        oldskill = skills_before[player].mu
        newskill = ts[match_season].skills[player].mu
        diff = newskill - oldskill
        if int(player.id) in optout:
            t2stats.append('{}'.format(player.name))
        else:
            t2stats.append('{} - {} **({}{})**'.format(player.name, int(newskill), '+' if diff>0 else '', int(diff)))

    resp['team1stats'] = '\n'.join(t1stats)
    resp['team2stats'] = '\n'.join(t2stats)

    resp['time'] = match['date'].isoformat()
    resp['image'] = match['map_image']

    print('end')
    return resp, 200

class JSONEncoder(flask.json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date): return obj.isoformat()
        if isinstance(obj, list): return jsonify(obj)
        try:
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return tuple(iterable)

        return flask.json.JSONEncoder.default(self, obj)

app.json_encoder = JSONEncoder

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
        

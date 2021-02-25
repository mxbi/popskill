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
import datetime

from match_db import MatchDB


		

matches = ['1088135', '1141745', '1088067', '1094696', '1141659', '1147113', '1143041', '1140989', '1141099', '1144316', '1134907', '1142326', '1101715', '1145612', '1092480', '1087975', '1146636', '1101607', '1094886', '1109606', '1146703', '1143208', '1142244', '1145704', '1140501', '1146522', '1144458', '1147353', '1135008', '1094757', '1147236', '1144625', '1146714', '1146408', '1146629', '1142520', '1142428', '1092336']
print(len(matches), 'seed matches')

db = MatchDB()

# Users that are not part of CUDGS. Matches will not be considered if they contain any of these users
user_blacklist = ['1123980', '1640115', '1642207', '1640116', '1640119', '1642471', '1640128']

for match in matches:
	m = pf.get_match(match)
	if not (set(m['team1table']['id']).intersection(user_blacklist) or set(m['team2table']['id']).intersection(user_blacklist)):
		print(m)
		print(match)
		db.add_match(match, season=0, cache=m)

matches = [pf.get_match(m) for m in matches]


matches = [m for m in matches if not (set(m['team1table']['id']).intersection(user_blacklist) or set(m['team2table']['id']).intersection(user_blacklist))]

print(len(matches))
mlc.save(matches, 'seedmatches4.pkl')
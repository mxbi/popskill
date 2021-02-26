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
db.build_cache()
exit()

# Users that are not part of CUDGS. Matches will not be considered if they contain any of these users
user_blacklist = ['1123980', '1640115', '1642207', '1640116', '1640119', '1642471', '1640128']

for match in matches:
    m = pf.get_match(match)
    if not (set(m['team1table']['id']).intersection(user_blacklist) or set(m['team2table']['id']).intersection(user_blacklist)):
        print(m)
        print(match)
        # try:
        db.add_match(match, cache=m, ignore_existing=True)
        # except pymongo.errors.DuplicateKeyError:
            # print("Match already added")

matches = [pf.get_match(m) for m in matches]

matches = [m for m in matches if not (set(m['team1table']['id']).intersection(user_blacklist) or set(m['team2table']['id']).intersection(user_blacklist))]

matches2 = "1147887,1148049,1148142,1148643,1148753,1148977,1149021,1149271,1149385,1149579,1149864,1150763,1150957,1151173,1151368,1152187,1153724,1153985,1154745,1154809,1155367,1155962,1156090,1156241,1157377,1157538,1157692,1158437,1158557,1158706,1159212,1159331,1159441,1160100,1160596,1160752,1160848,1161383,1161489,1161597,1162219,1162485,1162674,1162827,1162913,1163384,1163491,1163664,1163808,1163939,1164622,1165115,1165255,1165373,1165481,1166037,1166112,1166175,1166557,1166667,1167334,1167453,1167541,1167589,1167596,1167974,1168110,1168318,1168511,1169255,1169351,1169475,1169666,1170642,1170717,1170786,1171196,1171331,1171428,1171441,1171516,1172103,1172177,1172848,1172921,1172970,1173372,1173577".split(',')
for match in matches2:
    db.add_match(match, ignore_existing=True)

# print(len(matches))
# mlc.save(matches, 'seedmatches4.pkl')

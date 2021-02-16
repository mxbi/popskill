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

# matches = '1146703,1146629,1142428,1142326,1135008,1134907,1094886,1094757,1092480,1088135,1088067,1087975,1142520,1142428,1142326,1133930,1131132,1128002,1125764,1123980,1123292,1123133,1120870,1118333,1109606,1101715,1101607,1094886,1094757,1094696,1092480,1092336,1147353,1147236,1147113,1146703,1146629,1146522,1146408,1144625,1144458,1143208,1143041,1142520,1142428,1142326,1142244,1141099,1140989,1140501,1135008,1134907,1147353,1147236,1147113,1146703,1146629,1146522,1146408,1145704,1145612,1144316,1142244,1141745,1141659,1140989,1140501,1135008,1109606,1101715,1101607,1094886'.split(',')

matches = ['1088135', '1141745', '1088067', '1094696', '1141659', '1147113', '1143041', '1140989', '1141099', '1144316', '1134907', '1142326', '1101715', '1145612', '1092480', '1087975', '1146636', '1101607', '1094886', '1109606', '1146703', '1143208', '1142244', '1145704', '1140501', '1146522', '1144458', '1147353', '1135008', '1094757', '1147236', '1144625', '1146714', '1146408', '1146629', '1142520', '1142428', '1092336']
print(len(matches), 'seed matches')
# user_urls = ['https://popflash.site/user/1611211', 'https://popflash.site/user/1666368', 'https://popflash.site/user/1598215', 'https://popflash.site/user/758084', 'https://popflash.site/user/1660647', 'https://popflash.site/user/718211', 'https://popflash.site/user/210579', 'https://popflash.site/user/158557', 'https://popflash.site/user/1610522', 'https://popflash.site/user/567952', 'https://popflash.site/user/1309768', 'https://popflash.site/user/1610469', 'https://popflash.site/user/1611209']

# users = [pf.get_profile(u) for u in user_urls]
# print(users)

# for u in users:
  # match = u['match_table']
  # match = match[match['DATE'].str.contains('Jan')] # TODO: Fix
  # matches.extend(match['match_link'].values)

matches = [m.split('/')[-1] for m in matches]
matches = set(matches)
print(len(matches))

matches = [pf.get_match(m) for m in matches]

# Users that are not part of CUDGS. Matches will not be considered if they contain any of these users
user_blacklist = ['1123980', '1640115', '1642207', '1640116', '1640119', '1642471', '1640128']
matches = [m for m in matches if not (set(m['team1table']['id']).intersection(user_blacklist) or set(m['team2table']['id']).intersection(user_blacklist))]

print(len(matches))
mlc.save(matches, 'seedmatches4.pkl')
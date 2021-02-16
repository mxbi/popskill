import discord
import requests
import json
import sys
import io

import popflash_match_screenshot

if len(sys.argv) >1 and sys.argv[1] == 'testing':
  print('Running in testing mode')
  SERVER = "http://localhost:7355"
else:
  SERVER = "https://vm.mxbi.net:7355"

client = discord.Client()
#pms = popflash_match_screenshot.PopflashScreenshotter()

@client.event
async def on_ready():
  print("We have logged in as {0.user}".format(client))

@client.event
async def on_message(message):
  if message.author == client.user:
    return

  if message.content.startswith('!register') or message.content.startswith('!pop'):
    print(message)
    match_url = message.content.split(' ')[1]

    resp = requests.post(SERVER + '/submit_match', data=json.dumps({'match_url': match_url}), headers={"Content-Type": "application/json"})
    if resp.status_code != 200:
      print(resp, resp.text)
      await message.channel.send('Failed to process match:' + resp.text[:1000])
      return
    else:
      resp = resp.json()

    embed=discord.Embed(title="Match Report", url="https://pop.robey.xyz", description="10-man played at {}".format(resp['time'][:-34]))
    embed.set_thumbnail(url=resp['image'])
    embed.add_field(name=resp['team1status'], value=resp['team1stats'], inline=True)
    embed.add_field(name=resp['team2status'], value=resp['team2stats'], inline=True)
    await message.channel.send(embed=embed)

  if message.content.startswith('!stats') or message.content.startswith('!pop'):
    print(message)
    match_id = message.content.split(' ')[1].split('/')[-1]
    async with message.channel.typing():
      pms = popflash_match_screenshot.PopflashScreenshotter()
      img = pms.screenshot(match_id)
      pms.close()
      img = discord.File(io.BytesIO(img), 'match_id.png')
      await message.channel.send(file=img)

client.run(open('discord_token.txt', 'r').read().strip())
print('Hello')

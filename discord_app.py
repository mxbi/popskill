import discord
import requests
import json
import sys
import io
import pymongo

import popflash_match_screenshot
import popflash_api as pf

import os
import dotenv
dotenv.load_dotenv()

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

class DBHandler():
  def __init__(self):
    self.client = pymongo.MongoClient(os.getenv("MONGO_URI"))
    self.db = self.client[os.getenv("MONGO_DB")]
    self.users = self.db['user_links']
    self.users.create_index("discord_id", unique=True)

  async def handle_user_registration(self, message: discord.Message):
    user = {"discord_name": message.author.display_name + "#" + message.author.discriminator, "discord_id": message.author.id}
    popflash_id = message.content.split('/')[-1].strip()

    if not popflash_id.isnumeric():
      await message.channel.send("It didn't look like you sent a popflash user link. Send a message in the form 'https://popflash.site/user/1610522'")
      return

    user['popflash_id'] = popflash_id

    profile = pf.get_profile(popflash_id)
    user['steam'] = profile['steam']
    user['v'] = profile['v']
    print(user)

    try:
      self.users.insert_one(user)
    except pymongo.errors.DuplicateKeyError:
      await message.channel.send("Failed: you are already registered :(")
      return

    await message.channel.send("Registered! Thank you")

db = DBHandler()

@client.event
async def on_message(message: discord.Message):
  # print(message.channel, message)
  if message.author == client.user:
    return

  if isinstance(message.channel, discord.channel.DMChannel) and "/user" in message.content:
    await db.handle_user_registration(message)


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

client.run(os.getenv("DISCORD_TOKEN"))
print('Hello')

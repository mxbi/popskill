import asyncio  # util functions
import discord
from discord.ext import commands
import logging  # receives logs from discord.py
from datetime import datetime

logging.basicConfig(level=logging.INFO)

import aiohttp  # for querying api

import io
import popflash_match_screenshot

# for adding users to database
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient
import pymongo.errors

# fetches popflash profiles
import popflash_api as pf

import os
import dotenv
dotenv.load_dotenv()

import sys

if len(sys.argv)>1 and sys.argv[1] == 'testing':
    logging.info('Running in testing mode')
    SERVER = "http://localhost:7355"
else:
    SERVER = "https://vm.mxbi.net:7355"

client = commands.Bot('!')

class DBHandler:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("MONGO_DB")]
        self.users = self.db['user_links']
        self._idx = asyncio.ensure_future(self.users.create_index("discord_id", unique=True))

    @property
    def ready(self):
        return self._idx.done()

db = DBHandler()

@client.listen()
async def on_message(message: discord.Message):
    if not (isinstance(message.channel, discord.DMChannel) and '/user' in message.content):
        return

    assert db.ready

    popflash_id = message.content.split('/')[-1].strip()
    if not popflash_id.isnumeric():
        return await message.channel.send("It didn't look like you sent a popflash user link. Send a message of the form 'https://popflash.site/user/1610522'")

    profile = await asyncio.get_event_loop().run_in_executor(
        None, lambda: pf.get_profile(popflash_id)
    )

    user = {
        'discord_name': str(message.author),
        'discord_id': message.author.id,
        'popflash_id': popflash_id,
        'steam': profile['steam'],
        'register_date': datetime.now(),
        'v': profile['v'],
    }

    logging.info(str(user))

    try:
        await db.users.insert_one(user)
    except pymongo.errors.DuplicateKeyError:
        return await message.channel.send("Failed: you are already registered :(")

    await message.channel.send("Registered! Thank you")

@client.command()
async def register(ctx, match):
    logging.info(ctx.message.content)

    async with aiohttp.ClientSession() as session:
        async with session.post(SERVER+'/submit_match', json={'match_url': match}) as resp:
            if resp.status != 200:
                logging.warning(resp.text)
                return await ctx.send('Failed to process match:' + resp.text[:1000])
            resp = await resp.json()

    print(resp)

    embed = discord.Embed(
        title='Match Report',
        url='https://pop.robey.xyz',
        description='10-man played at {}'.format(resp['time']),
    ).set_thumbnail(url=resp['image']) \
     .add_field(name=resp['team1status'], value=resp['team1stats']) \
     .add_field(name=resp['team2status'], value=resp['team2stats'])

    await ctx.send(embed=embed)

@client.command()
async def stats(ctx, match):
    logging.info(ctx.message.content)

    def screenshot():
        pms = popflash_match_screenshot.PopflashScreenshotter()
        img = pms.screenshot(match.split('/')[-1])
        pms.close()
        return discord.File(io.BytesIO(img), 'match_stats.png')

    async with ctx.typing():
        file = await asyncio.get_event_loop().run_in_executor(None, screenshot)

    await ctx.send(file=file)

@client.command()
async def pop(ctx, match):
    asyncio.ensure_future(ctx.invoke(register, match))
    asyncio.ensure_future(ctx.invoke(stats, match))

client.run(os.getenv("DISCORD_TOKEN"))

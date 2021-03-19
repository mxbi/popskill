import asyncio  # util functions
from typing import Optional

import discord
from discord.ext import commands
import logging  # receives logs from discord.py
from datetime import datetime

from steam import steamid

logging.basicConfig(level=logging.INFO)

import aiohttp  # for querying api

import io

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
    SERVER = "https://api.sandb.ga"

client = commands.Bot(commands.when_mentioned_or('!'))

@client.event
async def on_command_error(ctx, error):
    emb = discord.Embed(
        colour=discord.Colour.red(),
        title=str(type(error)),
        description=str(getattr(error, 'original', error))
    )

    await ctx.send(embed=emb)

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
        'steam_id': int(steamid.steam64_from_url(profile["steam_profile"])),
        'register_date': datetime.now(),
        'v': profile['v'],
    }

    logging.info(str(user))

    try:
        await db.users.insert_one(user)
    except pymongo.errors.DuplicateKeyError:
        return await message.channel.send("You are already registered :)")

    await message.channel.send("Registered! Thank you")

@client.command()
async def register(ctx, match):
    "Add a match to the database and show the resulting Elo changes."
    logging.info(ctx.message.content)

    async with aiohttp.ClientSession() as session:
        async with session.post(SERVER+'/submit_match', json={'match_url': match}) as resp:
            if resp.status != 200:
                logging.warning(await resp.text())
                return await ctx.send('Failed to process match: ' + (await resp.text())[:1000])
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
    "Show the popflash statistics for a match."
    logging.info(ctx.message.content)

    match_url = "https://popflash.site/match/" + match.split('/')[-1]

    image_command = ["wkhtmltoimage",
                     "-f", "png",
                     "--width", "990",
                     "--disable-smart-width",
                     "--crop-h", "1106",
                     "--crop-w", "990",
                     "--crop-x", "0",
                     "--crop-y", "142",
                     "--cookie", "connect.sid", os.getenv('POPFLASH_SID'),
                     match_url, "-"]

    process = await asyncio.create_subprocess_exec(*image_command,
                                                   stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    await ctx.send(file=discord.File(io.BytesIO(stdout), 'match_stats.png'))

@client.command()
async def pop(ctx, match):
    "Equivalent to !register + !stats"
    asyncio.ensure_future(ctx.invoke(register, match))
    asyncio.ensure_future(ctx.invoke(stats, match))

@client.command()
async def balance(ctx, chan: Optional[discord.VoiceChannel] = None, *players: discord.User):
    if chan:
        players = [u for u in chan.members if u not in players]

    users = [
        u['popflash_id'] for u in await db.users.find(
            {'discord_id': {'$in': [p.id for p in players]}},
            projection=['discord_id', 'popflash_id']
        ).to_list(None)
    ]

    if len(users) < len(players):
        asyncio.ensure_future(ctx.send("Some players don't have popflash."))

    async with aiohttp.ClientSession() as session:
        async with session.post(
                    SERVER+'/v2/balance',
                    json={'team1': [str(u) for u in users], 'team2':[]}
                ) as resp:
            data = await resp.json()

    emb = discord.Embed()
    emb.add_field(name=f"Team 1 ({data['t1rating']})", value=data['team1'])
    emb.add_field(name=f"Team 2 ({data['t2rating']})", value=data['team2'])

    await ctx.send(embed=emb)



client.run(os.getenv("DISCORD_TOKEN"))

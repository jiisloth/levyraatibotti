# This example requires the 'message_content' intent.
import random

import discord
from discord.ext import commands
from datetime import datetime, timedelta

import configparser
import os
from tinytag import TinyTag



configReader = configparser.ConfigParser()
configReader.read('config.ini')

config = configReader['LEVYRAATI']
if not config:
    print('Please give config')
    quit()

description = '''Another nice bot by a sloth'''

token = config['BOT_TOKEN']
text_channel = config['BOT_TEXT_CHANNEL']
voice_channel = config['BOT_VOICE_CHANNEL']
music_dir = config['MUSIC_DIRECTORY']

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='/', description=description, intents=intents)

running_run_id = 123
randseed = str(random.randint(1, 99999999))

admins = [] #Add admin id's here
songnumber = -1
songmessageid = 0
current_reacts = []

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


@bot.command()
async def start(ctx):
    if ctx.author.id in admins:
        if str(ctx.channel) == text_channel or text_channel == "":
            """Joins a voice channel"""
            vc = discord.utils.get(ctx.guild.voice_channels, name=voice_channel)
            if ctx.voice_client is not None:
                return await ctx.voice_client.move_to(vc)
            await vc.connect()


@bot.command()
async def next(ctx):
    global songnumber
    global music
    global songmessageid
    global current_reacts
    if ctx.author.id in admins:
        if str(ctx.channel) == text_channel or text_channel == "":
            """Plays a file from the local filesystem"""
            if songnumber >= 0:
                write_song_reacts()
                current_reacts = []
            songnumber += 1
            if songnumber > len(music):
                await ctx.send(f'All songs played! Going again!')
                songnumber = 0
                random.shuffle(music)
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            song = music[songnumber]
            file = music_dir + "/" + song["Path"] + "/" + song["Filename"]
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(file))
            ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
            ctx.voice_client.source.volume = 15 / 100
            msg = song["Filename"]
            if song["Artist"]:
                msg = f'{song["Name"]} by {song["Artist"]}, ({timedelta(seconds=int(song["Duration"]))})'
            sentmsg = await ctx.send(f'{songnumber+1}/{len(music)} Now playing: {msg}')
            songmessageid = sentmsg.id


def write_song_reacts():
    song = music[songnumber]
    reacts = ", ".join(current_reacts)
    if song["Artist"]:
        line = f'{song["Artist"]}, {song["Name"]}, {timedelta(seconds=int(song["Duration"]))},  {song["Path"]},  {song["Filename"]}, [{reacts}]\n'
    else:
        line = f'-, -, -,  {song["Path"]},  {song["Filename"]}, [{reacts}]\n'
    with open("results.txt", "a") as f:
        f.write(line)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    global current_reacts
    """Gives a role based on a reaction emoji."""
    # Make sure that the message the user is reacting to is the one we care about.
    if payload.message_id != songmessageid:
        return
    current_reacts.append(payload.emoji.name)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Removes a role based on a reaction emoji."""
    # Make sure that the message the user is reacting to is the one we care about.
    if payload.message_id != songmessageid:
        return
    current_reacts.remove(payload.emoji.name)


def get_music_files(root):
    songs = []
    for path, subdirs, files in os.walk(root):
        for name in files:
            file = os.path.join(path, name)
            f = {"Artist": None, "Name": None, "Duration": None, "Path": path[len(root)+1:], "Filename": name}
            try:
                tag = TinyTag.get(file)
                f["Artist"] = tag.artist
                f["Name"] = tag.title
                f["Duration"] = tag.duration
            except UnicodeDecodeError:
                print(f'{file} sucks ass.')
            songs.append(f)
    random.shuffle(songs)
    return songs

music = get_music_files(music_dir)


bot.run(token)

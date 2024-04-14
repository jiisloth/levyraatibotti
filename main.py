# This example requires the 'message_content' intent.
import random
import time

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

token = config['BOT TOKEN']
bot_channel = config['BOT CHANNEL']
music_dir = config['MUSIC DIRECTORY']


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='/', description=description, intents=intents)


randseed = 0
startfrom = 1
admins = []
playmode = 0
anarchylevel = 0
songinfo = 0
volume = 15

at_channel = None
songnumber = 0
songmessageid = -1

current_reacts = []
music = []

paused = True
cctx = None
can_vote = False
next_at = None
paused_at = None

reaction_commands = {
    "next": "⏭️",
    "back": "⏮️",
    "pause": "⏸️",
    "play": "▶️",
    "manualplay": "⏯️",
    "autoplay": "🔁",
    "autoplay_min": "🔂"
}


def init(getmusic=False):
    global randseed
    global startfrom
    global admins
    global playmode
    global songnumber
    global anarchylevel
    global songinfo
    global config
    global music
    global songmessageid
    global volume
    global next_at
    global can_vote
    global paused
    paused = True
    can_vote = False
    next_at = None
    if getmusic:
        music = get_music_files(music_dir)
    configReader.read('config.ini')
    config = configReader['LEVYRAATI']
    volume = get_int_conf('VOLUME', 15)
    randseed = get_int_conf('RANDOM SEED')
    startfrom = get_int_conf('START FROM', 1)
    playmode = get_int_conf('PLAY MODE')
    songinfo = get_int_conf('SONG INFO')
    anarchylevel = get_int_conf('ANARCHY MODE')
    admins = get_int_conf('ADMIN ID', 0, True)
    songnumber = startfrom - 1
    songmessageid = -1


def get_int_conf(conf, default=0, is_list=False):
    value = config[conf]
    if is_list:
        val_list = []
        for a in value.split("\n"):
            if a == "":
                continue
            if a.isdigit():
                val_list.append(int(a))
            else:
                print(f'{conf} values must be valid integers')
        return val_list
    else:
        if value.isdigit():
            return int(value)
        else:
            print(f'{conf} must be valid integer')
            return default


@bot.event
async def on_ready():
    global cctx
    global next_at
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    while True:
        await discord.utils.sleep_until(datetime.now() + timedelta(seconds=1))
        if playmode > 0 and next_at and cctx and not paused:
            if datetime.now() >= next_at:
                await do_next(cctx, 1)


@bot.command()
async def join(ctx):
    global cctx
    global songnumber
    global at_channel
    if ctx.author.id in admins:
        if str(ctx.channel) == bot_channel or bot_channel == "":
            at_channel = str(ctx.channel)
            """Joins a voice channel"""
            init()
            vc = discord.utils.get(ctx.guild.voice_channels, name=bot_channel)
            if ctx.voice_client is not None:
                await ctx.voice_client.move_to(vc)
            else:
                await vc.connect()
            cctx = ctx

@bot.command()
async def start(ctx):
    global cctx
    global songnumber
    if ctx.author.id in admins:
        if str(ctx.channel) == at_channel:
            cctx = ctx
            with open("results.txt", "a", encoding='utf-8') as f:
                f.write(f'#### Started at: {datetime.now()} #####')
            await play_song(ctx)


@bot.command()
async def reload(ctx):
    global cctx
    global songnumber
    if ctx.author.id in admins:
        if str(ctx.channel) == at_channel:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            init(True)


@bot.command()
async def next(ctx):
    if ctx.author.id in admins:
        if str(ctx.channel) == at_channel:
            await do_next(ctx, 1)


@bot.command()
async def back(ctx):
    if ctx.author.id in admins:
        if str(ctx.channel) == at_channel:
            await do_next(ctx, -1)


def write_song_reacts():
    global current_reacts
    if songmessageid < 0:
        return
    song = music[songnumber]
    reacts = ", ".join(current_reacts)
    line = f'{song["Artist"]}, {song["Name"]}, {timedelta(seconds=int(song["Duration"]))},  {song["Path"]},  {song["Filename"]}, [{reacts}]\n'
    with open("results.txt", "a", encoding='utf-8') as f:
        f.write(line)

    current_reacts = []


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    global cctx
    global current_reacts
    global playmode
    global paused
    global paused_at
    global next_at
    """Gives a role based on a reaction emoji."""
    # Make sure that the message the user is reacting to is the one we care about.
    if payload.message_id != songmessageid:
        return

    if payload.user_id in admins or anarchylevel > 0:
        command = get_admin_reaction_command(payload.emoji.name)
        if command:
            if command == "next":
                await do_next(cctx, 1)
                return
    if payload.user_id in admins or anarchylevel > 1:
        command = get_admin_reaction_command(payload.emoji.name)
        if command:
            if command == "next":
                await do_next(cctx, 1)
            if command == "back":
                await do_next(cctx, -1)
            if command == "pause":
                if not paused:
                    paused = True
                    paused_at = datetime.now()
                    cctx.voice_client.pause()
            if command == "play":
                if paused:
                    paused = False
                    pausedfor = datetime.now() - paused_at
                    if can_vote:
                        cctx.voice_client.resume()
                        if next_at:
                            next_at += pausedfor
                    else:
                        play_song(cctx)
            if command == "manualplay":
                playmode = 0
                next_at = None
                await cctx.send(f'Manual next only')
            if command == "autoplay":
                playmode = 1
                await cctx.send(f'Autonext will start on next song..')
            if command == "autoplay_min":
                playmode = 2
                await cctx.send(f'Autonext will start on next song..')
            return
    if can_vote:
        current_reacts.append(payload.emoji.name)

@bot.event
async def stop(ctx):
    global at_channel
    global songmessageid
    global next_at
    next_at = None
    if ctx.author.id in admins:
        if str(ctx.channel) == bot_channel or bot_channel == "":
            write_song_reacts()
            at_channel = None
            next_at = None
            songmessageid = -1
            await ctx.voice_client.disconnect()
@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Removes a role based on a reaction emoji."""
    # Make sure that the message the user is reacting to is the one we care about.
    if payload.message_id != songmessageid:
        return
    if payload.user_id in admins or anarchylevel > 0:
        command = get_admin_reaction_command(payload.emoji.name)
        if command:
            if command == "next":
                return
    if payload.user_id in admins or anarchylevel > 1:
        command = get_admin_reaction_command(payload.emoji.name)
        if command:
            return
    if can_vote and payload.emoji.name in current_reacts:
        current_reacts.remove(payload.emoji.name)


def get_admin_reaction_command(emoji):
    for k in reaction_commands.keys():
        if reaction_commands[k] == emoji:
            return k
    return False

async def do_next(ctx, move):
    global songnumber
    global music
    global songmessageid
    global randseed
    global can_vote
    global next_at
    next_at = None
    can_vote = False
    write_song_reacts()
    songnumber += move
    if songnumber >= len(music):
        await ctx.send(f'All songs played! Resuffling and starting again')
        songnumber = 0
        randseed += 1
        random.Random(randseed).shuffle(music)
    if songnumber < 0:
        await ctx.send(f'Looped backwards! Going back to the previous round.')
        songnumber = len(music)-1
        randseed -= 1
        random.Random(randseed).shuffle(music)

    if paused:
        sentmsg = await ctx.send(f'{songnumber + 1}/{len(music)} (Paused)')
        songmessageid = sentmsg.id
    else:
        await play_song(ctx)


async def play_song(ctx):
    global songnumber
    global music
    global songmessageid
    global randseed
    global current_reacts
    global cctx
    global paused
    global can_vote
    global next_at
    can_vote = True
    paused = False
    write_song_reacts()

    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    print("hello?")
    print(songnumber)
    song = music[songnumber]
    file = music_dir + "/" + song["Path"] + "/" + song["Filename"]
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(file))
    ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
    ctx.voice_client.source.volume = volume / 100

    msg = f'{song["Name"]} by {song["Artist"]}, {timedelta(seconds=int(song["Duration"]))}, {song["Filename"]}'
    if playmode == 2:
        next_at = datetime.now() + timedelta(seconds=60)
    if playmode == 1 and int(song["Duration"]) > 0:
        next_at = datetime.now() + timedelta(seconds=int(song["Duration"]))
    if songinfo >= 0:
        print(f'{songnumber + 1}/{len(music)} Now playing: {msg}')
    if songinfo >= 1:
        sentmsg = await ctx.send(f'{songnumber + 1}/{len(music)} Now playing: {msg} \nReagoi nopee!')
        songmessageid = sentmsg.id
    else:
        sentmsg = await ctx.send(f'{songnumber + 1}/{len(music)} Äänestä reagoimalla!')
        songmessageid = sentmsg.id
    cctx = ctx


def get_music_files(root):
    songs = []
    count = 0
    for path, subdirs, files in os.walk(root):
        for name in files:
            file = os.path.join(path, name)
            f = {"Artist": None, "Name": "", "Duration": 0, "Path": path[len(root)+1:], "Filename": name}
            try:
                tag = TinyTag.get(file)
                f["Artist"] = tag.artist
                f["Name"] = tag.title
                f["Duration"] = tag.duration
            except UnicodeDecodeError:
                print(f'{file} sucks ass.')
            songs.append(f)
            if not f["Artist"]:
                f["Artist"] = "Not Found"
            if not f["Name"]:
                f["Name"] = "Not Found"
            if not f["Duration"]:
                f["Duration"] = 0
            msg = f'{f["Name"]} by {f["Artist"]}, {timedelta(seconds=int(f["Duration"]))}, {f["Filename"]}'
            print(f'{count+1} Found: {msg}')
            count += 1

    random.Random(randseed).shuffle(songs)
    return songs


init(True)
bot.run(token)

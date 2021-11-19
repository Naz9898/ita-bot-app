import os
import keep_alive
import discord
import logging
import asyncio
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from game import Game

TOKEN = os.environ['TOKEN']
prefix = "ita!"
client = commands.Bot(command_prefix=prefix)
client.remove_command("help")
games = {}
waiting_task = {}


async def answer_time_task(time):
    await asyncio.sleep(time)


def createEmbed(text, description, ranking=None):
    embed = discord.Embed(title=text,
                          description=description,
                          colour=discord.Colour.blue())

    if ranking is not None:
        embed.add_field(name='\u200b',
                        value="**Current scores:**",
                        inline=False)
        if len(ranking) == 0:
            embed.add_field(name="No one answered",
                            value='\u200b',
                            inline=False)
        else:
            for key, value in ranking.items():
                embed.add_field(name="@" + key,
                                value=str(value) + " points",
                                inline=False)
        embed.set_footer(text="You can skip the question sending \"s\"")

    return embed


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    global games, waiting_task
    if message.author == client.user:
        return
    #Not a command
    if not message.content.startswith(prefix):
        channel = message.channel.id
        #Game is on
        if channel in games and games[channel].game_on:
            if message.content == "s":
                waiting_task[channel].cancel()
            else:
                games[channel].submit(message.content.lower(),
                                      message.author.name)
                if len(games[channel].current_correct) > 0 and games[
                        channel].current_correct[0] == message.author.name:
                    waiting_task[channel].cancel()
                    waiting_task[channel] = asyncio.create_task(
                        answer_time_task(2))
                    try:
                        await waiting_task[channel]
                    except asyncio.CancelledError:
                        print("Waiting stopped")

    await client.process_commands(message)


@client.command()
async def help(ctx):
    embed = discord.Embed(title="Help ItaBot",
                          description="Commands",
                          colour=discord.Colour.blue())

    embed.add_field(name=prefix + "l",
                    value="Start listening game",
                    inline=False)
    embed.add_field(name=prefix + "q",
                    value="Start image guessing game",
                    inline=False)
    embed.add_field(name=prefix + "stop", value="Stop game", inline=False)
    embed.add_field(name=prefix + "t <word>",
                    value="Find english translation of word",
                    inline=False)
    await ctx.send(embed=embed)
    pass


@client.command(pass_context=True)
async def q(ctx):
    await start(ctx, False)
    pass


@client.command(pass_context=True)
async def l(ctx):
    await start(ctx, True)
    pass


async def start(ctx, listening_game=True):
    global games, waiting_task
    channel = ctx.channel.id

    #Check if is possible to start a game
    if not channel in games or games[channel].game_on is False:
        #Check if bot is already in voice call in same server (bot can only run a single voice call per server)
        if listening_game:
            if ctx.guild.voice_client in client.voice_clients:
                await ctx.send("A listening game is already on!")
                return
            #Connect to voice call if author is in one
            if ctx.author.voice is not None:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You must join a voice channel first!")
                return

        #Create game
        games[channel] = Game(listening_game)
        print("Creating new game!")
        await ctx.send("Game started!")
        while games[channel].game_on:
            games[channel].setupQuestion()
            #Show question
            if listening_game:
                source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(games[channel].current_file))
                ctx.voice_client.play(
                    source,
                    after=lambda e: print('Player error: %s' % e)
                    if e else None)
            else:
                file = discord.File(games[channel].current_file)
                embed = discord.Embed()
                embed.set_image(url="attachment://output.png")
                embed.add_field(name="Guess the word in italian!",
                                value='\u200b',
                                inline=False)
                embed.set_footer(
                    text="You can skip the question sending \"s\"")

                await ctx.send(file=file, embed=embed)
            #Wait for answers
            waiting_task[channel] = asyncio.create_task(answer_time_task(10))
            try:
                await waiting_task[channel]
            except asyncio.CancelledError:
                print("Waiting stopped")
            #If someone got it riight wait a couple of seconds
            if len(games[channel].current_correct) > 0:
                try:
                    await waiting_task[channel]
                except asyncio.CancelledError:
                    print("Waiting stopped")
            #Show question results
            title_string = "**Listening quiz**" if listening_game else "**Image guessing quiz**"
            answer_string = "Correct answer: _" + games[
                channel].current_answer + "_"
            if len(games[channel].current_correct) > 0:
                answer_string = answer_string + "\n**@" + games[
                    channel].current_correct[0] + "** got it first!"

            embed = createEmbed(title_string, answer_string,
                                games[channel].ranking)
            await ctx.send(embed=embed)

            if games[channel].game_on:
                games[channel].endQuestion()
                #Wait a couple of seconds before next question
                waiting_task[channel] = asyncio.create_task(
                    answer_time_task(3))
                try:
                    await waiting_task[channel]
                except asyncio.CancelledError:
                    print("Waiting 2 stopped ")

        if listening_game and ctx.guild.voice_client in client.voice_clients:
            await ctx.voice_client.disconnect()
        #await ctx.send("The game is over")
        embed = createEmbed(title_string, "Final scores:",
                            games[channel].ranking)
        await ctx.send(embed=embed)
        games.pop(channel, None)

    else:
        await ctx.send("The game is already on!")

    pass


@client.command(pass_context=True)
async def stop(ctx):
    global games, waiting_task
    channel = ctx.channel.id
    if channel in games and games[channel].game_on:
        if waiting_task[
                channel] is not None and not waiting_task[channel].done():
            waiting_task[channel].cancel()
            waiting_task.pop(channel, None)
        games[channel].stop()
        await ctx.send("Game stopped!")
    else:
        await ctx.send("Nothing to stop!")
    pass


@client.command(pass_context=True)
async def t(ctx, *args):

    word = '-'.join(args)
    print("Check meaning of  ", word)

    html = requests.get("https://www.wordreference.com/iten/" + word)
    result_list = []
    parsed_html = BeautifulSoup(html.text, 'html.parser')
    table = parsed_html.body.find('table', attrs={'class': 'WRD'})
    if table is None:
        print("I didn't find anything :(")
        result_list.append(None)
    else:
        for row in table.select('tr', attrs={'class': 'even'}):
            if row.has_attr('id'):

                from_wrd = row.find('td', attrs={'class': 'FrWrd'})
                for s in from_wrd.select('span'):
                    s.extract()
                def_wrd = row.find('td', attrs=None)
                to_wrd = row.find('td', attrs={'class': 'ToWrd'})
                for s in to_wrd.select('span'):
                    s.extract()

                current_def = []
                current_def.append(from_wrd.text)
                #current_def.append(def_wrd.text if def_wrd.text else '\u200b')
                current_def.append(def_wrd.text)
                current_def.append(to_wrd.text.strip())
                result_list.append(current_def)

                #print(from_wrd.text)
                #print(def_wrd.text)
                #print(to_wrd.text)
                #print("\n")
    if result_list[0] is None:
        embed = discord.Embed(title="I didn't find anything :(")
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title=' '.join(args), value='\u200b')
    for res in result_list:
        embed.add_field(name="Italiano", value=res[0]+res[1], inline=True)
        #embed.add_field(name='\u200b', value=res[1], inline=True)
        embed.add_field(name="English", value=res[2], inline=True)

    await ctx.send(embed=embed)
    pass


keep_alive.keep_alive()
client.run(TOKEN) 
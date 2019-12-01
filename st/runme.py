import logging
import time

import discord
from jishaku import help_command
now = time.time()

from discord.ext import commands

bot = commands.Bot(command_prefix=commands.when_mentioned_or('st ', 'St ', 'S.', 's.', 'supertool, please '),
				help_command=help_command.MinimalEmbedPaginatorHelp(dm_help_threshold=1024, dm_help=None),
				heartbeat_timeout=15, owner_ids=[421698654189912064, 317731855317336067],  # Put your ID in that list.
				activity=discord.Game(name="booting."), status=discord.Status.idle)
bot.startup = now

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='./data/debug.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

bot.cogged = [
	'jishaku',
	'cogs.owner',
	'cogs.mod',
	'cogs.error_handler',
	'cogs.config',
	'cogs.core',
	'cogs.guildexclusives',
	'cogs.verify',
	'cogs.eventlog',
	'cogs.messageinfo',
	'cogs.feeds'
]
bot.cogged = sorted(bot.cogged, key=lambda a: a, reverse=False)
bot.cool_people = [344878404991975427, 421698654189912064]
bot.reboots = -1


@bot.command()
async def cogs(ctx):
	"""Lists loaded cogs (modules)"""
	_cogs = bot.extensions
	p = commands.Paginator(prefix='```diff')
	for cog in bot.cogged:
		if cog in _cogs.keys():
			p.add_line(f"+ {cog.replace('cogs.', '')}\n")
		else:
			p.add_line(f"- {cog.replace('cogs.', '')}\n")
	for page in p.pages:
		await ctx.send(page)


@bot.event
async def on_ready():
	bot.ready_at = time.time()
	bot.reboots += 1
	guilds = len(bot.guilds)
	users = len(bot.users)
	latency = round(bot.latency*1000, 2)
	print(f"Booted up with {guilds} guilds, {users} users and {latency}ms ping.")
	loaded = 0
	print("Loading systems...")
	print(f"Initialising cogs [{loaded}/{len(bot.cogged)}]")
	for cog in bot.cogged:
		try:
			bot.load_extension(cog)
			loaded += 1
			print(f"Initialising cogs [{loaded}/{len(bot.cogged)}]{'.'*loaded}")
		except (commands.ExtensionNotLoaded, Exception):
			continue
	print("Changing status...")
	await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="discord go by."),
							status=discord.Status.online)
	print("Finished loading systems.")


bot.run('[REMOVED]')

import discord
import asyncio
import typing
import emoji as _emoji
import json
import time
import datetime
import re  # for `choose` command.
import random
import traceback

from discord.ext import commands, tasks
from discord import utils

from cogs.owner import DynamicGuild
from utils.checks import is_premium, is_super_premium
from utils.converters import fix_time, ago_time


class FuzzyRole(commands.Converter):
	async def convert(self, ctx, argument) -> discord.Role:
		try:
			argument = int(argument)
		except:
			pass
		if isinstance(argument, discord.Role):
			return argument
		elif isinstance(argument, int):
			role = ctx.guild.get_role(argument)
			if role is None:  # search all guilds, is faster then it looks
				for guild in ctx.bot.guilds:
					role = guild.get_role(argument)
					if role:
						return role
					else:
						continue
				else:
					raise commands.BadArgument(f"Unable to convert \"{argument}\" to role (from any guild).")
			else:
				return role
		elif isinstance(argument, str):
			for role in ctx.guild.roles:
				if role.name == argument:
					return role
				elif role.name.lower() == argument:
					return role
				elif role.name.startswith(argument):
					return role
				elif argument in role.name.lower():
					return role
			else:
				raise commands.BadArgument(f"Unable to convert string \"{argument}\" to role.")
		else:
			raise commands.BadArgument(f"Unable to convert type {type(argument)} to role: unsupported type.")

class Flag:
	def __init__(self, flag: str):
		self.flag = flag

	@property
	def age(self):
		return self.flag == 'age'

	@property
	def name_len(self):
		return self.flag == 'name-length'

	@property
	def name_length(self):
		return self.flag == 'name-length'

	@property
	def name_abc(self):
		return self.flag == 'name-age'
	@property
	def id(self):
		return self.flag == 'id'

	def __str__(self):
		return self.flag

class SortedFlagConverter(commands.Converter):
	async def convert(self, ctx, argument):
		argument = str(argument).lower()
		if argument == 'age':
			return Flag(argument)
		elif argument == 'name-abc':
			return Flag(argument)
		elif argument == 'name-length':
			return Flag(argument)
		elif argument == 'id':
			return Flag(argument)
		else:
			raise commands.BadArgument("flag \"{argument}\" not a valid flag\nValid Flags: 'age', 'name-abc', 'name-length', 'id'")


class Core(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.emojis = {
			"toggles": {"on": str(bot.get_emoji(616068601476022283)), "off": ' <:off:616068601375358987>'},
			"wumpus": '<:dds_wumpus:616073315844358225>',
			'invite': '<:invite_white:616075493082529846>',
			'verified': '<:dds_verified:616073827180478466>',
			'partner': '<:dds_partner:616073613157728276>',
			'search': '<:dds_search:616074439368638475>',
			'animated_icon': '<a:dwumpus:616077357496926209>',
			'lurk': '<:dds_lurk:616075914597498988>',

		}
		self.aping = []

	async def get_guild_info(self, guild: discord.Guild):
		"""Get a guild's info and return a fully formatted, ready-made embed fields list.

		returns: [{'name': *name*, 'value': *value*}]"""

		member_info = ""
		bots = 0
		humans = 0
		admins = 0
		total_member_count = guild.member_count
		for member in guild.members:
			if member.bot:
				bots += 1
				continue
			else:
				humans += 1
				if member.guild_permissions.administrator:
					admins += 1
		member_info += f"{total_member_count} total, {bots} bots, {humans} humans ({admins} admins)"

		us = '🇺🇸'
		regions = {
			# these look like weird font letters, but they are actually the flag emojis (when sent in discord).
			'amsterdam': '🇳🇱',
			'brazil': '🇧🇷',
			'eu_central': '🇪🇺',
			'eu_west': '🇪🇺',
			'frankfurt': '🇩🇪',
			'hongkong': '🇨🇳',
			'india': '🇮🇳',
			'japan': '🇯🇵',
			'london': '🇬🇧',
			'russia': '🇷🇺',
			'singapore': '🇸🇬',
			'southafrica': '🇿🇦',
			'sydney': '🇦🇺',
			'us_central': us,
			'us_east': us,
			'us_south': us,
			'us_west': us
		}
		features_dict = {
			"VIP_REGIONS": f'\U00002b50{str(guild.region).lower().replace("-", "_")}',
			"COMMERCE": '\U0001f6d2',
			'NEWS': '\U0001f4f0',
			'BANNER': '\U0001f3f3',
			'ANIMATED_ICON': '',
			'DISCOVERABLE': self.emojis['search'],
			'LURKABLE': self.emojis['lurk'],
			'MORE_EMOJI': '\U00002795\U0001f604',
			'PARTNERED': self.emojis['partner'],
			'VERIFIED': self.emojis['verified'],
			'INVITE_SPLASH': f'{self.emojis["invite"]}\U0001f3f3',
			'VANITY_URL': self.emojis['invite']
		}
		features = guild.features
		fs = ""
		for f in features:
			fs += f"{features_dict[str(f)]} {str(f).lower().replace('_', ' ')}\n"
		region = f"{regions[str(guild.region).lower().replace('-', '_')]} {str(guild.region)}"
		verif = str(guild.verification_level).replace('_', ' ')
		notif = str(guild.default_notifications).replace('_', ' ').replace('NotificationLevel.', ' ')
		filter = str(guild.explicit_content_filter).replace('_', ' ')

		system_channel = '#'+str(guild.system_channel) if guild.system_channel else None
		system_channel_flags = []
		for flag, value in guild.system_channel_flags:
			system_channel_flags.append((str(flag).replace('_', ' '), self.emojis['toggles']['on'] if value else self.emojis['toggles']['off']))
		system_channel_flags = ' | '.join([f"{x}: {y}" for x, y in system_channel_flags])

		emojis = len(guild.emojis)

		afk_channel = guild.afk_channel
		afk_timeout = fix_time(guild.afk_timeout)

		icon = str(guild.icon_url_as(static_format='png')) if guild.icon_url else None

		nitro_level = f"Nitro Level: {guild.premium_tier}"
		nitro_subs = f"Boosters: {guild.premium_subscription_count}"

		voice = len(guild.voice_channels)
		text = len(guild.text_channels)
		cat = len(guild.categories)
		ci = f"<:category:614652379278606376> {cat} categories\n <:text_channel:614652616403845120>{text} text channels" \
			f"\n<:voice_channel:614652616437268636> {voice} voice channels"
		created = ago_time(guild.created_at)
		stuff = []
		stuff.append({"name": "member info", "value": member_info})
		stuff.append({"name": "channel info", "value": ci})
		stuff.append({"name": "region", "value": region})
		stuff.append({"name": "verification level", "value": verif})
		stuff.append({"name": "notification level", "value": notif})
		stuff.append({"name": "filter level", "value": filter})
		stuff.append({"name": "system channel", "value": f"{system_channel}\nSystem channel flags: {system_channel_flags}"})
		stuff.append({"name": "emojis", "value": emojis})
		stuff.append({"name": "afk info", "value": f"Channel: {afk_channel.mention if afk_channel else None}\nTimeout: {afk_timeout}"})
		stuff.append({"name": "nitro boost info", "value": f"{nitro_level}\n{nitro_subs}"})
		stuff.append({"name": "created", "value": created})
		stuff.append({"name": "icon url", "value": icon})
		return stuff

	@commands.command()
	async def serverinfo(self, ctx, *, guild: DynamicGuild() = None): # Commented & partially rewritten by Minion3665
		"""Get a server's information

		Provide a server id/name after the command to get their information."""
		if not guild: # If the guild wasn't supplied
			guild = ctx.guild # Get the current guild as the guild instead

		async with ctx.channel.typing(): # Show the typing status until I have sent the serverinfo
			fields_list = await self.get_guild_info(guild) # Get the guild information
			if len(fields_list) > 25: # If the embed length is too long
				return await ctx.send(f"Unable to display data with reason: ListTooLong "
									  f"(data received was larger then the discord embed field limit.)") # If data is too long, return with an error message (TODO: Make it send anyway later)
			embed = discord.Embed(title=guild.name, description=str(guild.id), color=guild.owner.color, timestamp=guild.created_at) # Create an embed
			for field in fields_list: # Enumerate over the pieces of server information
				embed.add_field(name=field['name'], value=field['value'], inline=False) # Add a field displaying a piece of server information
				if field['name'] == 'icon url' and field['value']: # If the current field is the icon URL (and it actually exists (i.e. isn't None))
					embed.set_thumbnail(url=str(field['value'])) # Set the thumbnail to the server icon
		return await ctx.send(embed=embed) # Send the embed

	@commands.command(enabled=True, aliases=['ui', 'u', 'user', 'whois'])
	@commands.guild_only()
	@commands.bot_has_permissions(embed_links=True)
	async def userinfo(self, ctx, *, user: typing.Union[discord.Member, discord.User] = None):
		"""get someones information."""
		user = user if user else ctx.author
		e = discord.Embed(title=f"{user.display_name}'s information:", description=f"ID: {user.id}", color=(
											user.color if isinstance(user, discord.Member) else discord.Color.blue()),
						timestamp=user.created_at)
		e.add_field(name="User avatar url:", value=str(user.avatar_url_as(static_format='png')), inline=True)
		created_at, ago_at = user.created_at.strftime('%A the %d of %b, %Y UTC'), ago_time(user.created_at)
		e.add_field(name="Account created:", value=f"{created_at} ({ago_at})", inline=False)
		with open('./data/names.json', 'r') as nf:
			data = json.load(nf)
			if str(user.id) in data.keys():
				e.add_field(name=f"Past names ({len(data[str(user.id)])}):", value=f"`{'`, `'.join(data[str(user.id)])}`")
		if isinstance(user, discord.Member):
			roles = [r.name for r in user.roles if not r.name.lower().startswith('@everyone')]
			joined_at, ago__at = user.joined_at.strftime('%A the %d of %b, %Y UTC'), ago_time(user.joined_at)
			e.add_field(name="Joined at:", value=f"{joined_at} ({ago__at})")
			e.add_field(name=f"Roles ({len(roles)}):", value=str(', '.join(roles))[:1024])
		e.set_thumbnail(url=str(user.avatar_url_as(static_format='png')))
		e.set_footer(text="this command is a work in progress and not everything is shown.")
		return await ctx.send(embed=e)

	@commands.command(aliases=['ri'])
	@commands.bot_has_permissions(embed_links=True)
	async def roleinfo(self, ctx, *, role: typing.Union[discord.Role, FuzzyRole]):
		"""Get information on a role."""
		e = discord.Embed(
			title=f"Name: {role.name}",
			description=f"ID: `{role.id}`\nHoisted: {role.hoist}\nMentionable: {role.mentionable}\nColour: {role.color}"
						f"\nMembers: {len(role.members)}\nCreated: {ago_time(role.created_at)}",
			color=role.color,
			timestamp=role.created_at
		)
		if role.guild != ctx.guild:
			e.description += f"\nGuild: {role.guild.name}"
		return await ctx.send(embed=e)

	@commands.command(name='inrole', aliases=['ir, rolein', 'rolemembers', 'rm'])
	@commands.bot_has_permissions(embed_links=True, manage_roles=True)
	async def in_role(self, ctx, *, role: FuzzyRole()):
		"""Get the members in a role. displays first 15 if there are more then 30 members"""
		if len(role.members) > 30:
			paginated_members = str('\n'.join([member.display_name for member in role.members[:15]]))[:2040]
		else:
			paginated_members = str('\n'.join([member.display_name for member in role.members]))
		e = discord.Embed(
			title=f"{len(role.members)} members:",
			description=paginated_members,
			color=role.color
		)
		return await ctx.send(embed=e)

	@commands.group(case_insensitive=True, invoke_without_command=True)
	async def newest(self, ctx):
		"""Lists the newest x."""
		await ctx.send(f"`newest` command sorts lots of things, by age or name/length of name."
					f" run `{ctx.prefix}help newest` to get the subcommands.")

	@newest.command(name="members")
	async def newest_members(self, ctx, *, mode: SortedFlagConverter() = Flag('age')):
		"""Sort members"""
		if mode.age:
			done = sorted(ctx.guild.members, key=lambda m: m.joined_at, reverse=True)

		elif mode.name_abc:
			done = sorted(ctx.guild.members, key=lambda m: m.name, reverse=True)
		elif mode.name_length:
			done = sorted(ctx.guild.members, key=lambda m: len(m.name), reverse=True)
		elif mode.id:
			done = sorted(ctx.guild.members, key=lambda m: m.id, reverse=False)
		else:
			return await ctx.send("Invalid Option")

		done = done[:5]
		done = [x.name for x in done]
		await ctx.send(str('\n'.join(done)).replace('@e', '@:e').replace('@h', '@.h')[:2000])

	@commands.command(aliases=['poll', 'addvote', 'vote'])
	@commands.has_permissions(manage_messages=True, add_reactions=True)
	async def addpoll(self, ctx, message_id: discord.Message, reactions: commands.Greedy[typing.Union[discord.Emoji, str]]):
		"""Add reactions to a message. max of 10

		*reactions* can be discord.Emojis, or str (unicode emojis). if the bot fails to add them, it means it could
		not convert it to an emoji. remember i must be in the guild of the custom emoji(s)
		message_id must be in the format of channel_id-message_id if the message is not in the current channel, or just the message link."""
		fixed = []
		for emoji in reactions:
			if isinstance(emoji, discord.Emoji):
				fixed.append(emoji)
			else:
				try:
					await ctx.message.add_reaction(emoji)
					await ctx.message.remove_reaction(emoji, ctx.me)
					fixed.append(emoji)
					continue
				except:
					pass
				if emoji in _emoji.EMOJI_UNICODE.keys():
					if emoji in _emoji.EMOJI_UNICODE.values():
						x = _emoji.emojize(emoji)
						fixed.append(x)
						continue
					x = _emoji.emojize(emoji)
					fixed.append(x)
		for emoji in fixed:
			try:
				await message_id.add_reaction(emoji)
			except discord.Forbidden as e:
				if '(20)' in str(e):
					return await ctx.send("The maximum amount of emojis (20) are on that message.")
				return await ctx.send(f"I can't add reactions in {message_id.channel.mention}!\n{e}")
			except Exception as e:
				raise

	@commands.command(ignore_extra=False)
	@commands.has_permissions(manage_messages=True)
	@is_premium()
	@commands.bot_has_permissions(embed_links=True)
	async def bigsay(self, ctx, *, embed_colour: discord.Color = discord.Color.blurple()):
		"""A say command for when you want to say stuff larger then 2000 characters"""
		text = commands.Paginator(prefix='', suffix='', max_size=2048)
		message = await ctx.send(f"Please supply me with as much text as you would like me to send.\nThere is a limit"
								f" at `10240` characters (roughly 5 2000 character messages) to prevent spam/abuse."
								f"To stop inputting text and to send the messages, please say `--exit`. *this will "
								f"automatically quit if you hit the character limit.*\n\nUsed characters: `{len(text)}/10240`")
		c = None
		while (len(text) - 1) < 10240:
			x = lambda m: m.author == ctx.author and m.channel == ctx.channel
			c = x
			msg = await self.bot.wait_for('message', check=c, timeout=600*6)
			if msg.content.lower().startswith(('--exit', '--quit', '--cancel', '--finish')):
				break
			else:
				text.add_line(msg.clean_content)
				await message.edit(content=f"Please supply me with as much text as you would like me to send.\nThere is a limit"
								f" at `10240` characters (roughly 5 2000 character messages) to prevent spam/abuse."
								f"To stop inputting text and to send the messages, please say `--exit`. *this will "
								f"automatically quit if you hit the character limit.*\n\nUsed characters: `{len(text)}/10240`")
				try:
					await msg.delete(delay=0.4)
				except (discord.NotFound, discord.Forbidden):
					pass
				continue
		await message.edit(content="Ok. please tell me the channel to send to. Remember you need the correct permissions.")
		tc = None
		while True:
			tosendto = await self.bot.wait_for('message', check=c)
			if tosendto.content.lower().startswith(('cancel', 'quit')):
				return await message.edit(content="cancelled.")
			await tosendto.delete(delay=0.4)
			if len(tosendto.channel_mentions) > 0:
				tc = tosendto.channel_mentions[0]
				if not tc.permissions_for(ctx.author).send_messages:
					await message.edit(content="You do not have send messages permission in that channel!")
				else:
					break
			content = str(tosendto.content)
			try:
				channel = await commands.TextChannelConverter().convert(ctx, content)
				if channel:
					tc = channel
					if not tc.permissions_for(ctx.author).send_messages:
						await message.edit(content="You do not have send messages permission in that channel!")
					else:
						break
				else:
					await message.edit(content="That channel was not found. please try again.")
			except (commands.BadArgument, discord.NotFound, discord.Forbidden):
				await message.edit(content="That channel was not found. please try again.")
		if tc.permissions_for(ctx.me).embed_links and tc.permissions_for(ctx.me).send_messages and tc.permissions_for(ctx.me).read_messages:
			for num, page in enumerate(text.pages, start=1):
				
				e = discord.Embed(description=page, timestamp=ctx.message.created_at, color=embed_colour,
							url='https://dragdev.github.io/redirects/server.html')
				e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(static_format='png'),
								url='https://dragdev.github.io/redirects/server.html')
				e.set_footer(text=f"\"bigsay\" command, by {ctx.me.display_name}.", icon_url=self.bot.user.avatar_url)
				await tc.send(embed=e)
				await asyncio.sleep(2)
		await message.edit(content=f"ok. {len(text.pages)} embeds have been sent. have a good day!")

	@commands.command(aliases=['rr', 'rroulette', 'russianr'])
	async def russian_roulette(self, ctx):
		"""Take your chances and play the russian roulette!"""
		import random
		choices = ['empty', 'empty', 'empty', 'empty', 'empty', 'bang']
		await ctx.send(random.choice(choices))

	@commands.command(name='unmarkdown', aliases=['umd', 'unmd', 'umarkdown'])
	async def unmarkdown(self, ctx, *, message: discord.Message):
		"""Get the raw version of a message. if the message ID isnt in the current channel, provide the message link
		or the channel_id-message_id."""
		p = commands.Paginator(prefix='```md')
		if len(message.embeds) > 0:
			p.add_line(utils.escape_markdown(message.embeds[0].description, ignore_links=False))
		p.add_line(utils.escape_markdown(message.content, ignore_links=False))
		for pa in p.pages:
			await ctx.send(pa)

	@commands.command()
	async def channelurl(self, ctx, *, channel: typing.Union[discord.TextChannel, discord.VoiceChannel] = None):
		"""Get the channel's url."""
		c = channel if channel else ctx.channel
		return await ctx.send(f"https://discordapp.com/channels/{ctx.guild.id}/{c.id}")

	@commands.command(name='ping', aliases=['pong', 'pang', ':ping_pong:'])
	@commands.cooldown(5, 10, commands.BucketType.channel)
	@commands.bot_has_permissions(embed_links=True)
	async def ping(self, ctx):
		"""Get the bots ping, heartbeat and database read time.

		spamming this command may result in a bot ban. so dont constantly hit the cooldown."""
		heartbeat = round(ctx.bot.latency*1000, 2)
		hb = fix_time(round(ctx.bot.latency, 2), return_ints=False)
		a = time.perf_counter()
		f = await ctx.send(embed=discord.Embed(title="**Loading information - Please wait.**", color=discord.Color.blue()))
		b = time.perf_counter()
		st = round(b - a, 2) * 1000
		s_r = time.time()
		with open('./data/names.json', 'r') as _______:
			_ = json.load(_______)
			f_r = time.time()
		ff_rt = round(f_r - s_r, 2)
		e = discord.Embed(title=f"Pong! IM ALIVEEEEEEEEEEEEEEE", description=f"\U00002764 **{hb} ({heartbeat}ms)** Heartbeat Latency\n"
																			f"\U000023f1 **{st}ms** Messaging delay\n"
																			f"\U0001f4d8 **{ff_rt}ms** Database read time (names.json)",
						color = discord.Color.blue())
		ini = round(time.time() - self.bot.startup, 2)
		b = round(time.time() - self.bot.ready_at, 2)
		fixed_run = fix_time(ini)
		fixed_ready = fix_time(b)
		e.add_field(name="Boot info:",
					value=f"Bot initially run: `{fixed_run}` ago\nLast booted: `{fixed_ready}` ago\n"
						f"Total reboots: `{self.bot.reboots}`", inline=False)
		return await f.edit(embed=e)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	@commands.bot_has_permissions(administrator=True)
	async def stealemoji(self, ctx, *, emoji: discord.PartialEmoji):
		x = await ctx.guild.create_custom_emoji(name=ctx.author.display_name[:2] + emoji.name, image=await emoji.url.read())
		return await ctx.send('`' + str(x) + '`')

	@commands.command(aliases=['brb', 'gtg', 'bye'])
	@commands.bot_has_permissions(embed_links=True)
	async def afk(self, ctx, *, reason: commands.clean_content = None):
		"""Mark yourself as AFK."""
		if reason is None:
			with open('./data/afk.json', 'r') as x:
				data = json.load(x)
				since = '`Unavailable`'
				if str(ctx.author.id) in data.keys():
					since = data[str(ctx.author.id)]['since']
					del data[str(ctx.author.id)]
				else:
					return await ctx.send("You weren't afk.")
				await ctx.send(f"Welcome back! You have been afk for "
							f"{str(ago_time(since)).replace('ago', '')}.")
				with open('./data/afk.json', 'w') as y:
					json.dump(data, y)
					return

		reason = str(reason)[:256]
		R = f"with reason: {reason}" if reason else ''
		a = await ctx.send("Set you to AFK" + ' ' + R)
		if ctx.channel.permissions_for(ctx.me).manage_messages and ctx.guild is not None:
			await ctx.message.delete()
		with open('./data/afk.json', 'r') as ab:
			d = json.load(ab)
			_d = d

			removed = False

			if reason is None and str(ctx.author.id) in d.keys():
				removed = True
				d.keys().remove(str(ctx.author.id))

			if not removed:
				d[str(ctx.author.id)] = {"reason": reason, "since": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")}

			with open('./data/afk.json', 'w') as b:
				json.dump(d, b, indent=1)
				if removed:
					dt = datetime.datetime.strptime(_d[str(ctx.author.id)]['since'],"%Y-%m-%d %H:%M:%S.%f") \
					.strftime('%A the %d of %b, %Y')
					await a.delete()
					return await ctx.send(f"Welcome back! You have been afk for "
										f"{str(ago_time(_d[str(ctx.author.id)]['since'])).replace('ago', '')}")
				else:
					return

	@commands.Cog.listener(name='on_message')
	async def check_if_pinged(self, message):
		if message.author.bot or message.guild is None:
			return
		if not message.channel.permissions_for(message.guild.me).embed_links:
			return
		if len(message.mentions) == 0:
			return

		with open('./data/afk.json', 'r') as afkfile:
			data = json.load(afkfile)
			# if len(message.mentions) > 1:
			# 	e = discord.Embed(description="Multiple of the people you mentioned are AFK.")
			# 	return await message.channel.send(embed=e)

			member = message.mentions[0]
			if str(member.id) in data.keys():
				e = discord.Embed(title=f"{member.display_name} is afk.", description=f"Reason: "
																f"{data[str(member.id)]['reason']}", color=member.color)
				try:
					s = datetime.datetime.strptime(data[str(member.id)]['since'], "%Y-%m-%d %H:%M:%S.%f")
					e.timestamp = s
					e.set_footer(text="AFK since: ")
				except:
					pass
				return await message.channel.send(embed=e, delete_after=15)

	@commands.group(invoke_without_command=True)
	async def scramble(self, ctx, *, text: commands.clean_content = 'You didn\'t provide any text!'):
		"""Scramble some text to make it look weird.

		Takes code blocks, words, letters, mentions (channel mentions may be broken) or basically anything."""
		_w = list(str(text))
		new_word = ""
		for i in range(len(_w)):
			l = __import__('random').choice(_w)
			new_word += l
			_w.remove(l)
		return await ctx.send(discord.utils.escape_mentions(new_word))

	@commands.command(name='choose', aliases=['choice', 'pick'], usage='choose [things to choose from separated by space]')
	async def choose(self, ctx, *options: commands.clean_content):
		"""Chooses between a list of things."""
		opt = list(options)
		for num, option in enumerate(opt, 1):
			if re.search(r'(?:https?://)?discord(?:app\.com/invite|\.gg)/?[a-zA-Z0-9]+/?', str(option)) is not None:
				opt.remove(option)
				opt.append('[invite detected and removed.]')
		return await ctx.send(random.choice(opt).replace('discord.gg/', 'nononon.on/'))

	@commands.command(name="clappify", aliases=['clapify', 'clapup', 'clap', 'gg', '\N{CLAPPING HANDS SIGN}'])
	async def clapup(self, ctx, *, text: commands.clean_content = 'you forgot to supply text :bigbrain10000:'):
		"""clap 👏 up 👏 some 👏 text"""
		text = str(text)
		text = text.replace('.', '\u200B.')
		return await ctx.send(str(' \N{CLAPPING HANDS SIGN} '.join(text.split()))[:2000])

	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	async def invite(self, ctx):
		"""Get invite links for the bot."""
		rec_p = discord.Permissions(268791015)
		min_p = discord.Permissions(355425)
		r = 'https://dragdev.xyz/thank_you.htmk'
		rec = utils.oauth_url(ctx.bot.user.id, permissions=rec_p, redirect_uri=r)
		min = utils.oauth_url(ctx.bot.user.id, permissions=min_p, redirect_uri=r)
		e = discord.Embed(
			title="Invite me!",
			description=f"To invite the bot we recommend using the [website's dropdown menu]"
			f"(https://dragdev.xyz/supertool), but you can choose from [recommended perms]({rec}), or [Minimum "
			f"Permissions]({min}).\n\nBotLists:\n[discord.bots.gg](https://discord.bots.gg/bots/614260030015012875)\n"
			f"[pending]\n[pending]\n\nSupport server: https://discord.gg/ekcWBMT",
			color=0xbc1b16
		)
		owner = self.bot.get_user(self.bot.owner_ids[0])
		e.set_footer(text=f"My owner is {str(owner)}.", icon_url=str(owner.avatar_url_as(format='png')))
		return await ctx.send(embed=e)

def setup(bot):
	bot.add_cog(Core(bot))

import discord
import json
import typing
import asyncio

from discord.ext import commands
from utils import checks, errors
try:
	from utils.converters import fix_time
except:
	pass


class DynamicGuild(commands.Converter):
	async def convert(self, ctx, argument):
		try:
			argument = int(argument)
		except:
			pass
		bot = ctx.bot
		if isinstance(argument, int):
			# check if its an ID first, else check enumerator
			guild = bot.get_guild(argument)
			if guild is not None:  # YAY
				return guild
			else:  # AWW
				for number, guild in enumerate(bot.guilds, start=1):
					if number == argument:
						return guild
				else:
					if guild is None:
						raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' with reason 'type None'")
					else:
						raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' as loop left.")
		elif isinstance(argument, str):  # assume its a name
			for guild in bot.guilds:
				if guild.name.lower() == argument.lower():
					return guild
			else:
				raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' with reason 'type None' at 1")
		else:
			raise commands.BadArgument(f"Could not convert argument of type '{type(argument)}' to 'Guild'")


class Owner(commands.Cog, name="Bot Management"):
	"""Bot management cog that just does the boring HR stuff."""
	def __init__(self, bot):
		self.bot = bot

	@commands.group(invoke_without_command=True)
	@checks.bot_mod()
	async def servers(self, ctx):
		"""Lists servers."""
		paginator = commands.Paginator(prefix="```md")
		for number, guild in enumerate(ctx.bot.guilds, start=1):
			dot = '\u200B.'
			backtick = '\u200B`'
			paginator.add_line(discord.utils.escape_markdown(f'{number}) {guild.name.replace(".", dot).replace("`", backtick)}\n'))
		for page in paginator.pages:
			await ctx.send(page)

	@servers.command(aliases=['join'])
	@checks.bot_mod()
	async def invite(self, ctx, *, guild: DynamicGuild()):
		"""get an invite to a guild

		you can pass a name, id or enumerator number. ID is better."""
		if guild.me.guild_permissions.manage_guild:
			m = await ctx.send("Attempting to find an invite.")
			invites = await guild.invites()
			for invite in invites:
				if invite.max_age == 0:
					return await m.edit(content=f"Infinite Invite: {invite}")
			else:
				await m.edit(content="No Infinite Invites found - creating.")
				for channel in guild.text_channels:
					try:
						invite = await channel.create_invite(max_age=60, max_uses=1, unique=True,
															 reason=f"Invite requested"
															 f" by {ctx.author} via official management command. do not be alarmed, this is usually just"
															 f" to check something.")
						break
					except:
						continue
				else:
					return await m.edit(content=f"Unable to create an invite - missing permissions.")
				await m.edit(content=f"Temp invite: {invite.url} -> max age: 60s, max uses: 1")
		else:
			m = await ctx.send("Attempting to create an invite.")
			for channel in guild.text_channels:
				try:
					invite = await channel.create_invite(max_age=60, max_uses=1, unique=True, reason=f"Invite requested"
					f" by {ctx.author} via official management command. do not be alarmed, this is usually just"
					f" to check something.")
					break
				except:
					continue
			else:
				return await m.edit(content=f"Unable to create an invite - missing permissions.")
			await m.edit(content=f"Temp invite: {invite.url} -> max age: 60s, max uses: 1")

	@servers.command(name='leave')
	@checks.bot_mod()
	async def _leave(self, ctx, guild: DynamicGuild(), *, reason: str = None):
		"""Leave a guild. if ::reason:: is provided, then an embed is sent to the guild owner/system channel
		stating who made the bot leave (you), the reason and when.

		supply no reason to do a 'silent' leave"""
		if reason:
			e = discord.Embed(color=discord.Color.orange(), description=reason, timestamp=ctx.message.created_at)
			e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(static_format='png'))
			if guild.system_channel is not None:
				if guild.system_channel.permissions_for(guild.me).send_messages:
					if guild.system_channel.permissions_for(guild.me).embed_links:
						await guild.system_channel.send(embed=e)
			else:
				try:
					await guild.owner.send(embed=e)
				except discord.Forbidden:
					pass

		await guild.leave()

	@servers.command()
	@commands.dm_only()
	@checks.bot_mod()
	async def info(self, ctx, *, guild: DynamicGuild()):
		"""Force get information on a guild. this includes debug information."""
		owner, mention = guild.owner, guild.owner.mention
		text_channels = len(guild.text_channels)
		voice_channels = len(guild.text_channels)
		roles, totalroles = [(role.name, role.permissions) for role in reversed(guild.roles)], len(guild.roles)
		bot_to_human_ratio = '{}:{}'.format(len([u for u in guild.members if u.bot]), len([u for u in guild.members if not u.bot]))
		default_perms = guild.default_role.permissions.value
		invites = len(await guild.invites()) if guild.me.guild_permissions.manage_guild else 'Not Available'
		fmt = f"Owner: {owner} ({owner.mention})\nText channels: {text_channels}\nVoice Channels: {voice_channels}\n" \
				f"Roles: {totalroles}\nBTHR: {bot_to_human_ratio}\n`@everyone` role permissions: {default_perms}\nInvites: " \
				f"{invites}"
		await ctx.send(fmt)

		paginator = commands.Paginator()
		for name, value in roles:
			paginator.add_line(f"@{name}: {value}")
		for page in paginator.pages:
			await ctx.send(page)
		return await ctx.message.add_reaction('\U00002705')

	@staticmethod
	async def getconfig():
		with open('./data/owner.json', 'r') as raw:
			data = json.load(raw)
		return data

	@staticmethod
	async def setconfig(*, data: dict):
		with open('./data/owner.json', 'w+') as fi:
			json.dump(data, fi, indent=2)
		return True

	@commands.command(name='getlog', aliases=['getlogs', 'botlog', 'debuglog', 'debug'])
	@commands.has_any_role(619296110585970691, 606990179642900540)
	async def _getlog(self, ctx):
		"""Uploads the current log file. assuming that its small enough.

		It may take a moment to remove sensitive information from the file."""
		try:
			with open('./data/debug.log', 'r') as abc:
				lines = abc.readlines()
				new = []
				for line in lines:
					line = line.replace(self.bot.http.token, '[token hidden]')
					new.append(line)
				pag = commands.Paginator(prefix='```bash', max_size=2000)
				for line in new:
					if len(line) >= 1975:
						pag.add_line(line[:1975] + '...')
					else:
						pag.add_line(line)
				for page in pag.pages:
					try:
						await ctx.author.send(page)
					except discord.Forbidden:
						return await ctx.send("Enable your DMs.")
		except UnicodeDecodeError:
			try:
				await ctx.author.send(file=discord.File('./data/debug.log'))
			except discord.Forbidden:
				return await ctx.send("Enable your DMs.")
			except UnicodeDecodeError:
				await ctx.send("Fatal error while reading from the file.")

	@commands.group(invoke_without_command=True)
	@commands.has_role(606990179642900540)
	async def names(self, ctx):
		"""Lists names."""
		paginator = commands.Paginator()
		with open('./data/names.json', 'r') as asdf:
			data = json.load(asdf)
		for line in data.keys():
			user = self.bot.get_user(int(line))
			if user:
				paginator.add_line(f"{str(user)}:")
			else:
				paginator.add_line(f"{line}:")
			for name in data[line]:
				paginator.add_line(f'-- {name}'[:1975])
		paginator.add_line('\n============\nfinished.')
		pages = list(paginator.pages)
		if len(pages) > 5:
			ab = await ctx.send(f"There are over 5 pages. continue to send {len(pages)} pages?")
			try:
				await self.bot.wait_for('message', check=lambda a: a.author == ctx.author and a.channel == ctx.channel and a.content.lower().startswith('y'),
										timeout=30)
			except asyncio.TimeoutError:
				return await ab.delete()
		for page in pages:
			await ctx.send(page)
			await asyncio.sleep(1)

	@names.command()
	@commands.has_role(606990179642900540)
	async def remove(self, ctx, *, user: discord.User):
		"""remove a name from the entries. this removes full name logs."""
		with open('./data/names.json', 'r') as _:
			data = json.load(_)
			if str(user.id) not in data.keys():
				return await ctx.send('\U0001f44e')
			else:
				del data[str(user.id)]
				with open('./data/names.json', 'w') as __:
					json.dump(data, __, indent=1)
				return await ctx.send('\U0001f44d')

	"""@commands.command()
	@commands.has_role(619296110585970691)
	async def fixtime(self, ctx, ret_tup: bool = False, *, seconds: float = 1.0):
		""Convert a unit of seconds to a readable time.

		do `s.fixtime True <time>` to get a tuple of (days, hours, minutes, seconds. defaults to False.""
		await ctx.send(fix_time(seconds, return_ints=ret_tup))"""


def setup(bot):
	# bot.add_check(Owner(bot).bot_check)
	bot.add_cog(Owner(bot))
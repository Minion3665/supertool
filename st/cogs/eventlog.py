import discord
import json
import asyncio

from discord import utils
from discord.ext import commands, tasks
from typing import Union
from utils.converters import ago_time
from utils.checks import bot_mod


class EventLog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.fp = './data/eventlog.json'
		self.default_features = [('message_edits', True), ("message_deletes", True), ("channel_create", False),
								("channel_delete", False), ("role_create", False), ("role_delete", False),
								("member_join", True), ("member_leave", True), ("member_ban", False),
								("emoji_create", False), ("emoji_delete", False), ("member_unban", False),
								("ignore_bots", False)]
		self.format = {
			"log_channel": None,
			"features": self.default_features
		}
		self.sandbox = None
		self.backup_data.start()

	@tasks.loop(hours=1)
	async def backup_data(self):
		with open('./data/names.json', 'r') as a:
			d = json.load(a)
			with open('./data/names_backup.json', 'w+') as cool:
				json.dump(d, cool, indent=1)

	def cog_unload(self):
		self.backup_data.stop()

	async def listen_to_bots(self, ctx, *, potential_bot: Union[discord.User, discord.Member]):
		if not potential_bot.bot:
			return True
		_, data = await self.getconfig(ctx, getguild=True)
		if data is None:  # no config
			return True
		elif data['features'] is None:
			return True
		else:
			for field, value in data['features']:
				if field == 'ignore_bots' and value:
					return False
			else:
				return None

	async def get_response(self, ctx):
		m = await self.bot.wait_for('message', check=lambda a: a.author == ctx.author and a.channel == ctx.channel)
		await m.delete(delay=0.3)
		if m.content.lower().startswith('y'):
			return True
		else:
			return False

	async def getconfig(self, ctx, getguild: bool = False):
		if isinstance(ctx, discord.Guild):
			id = str(ctx.id)
		else:
			id = str(ctx.guild.id)
		with open(self.fp, 'r') as raw:
			data = json.load(raw)

		if getguild:
			return (data, data[id]) if id in data.keys() else (data, None)
		else:
			return data, data

	async def setconfig(self, ctx=None, *, data: dict):
		if ctx:
			d = list(await self.getconfig(ctx))[1]
			d[str(ctx.guild.id)] = data
			data = d
		with open(self.fp, 'w+') as fi:
			json.dump(data, fi, indent=2)
		return True

	async def set_default_values(self, ctx):
		default_log_channel = utils.get(ctx.guild.text_channels, name="event-log")
		data = {}
		data[str(ctx.guild.id)] = self.format
		data[str(ctx.guild.id)]['log_channel'] = default_log_channel
		return await self.setconfig(data=data)

	@commands.group(name="eventlog", aliases=['elog', 'events', 'eventlogging'], invoke_without_command=True)
	@commands.has_permissions(manage_guild=True)
	@commands.bot_has_permissions(manage_guild=True, embed_links=True, manage_messages=True)
	@commands.guild_only()
	async def event_logging(self, ctx):
		"""Get your event logging information.

		This is very similar to how `s.verify` displays."""
		raw, data = await self.getconfig(ctx, getguild=True)
		if data is None:
			pre = ctx.prefix
			qname = ctx.command.qualified_name
			return await ctx.send(f"You haven't got a valid configuration yet! run `{pre}{qname} quicksetup`"
								f" or `{pre}{qname} isetup` to get it all working!")
		else:
			e = discord.Embed(title="Event logging settings:", description="", color=discord.Color.gold())
			p = commands.Paginator(prefix='', suffix='')
			for event, toggled in data['features']:
				d = {
					True: "on",
					False: "off",
					None: "Not set!"
				}
				p.add_line(f"**{event.replace('_', ' ')}:** {d[toggled]}")
			e.description = p.pages[0]
			p.pages.pop(0)  # removes the first page
			chan = self.bot.get_channel(data['log_channel'])
			if chan is None:
				e.add_field(name="Logging channel:", value="Not found (`#not-found!`)")
			else:
				e.add_field(name="logging channel:", value=f"{chan.mention} (`#{str(chan)}`)")
			embeds = [e]
			for page in p.pages:
				e = discord.Embed(description=page, color=discord.Color.gold())
				embeds.append(e)
			embeds[-1].set_footer(text=f"event logging, by {ctx.me.display_name}.", icon_url=self.bot.user.avatar_url_as(format='png'))
			for page, embed in enumerate(embeds, start=1):
				embed.set_author(name=f"page {page}/{len(embeds)}")
				await ctx.send(embed=e)

	@event_logging.command(name="edit", aliases=['change', 'newvalue', 'set'])
	@commands.has_permissions(manage_guild=True)
	@commands.bot_has_permissions(manage_guild=True, embed_links=True, manage_messages=True)
	@commands.guild_only()
	async def event_logging_edit(self, ctx, field: str, *, new_setting: Union[bool, discord.TextChannel] = None):
		"""Edit a field.
		pass field as `list` to get a list of fields."""
		raw, data = await self.getconfig(ctx, getguild=True)
		if field.lower() == 'list':
			x = ""
			for fi, va in data['features']:
				x += f"**Field name:** {fi}\n"
			x += f"\n\n**log_channel:** <#{data['log_channel']}>"
			return await ctx.send(x)
		else:
			if field.lower() == 'log_channel':
				data['log_channel'] = new_setting.id
				await self.setconfig(ctx, data=data)
				return await ctx.send(f"Changed event logging channel to {new_setting.mention}.")
			else:
				_data = []
				field = field.lower().replace(' ', '_')
				if field == 'all':
					for a, b in data['features']:
						_data.append((a, new_setting))
					await ctx.send(f"Set all fields to `{new_setting}`.")
				elif field not in [a for a, b in data['features']] or isinstance(new_setting, discord.TextChannel):
					return await ctx.send("Invalid field.")
				else:
					for fi, va in data['features']:
						if fi.lower() == field:
							_data.append((fi, new_setting))
						else:
							_data.append((fi, va))
				data["features"] = _data
				await self.setconfig(ctx, data=data)
				return await ctx.send(f"set {field} to {new_setting}.")

	@event_logging.command(name='quicksetup', aliases=['qsetup', 'quicks'])
	@commands.has_permissions(manage_guild=True)
	@commands.bot_has_permissions(manage_guild=True, embed_links=True, manage_messages=True)
	@commands.guild_only()
	async def event_logging_quick_setup(self, ctx):
		"""Runs a setup which sets the default values for you to edit later on."""
		await self.set_default_values(ctx)
		await ctx.send("Done.")
		return await ctx.invoke(self.bot.get_command('elog'))

	@event_logging.command(name="interactivesetup", aliases=['isetup', 'interactives'])
	@commands.has_permissions(manage_guild=True)
	@commands.bot_has_permissions(manage_guild=True, embed_links=True, manage_messages=True)
	@commands.guild_only()
	async def event_logging_interactive_setup(self, ctx):
		"""Interactive setup, taking you through every option."""
		return await ctx.send("Wip.")

	# TODO:

	async def do_message_log(self, message: discord.Message, *, before: discord.Message=None, edit: bool = False, channel:discord.TextChannel):
		x = {
			True: "edited",
			False: "deleted"
		}
		e = discord.Embed(title=f"Message (in {message.channel.name}) {x[edit]}!",
			description=message.content,
			color=message.author.color,
			timestamp=message.created_at,
		)
		e.set_author(name=message.author.display_name, icon_url=message.author.avatar_url_as(static_format='png'))
		if before and edit:
			e.add_field(name="before:", value=str(before.content), inline=False)
		try:
			return await channel.send(embed=e)
		except discord.HTTPException:
			return

	@commands.Cog.listener(name="on_message_delete")
	async def log_delete(self, message: discord.Message):
		if not await self.listen_to_bots(message, potential_bot=message.author):
			return
		_, data = await self.getconfig(message, getguild=True)
		if data is None:
			return
		for field, toggle in data['features']:
			if field.lower() == 'message_deletes' and toggle is True:
				msgchan = self.bot.get_channel(data['log_channel'])
				if msgchan is None:
					return
				return await self.do_message_log(message, channel=msgchan)

	@commands.Cog.listener(name='on_message_edit')
	async def log_edit(self, message, after):
		if not await self.listen_to_bots(message, potential_bot=message.author):
			return
		_, data = await self.getconfig(message, getguild=True)
		if data is None:
			return
		for field, toggle in data['features']:
			if field.lower() == 'message_edits' and toggle is True:
				msgchan = self.bot.get_channel(data['log_channel'])
				if msgchan is None:
					return
				return await self.do_message_log(after, before=message, edit=True, channel=msgchan)

	async def do_member_log(self, member, *, ban: bool = False, leave: bool = False, channel: discord.TextChannel):
		roles = None
		if ban:
			x = "banned!"
		elif leave:
			x = "left!"
		else:
			x = "joined!"
		if x.startswith('b'):
			col = discord.Color.dark_red()
		elif x.startswith('l'):
			col = discord.Color.red()
		else:
			col = discord.Color.green()
		e = discord.Embed(title=f"Member {x}", description="", color=col, timestamp=__import__('datetime').datetime.utcnow())
		with open('./data/names.json', 'r') as names:
			past_names_raw = json.load(names)
		a_long_long_time = ago_time(member.created_at)
		e.description += f"**Name and ID:** `{str(member)} ({member.id})`\n**Account Created:** {a_long_long_time}"
		if str(member.id) in past_names_raw.keys():
			names = [utils.escape_markdown(name, ignore_links=False) for name in past_names_raw[str(member.id)]]
			e.add_field(name="Past names:", value=str(', '.join(names))[:1024], inline=False)
		if (ban or leave) and isinstance(member, discord.Member):
			x = []
			for role in member.roles:
				x.append(role.mention)
			x = ', '.join(x)
			if len(str(x)) > 1024:
				e.add_field(name="Roles:", value=str(x)[:1020] + '...', inline=False)
			else:
				e.add_field(name="Roles:", value=x, inline=False)
		e.set_thumbnail(url=member.avatar_url_as(static_format='png'))
		return await channel.send(embed=e)

	@commands.Cog.listener(name="on_member_join")
	async def do_join_log(self, member):
		if not await self.listen_to_bots(member, potential_bot=member):
			return
		_, data = await self.getconfig(member, getguild=True)
		if data is None:
			return
		for field, toggle in data['features']:
			if field.lower() == 'member_join' and toggle is True:
				msgchan = self.bot.get_channel(data['log_channel'])
				if msgchan is None:
					return
				return await self.do_member_log(member, channel=msgchan)

	@commands.Cog.listener(name='on_member_remove')
	async def do_leave_log(self, member):
		if not await self.listen_to_bots(member, potential_bot=member):
			return
		_, data = await self.getconfig(member, getguild=True)
		if data is None:
			return
		for field, toggle in data['features']:
			if field.lower() == 'member_leave' and toggle is True:
				msgchan = self.bot.get_channel(data['log_channel'])
				if msgchan is None:
					return
				return await self.do_member_log(member, leave=True, channel=msgchan)

	@commands.Cog.listener(name='on_member_ban')
	async def do_ban_log(self, guild, member):
		if not await self.listen_to_bots(member, potential_bot=member):
			return
		_, data = await self.getconfig(guild, getguild=True)
		if data is None:
			return
		for field, toggle in data['features']:
			if field.lower() == 'member_ban' and toggle is True:
				msgchan = self.bot.get_channel(data['log_channel'])
				if msgchan is None:
					return
				return await self.do_member_log(member, ban=True, channel=msgchan)

	@commands.Cog.listener(name='on_user_update')
	async def save_new_names(self, bef, aft):
		if bef.name != aft.name:
			with open('./data/names.json', 'r') as nam:
				data = json.load(nam)
				if str(aft.id) not in data.keys():
					data[str(aft.id)] = []
				data[str(aft.id)].append(str(bef.name))
			with open('./data/names.json', 'w') as man:
				json.dump(data, man)

	async def do_role_log(self, role, *, delete: bool = False, channel: discord.TextChannel):
		members = ', '.join([x.mention for x in role.members])
		e = discord.Embed(
			title=f"Role {'created!' if not delete else 'deleted!'}",
			description=f"**Role name:** `{role.name}`\n**Mentionable:** {role.mentionable}\n**Hoisted:** {role.hoist}\n"
						f"**Managed by integration/bot:** {role.managed}\n"
						f"**Color:** `#{role.color}` (preview in embed bar)\n**Members:** {members}",
			color=role.color,
			timestamp=role.created_at
		)
		e.set_footer(text=f"role {'deleted' if delete else 'created'}: ")
		return await channel.send(embed=e)

	@commands.Cog.listener(name='on_guild_role_create')
	async def log_role_create(self, role):
		# print("create - 1")
		await asyncio.sleep(10)
		_, data = await self.getconfig(role, getguild=True)
		if data is None:
			return
		# print("craete - 2")
		for field, toggle in data['features']:
			if field.lower() == 'role_create' and toggle is True:
				msgchan = self.bot.get_channel(data['log_channel'])
				# print("create - 3")
				if msgchan is None:
					return
				# print("create - final")
				return await self.do_role_log(role, delete=False, channel=msgchan)

	@commands.Cog.listener(name='on_guild_role_delete')
	async def log_role_delete(self, role):
		_, data = await self.getconfig(role, getguild=True)
		if data is None:
			return
		for field, toggle in data['features']:
			if field.lower() == 'role_delete' and toggle is True:
				msgchan = self.bot.get_channel(data['log_channel'])
				if msgchan is None:
					return
				return await self.do_role_log(role, delete=True, channel=msgchan)

	async def do_channel_log(self):
		return


def setup(bot):
	bot.add_cog(EventLog(bot))


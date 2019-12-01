import datetime
from discord.ext import commands
import discord
from cogs.owner import DynamicGuild

class IntegerOverflow(Exception):
	def __init__(self, *, current_value, max_value):
		self.current = current_value
		self.max = max_value

	def __str__(self):
		return f"IntegerOverflow: {self.current} > {self.max}, with {self.max} being the highest permitted value."


def ago_time(time):
	"""Convert a time (datetime) to a human readable format.
	"""
	date_join = datetime.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S.%f")
	date_now = datetime.datetime.now(datetime.timezone.utc)
	date_now = date_now.replace(tzinfo=None)
	since_join = date_now - date_join

	m, s = divmod(int(since_join.total_seconds()), 60)
	h, m = divmod(m, 60)
	d, h = divmod(h, 24)
	y = 0
	while d >= 365:
		d -= 365
		y += 1

	if y > 0:
		msg = "{4}y, {0}d {1}h {2}m {3}s ago"
	elif d > 0 and y == 0:
		msg = "{0}d {1}h {2}m {3}s ago"
	elif d == 0 and h > 0:
		msg = "{1}h {2}m {3}s ago"
	elif d == 0 and h == 0 and m > 0:
		msg = "{2}m {3}s ago"
	elif d == 0 and h == 0 and m == 0 and s > 0:
		msg = "{3}s ago"
	else:
		msg = ""
	return msg.format(d, h, m, s, y)


def fix_time(time: int = None, *, return_ints: bool = False, brief: bool = False):
	"""Convert a time (in seconds) into a readable format, e.g:
	86400 -> 1d
	3666 -> 1h, 1m, 1s

	set ::return_ints:: to True to get a tuple of (days, minutes, hours, seconds).
	--------------------------------
	:param time: int -> the time (in seconds) to convert to format.
	:keyword return_ints: bool -> whether to return the tuple or (default) formatted time.
	:raises ValueError: -> ValueError: time is larger then 7 days.
	:returns Union[str, tuple]:
	to satisfy pycharm:
	"""
	seconds = round(time, 2)
	minutes = 0
	hours = 0
	overflow = 0

	d = 'day(s)' if not brief else 'd'
	h = 'hour(s)' if not brief else 'h'
	m = 'minute(s)' if not brief else 'm'
	s = 'seconds(s)' if not brief else 's'
	a = 'and' if not brief else '&'

	while seconds >= 60:
		minutes += 1
		seconds -= 60
	while minutes >= 60:
		hours += 1
		minutes -= 60
	while hours > 23:
		overflow += 1
		hours -= 23

	if return_ints:
		return overflow, hours, minutes, seconds
	if overflow > 0:
		return f'{overflow} day(s), {hours} hour(s), {minutes} minute(s) and {round(seconds, 2)} second(s)'
	elif overflow == 0 and hours > 0:
		return f'{hours} hour(s), {minutes} minute(s) and {round(seconds, 2)} second(s)'
	elif overflow == 0 and hours == 0 and minutes > 0:
		return f'{minutes} minute(s) and {round(seconds, 2)} second(s)'
	else:
		return f'{round(seconds, 2)} second(s)'


class GlobalMemberConverter(commands.Converter):
	async def convert(self, ctx, argument) -> discord.Member:
		if isinstance(argument, discord.Member):
			return argument  # why
		elif isinstance(argument, int):
			u = ctx.bot.get_uer(argument)
			if u is None:  # not in cache
				try:
					u = await ctx.bot.fetch_user(argument)
				except discord.NotFound:
					raise commands.BadArgument(f"Could not convert \"{argument}\" of type `int` to User.")
			if u:
				for guild in ctx.bot.guilds:
					try:
						_ctx = ctx
						_ctx.guild = guild
						member = await commands.MemberConverter().convert(_ctx, u.id)
						return member
					except:
						continue
				else:
					raise commands.BadArgument(f"Unable to convert User to Member. do we share a guild?")
		elif isinstance(argument, str):
			for guild in ctx.bot.guilds:
				try:
					_ctx = ctx
					_ctx.guild = guild
					member = await commands.MemberConverter().convert(_ctx, str(argument))
					return member
				except:
					continue
			else:
				raise commands.BadArgument(f"Unable to convert \"{argument}\" to member. did you type the name correctly?")
		else:
			raise commands.BadArgument(f"Unsupported type '{type(argument)}' provided to member converter")



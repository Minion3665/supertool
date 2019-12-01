from discord.ext import commands
import discord
from utils import errors

def guild_owner():
	def pred(ctx):
		return ctx.author == ctx.guild.owner or ctx.author.id == ctx.bot.owner_id
	return commands.check(pred)


def owner_access():
	def pred(ctx):
		return ctx.author.id in ctx.bot.cool_people
	return commands.check(pred)


# stuff i don't get below:
def check_permissions(ctx, perms, *, check=all):
	resolved = ctx.channel.permissions_for(ctx.author)
	return check(getattr(resolved, name, None) == value for name, value in perms.items())


def has_permissions(*, check=all, **perms):
	async def pred(ctx):
		return check_permissions(ctx, perms, check=check)
	return commands.check(pred)


async def check_guild_permissions(ctx, perms, *, check=all):
	if ctx.guild is None:
		return False

	resolved = ctx.author.guild_permissions
	return check(getattr(resolved, name, None) == value for name, value in perms.items())


def has_guild_permissions(*, check=all, **perms):
	async def pred(ctx):
		return await check_guild_permissions(ctx, perms, check=check)
	return commands.check(pred)

# end wierd shit


def bot_mod():
	def predicate(ctx):
		roles = [625584831320948737]
		if ctx.author is None or isinstance(ctx.author, discord.User):
			return False
		members = []
		for role in roles:
			members = members + discord.utils.get(ctx.bot.get_guild(606866057998762023).roles, id=role).members
		if ctx.author not in members:
			raise commands.CheckFailure("This command is Bot Moderator only. Sorry, Minion3665 + Eek")
		return ctx.author in members
	return commands.check(predicate)


def is_premium():
	def regular(ctx):
		if ctx.author is None or isinstance(ctx.author, discord.User):
			return False
		a = discord.utils.get(ctx.bot.get_guild(606866057998762023).roles, name='SuperTool - Premium Standard').members
		b = discord.utils.get(ctx.bot.get_guild(606866057998762023).roles, name='SuperTool - Super Premium').members
		if ctx.author not in a and ctx.author not in b:
			raise commands.CheckFailure("This command is Premium only! get premium at "
										f"<https://www.dragdev.xyz/supertool/#pricing-tables2-5>!")
		return ctx.author in a or ctx.author in b
	return commands.check(regular)


def is_super_premium():
	def _super(ctx):
		if ctx.author is None or isinstance(ctx.author, discord.User):
			return False
		b = discord.utils.get(ctx.bot.get_guild(606866057998762023).roles, name='SuperTool - Super Premium').members
		if ctx.author not in b:
			raise commands.CheckFailure("This command is Super-Premium only! get premium at "
										f"<https://www.dragdev.xyz/supertool/#pricing-tables2-5>!")
		return ctx.author in b
	return commands.check(_super)

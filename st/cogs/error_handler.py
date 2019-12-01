import discord
import traceback
from utils.errors import BlacklistedGuild, BlacklistedUser
from utils.converters import fix_time

from discord.ext import commands


class ErrorHandler(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.bot.error_channel = bot.get_channel(613073501372416000)
		self.default_responses = {
			BlacklistedUser: "Sorry {author.name}, but you are banned from using this bot for: `{reason}`. If"
							 " You believe this was unfair, please ping my developer.",
			BlacklistedGuild: "Sorry {author.name}, but this guild has been banned from using this bot for: `{reason}`."
							  " Please ask the owner to appeal this with the developer.",
			commands.NoPrivateMessage: "This command can't be run in DMs. try running it in a server?"
		}

	async def send_tb(self, ctx, channelobj: discord.TextChannel, *, cid: int, tb: str = None, pages: list = None):
		if tb is None and pages is None:
			raise ValueError("tb or pages must be provided")
		if ctx.command is None:
			ctx.command = self.bot.get_command('help')
		index = await channelobj.send(f"**Case {str(ctx.message.id)[-4:-1]}:**")
		msgs = []
		for page in pages:
			x = await channelobj.send(page)
			msgs.append(x.jump_url)
		y = f"Author: {discord.utils.escape_mentions(str(ctx.author))} | `{ctx.author.id}`\nCommand: {ctx.command.qualified_name} |"\
			f" {str(ctx.command.cog.qualified_name)}\nGuild: {ctx.guild.name.replace('@', '@:') if ctx.guild else 'DM'} | `" \
			f"{ctx.guild.id if ctx.guild else ctx.channel.id}`\nMy Permissions: " \
			f"{ctx.channel.permissions_for(ctx.me).value if ctx.guild else 'DM'}\n" \
			f"Their Permissions: {ctx.channel.permissions_for(ctx.author).value if ctx.guild else 'DM'}"

		x = await channelobj.send(y)
		msgs.append(x.jump_url)
		ws = '\n'
		await index.edit(content=f"**Case {str(ctx.message.id)[-4:-1]}:**\n\n*index: {ws.join(msgs)}*")
		await index.channel.send('```\n```')
		return index

	@commands.Cog.listener(name="on_command_error")
	async def stupid_god_damn_errors(self, ctx, error):
		exc_channel = self.bot.get_channel(613073501372416000)
		ctx = await self.bot.get_context(ctx.message)
		if not ctx.valid:
			return # If ctx is not valid this means that a command that is not defined was run. Pass
		try:
			raise error
		except:
			_error = traceback.format_exc()
		ignored = commands.CommandNotFound
		badargs = (commands.BadUnionArgument, commands.BadArgument)
		if ctx.guild is None and isinstance(error, commands.CommandNotFound):
			return await ctx.send(str(error) + '. check `s.help` to see a list of available commands that you can run.')

		if isinstance(error, ignored):
			return

		if isinstance(error, badargs):
			await ctx.send(f"Bad argument\n(`{str(error)}`)\nhelp is below.")
			return await ctx.send_help(ctx.command)
		elif isinstance(error, commands.MissingRequiredArgument):
			await ctx.send("Missing argument(s). help is below.")
			return await ctx.send_help(ctx.command)

		if isinstance(error, commands.TooManyArguments):
			num = len(ctx.command.clean_params)
			return await ctx.send(f"This command takes {num} arguments, but you passed {len(ctx.args)}! if"
								f" you wanted a subcommand, check the name and try again.")

		elif isinstance(error, commands.NotOwner):
			ownerNames = str(self.bot.get_user(self.bot.owner_ids[0]))
			for owner in self.bot.owner_ids[1:]:
				ownerNames = ownerNames + " or " + str(self.bot.get_user(owner))
			return await ctx.send(f"You must be {ownerNames} to run this command!")

		elif isinstance(error, commands.CommandOnCooldown):
			rem = fix_time(error.retry_after)
			return await ctx.send(f"Oh no! it looks like this command is on cooldown! try again in `{rem}`!")

		elif isinstance(error, commands.BotMissingPermissions):
			x = [m.replace('_', ' ') for m in error.missing_perms]
			n = '\n• '
			return await ctx.send(f"I'm' missing the following permissions:\n```\n• {n.join(x)}\n```")
		elif isinstance(error, commands.MissingPermissions):
			x = [m.replace('_', ' ') for m in error.missing_perms]
			n = '\n• '
			return await ctx.send(f"You're missing the following permissions:\n```\n• {n.join(x)}\n```")

		else:  # unknown error
			ctx.command.reset_cooldown(ctx)

			if isinstance(error, commands.CheckFailure):
				if 'premium only' in str(error).lower():
					return await ctx.send(str(error))
				else:
					return await ctx.send(f"Insufficient permissions to run this command (you don't meet a check)"
										f"\n(`{str(error)}`)")

			e = discord.Embed(title="We dropped the scissors!",
							description=f"It looks like an error occurred that managed to cut through the paper!"
							f"\nOur developers have been notified, but if you need it resolving, please"
							f" report the **case ID `{str(ctx.message.id)[-4:-1]}`** to our [support team]("
							f"https://dragdev.xyz/redirects/server.html).",
							color=discord.Color.red())
			e.set_footer(text=f"{str(error)}", icon_url='https://cdn.discordapp.com/emojis/459634743181574144.png?v=1')
			pageinator = commands.Paginator(prefix="```py")
			for line in _error.splitlines(keepends=False):
				pageinator.add_line(line)
			if ctx.author.id in [self.bot.owner_id, 317731855317336067]:
				for page in pageinator.pages:
					await ctx.send(page)
			try:
				await ctx.send(embed=e)
			except (discord.Forbidden, discord.HTTPException):
				try:
					await ctx.send(f"403 or 400 response while sending error message. please ensure i have embed links to do this.")
				except discord.Forbidden:
					try:
						await ctx.author.send(f"403 or 400 response while sending error message. please ensure "
											f"i have embed links to do this.")
					except discord.Forbidden:
						try:
							await ctx.message.add_reaction('<:eekuborkedit:603246957288226860>')
						except discord.Forbidden:
							pass
			finally:
				await self.send_tb(ctx, exc_channel, cid=6969, tb=_error, pages=pageinator.pages)
			raise error


def setup(bot):
	bot.add_cog(ErrorHandler(bot))

import discord
import datetime
import json
import asyncio
import typing

from discord.ext import commands


class Verification(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.format = {
			"dm_mode": False,
			"image_mode": False,
			"image": "",
			"text_mode": True,
			"verify_text": "agree",
			"case_sensitive": True,
			"reaction_mode": False,
			"reaction": "",
			"message_id": None,
			"channel_id": None,
			"mode": "text",
			"kick_if_timeout": True,
			"timeout": 120,
			"give_role": None,
			"enabled": True
		}

	async def setupconfig(self, ctx):
		id = str(ctx.guild.id)
		with open('./data/verify.json', 'r') as raw:
			data = json.load(raw)
		_fmt = self.format
		chanid = discord.utils.get(ctx.guild.text_channels, name='verify')
		chanid = chanid.id if chanid else chanid
		_fmt['channel_id'] = chanid
		data[id] = self.format
		await self.setconfig(data=data)

	@staticmethod
	async def getconfig(ctx, getguild: bool = False):
		id = str(ctx.guild.id)
		with open('./data/verify.json', 'r') as raw:
			data = json.load(raw)

		if getguild:
			return (data, data[id]) if id in data.keys() else (data, None)
		else:
			return data

	async def setconfig(self, ctx=None, *, data: dict):
		if ctx:
			d = await self.getconfig(ctx)
			d[str(ctx.guild.id)] = data
			data = d
		with open('./data/verify.json', 'w+') as fi:
			json.dump(data, fi, indent=2)
		return True

	@staticmethod
	async def has_verify_permissions_bot(ctx, *, channel: discord.TextChannel = None):
		channel = ctx.channel if not channel else channel
		p = channel.permissions_for(ctx.me)
		if p.send_messages and p.read_message_history and p.read_messages and p.embed_links and p.attach_files:
			c = ctx.guild.me.guild_permissions
			if c.kick_members and c.manage_roles:
				return True
			else:
				return False
		else:
			return False

	@commands.group(name="verification", aliases=['captcha', 'verify'], case_insensitive=True, invoke_without_command=True)
	@commands.has_permissions(manage_guild=True)
	async def verification(self, ctx):
		"""Get the current information about your verification configuration."""
		data = await self.getconfig(ctx, True)
		if list(data)[1] is None:
			return await ctx.send(f"You don't have a verification system set yet!\nRun "
								  f"`{ctx.prefix}{ctx.command.qualified_name} setup` to get started!")
		else:
			message = 'https://cdn.discordapp.com/attachments/567753690690093058/616807720296644629/noneset.png'
			if list(data)[1].keys() != self.format.keys():
				return await ctx.send("It looks like your configuration is outdated. please run setup again.")
			data = list(data)[1]
			e = discord.Embed(color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
			channel = self.bot.get_channel(data["channel_id"])
			if channel:
				try:
					message = await channel.fetch_message(data["message_id"])
					message = message.jump_url
				except (discord.NotFound, discord.Forbidden, discord.HTTPException):
					message = 'https://cdn.discordapp.com/attachments/567753690690093058/616807720296644629/noneset.png'
				channel = channel.mention
			else:
				channel = 'https://cdn.discordapp.com/attachments/567753690690093058/616807720296644629/noneset.png'
			e.add_field(name="Location:", value=f"Channel: {channel}\nMessage: [click me]({message})", inline=False)
			setting = data['mode']
			e.add_field(name="Mode:", value=setting.replace('_', ' ').capitalize(), inline=False)
			if setting.lower() == 'text':
				e.add_field(name="Verification text:", value=f"`{discord.utils.escape_markdown(data['verify_text'])}`",
							inline=False)
				e.add_field(name="Case sensitive:", value=data['case_sensitive'], inline=True)
			elif setting.lower() == 'image':
				e.add_field(name="Image:", value="below", inline=False)
				e.set_image(url=f"attachment://./data/{str(ctx.guild.id)}.png")
			elif setting.lower() == 'reaction':
				e.add_field(name="Reaction:", value=data['reaction'], inline=False)
			e.add_field(name="Enabled:", value=data['enabled'], inline=False)
			e.add_field(name="Kick & timeout:", value=f"Kick if timeout reached: {data['kick_if_timeout']}\nTimeout: "
			f"{data['timeout']}", inline=False)
			e.add_field(name="Verification role:", value=str(data['give_role']), inline=False)
			await ctx.send(embed=e)

	@verification.group(name="setup", invoke_without_command=True)
	@commands.has_permissions(manage_guild=True)
	async def verification_setup(self, ctx):
		"""Sets the default values for the data."""
		try:
			await self.setupconfig(ctx)
			await ctx.send("Done.")
		except Exception as e:
			await ctx.send(f"Error while setting up: {e}")

	@verification.command(name="raw")
	@commands.has_permissions(manage_guild=True)
	async def verification_raw(self, ctx):
		"""View the raw data if you feel some values are missing/incorrect."""
		paginator = commands.Paginator(prefix="```json")
		for line in str(list(await self.getconfig(ctx, getguild=True))[1]).splitlines(keepends=False):
			paginator.add_line(line)
		for page in paginator.pages:
			await ctx.send(page, delete_after=120)

	@verification.command(name='interactivesetup', aliases=['is, isetup', 'interactives'])
	@commands.has_permissions(manage_guild=True)
	async def verification_is(self, ctx):
		"""This command will guide you through setting up verification."""
		message = await ctx.send(f"Disclaimer: verification is in very early alpha, and most likely wont work."
								f"Known bugs:\n- image mode not supported\n- reaction mode not supported.")
		await asyncio.sleep(5)

		data = self.format
		await message.edit(content=f"Ok. first of all, what mode will you be using?\nAvailable modes:\n"
								f"~~• image~~\n~~• reaction~~\n• text")

		def check(_message):
			return _message.channel == ctx.channel and ctx.author == _message.author
		msg = await self.bot.wait_for('message', check=check, timeout=600)
		content = msg.content.lower()
		if content.startswith('image'):
			return await message.edit(content="Sorry, but this option is unavailable. Try again later.")
		elif content.startswith('reaction'):
			return await message.edit(content="Sorry, but this option is unavailable. Try again later.")
		elif content.startswith('text'):
			data['mode'] = 'text'
		else:
			return await message.edit(content="Sorry, but that was not a recognised setting.")

		await message.edit(content="What role would you like me to give the user upon verifying?")
		msg = await self.bot.wait_for('message', check=check, timeout=600)
		content = str(msg.clean_content)
		for role in ctx.guild.roles:
			if role.name.lower().startswith(content.lower()):
				if role >= ctx.guild.me.top_role:
					return await message.edit(content="That role is too high.")
				data["give_role"] = role.id
				break
		else:
			return await message.edit(content=f"No role called \"{content}\" found.")
		await message.edit(content="What would you like the user to have to say to verify?\ne.g: agree.")
		msg = await self.bot.wait_for('message', check=check, timeout=600)
		content = str(msg.clean_content).lower()
		content = content.replace('`', '').replace('~~', '').replace('*', '').replace('_', '').replace('||', '')
		data['verify_text'] = content
		await message.edit(content=f"Alright then! the user will have to say `{content}`!\nNext, what channel should"
		f" i tell them to verify in?\nSay DM for DMs (not recommended) or mention a channel.")
		while True:
			msg = await self.bot.wait_for('message', check=check, timeout=600)
			if msg.content.lower().startswith('dm'):
				data['dm_mode'] = True
				break
			else:
				mention = msg.channel_mentions[0]
				can_send = await self.has_verify_permissions_bot(ctx, channel=mention)
				if not can_send:
					await msg.delete()
					await message.edit(content="I am missing one of the following permissions in that channel:\n{}\nTry another channel.".format(
						"\n".join(sorted(['manage messages', 'embed links', 'read message history', 'read messages',
										'attach files', 'kick members', 'manage roles'], key=lambda a: a)
					)))
				else:
					data['channel_id'] = mention.id
					break
		await message.edit(content=f"Ok, and should i kick the user if they don't respond withing <time> seconds? [y/n]")
		msg = await self.bot.wait_for('message', check=check, timeout=600)
		content = msg.content.lower()
		if content.startswith('y'):
			data['kick_if_timeout'] = True
			await message.edit(content="And how long (in seconds) should that be?\n```\n1 minute = 60 seconds\n1 hour = "
									"3600 seconds\n1 day (why) = 86400 seconds\nNo timeout = 0 seconds\n```")
			msg = await self.bot.wait_for('message', check=check, timeout=600)
			content = msg.content.lower()
			time = 0
			for letter in content:
				try:
					l = int(letter)
					time += l
				except:
					continue
		else:
			data['kick_if_timeout'] = False
		await message.edit(
			content=f"Ok, and finally, should the verification text be case sensitive? [y/n]\ne.g: if yes, `Agree` "
					f"wouldn't work if the verify text was set to `agree`.")
		msg = await self.bot.wait_for('message', check=check, timeout=600)
		content = msg.content.lower()
		if content.startswith('y'):
			data['case_sensitive'] = True
		else:
			data['case_sensitive'] = False
		await message.edit(content=f"Oh and, what message ID should i use for verifying? say `0` to make me send a"
									f" predefined message.")
		msg = await self.bot.wait_for('message', check=check, timeout=600)
		content = msg.content.lower()
		try:
			content = int(content)
		except:
			await message.edit(content="Cancelled.")
		else:
			if content == 0:
				tout = data['timeout']
				theid = await mention.send(f"Welcome to {ctx.guild.name}!\nTo gain access to the rest of the server"
										   f", please say "
										   f"`{data['verify_text']}`. {'You will be kicked after {} seconds if you do not verify.'.format(tout) if tout > 0 else ''}")
				data['message_id'] = theid.id
			else:
				data['message_id'] = content
		await message.edit(content="Setting data...")
		try:
			await self.setconfig(ctx, data=data)
		except Exception as e:
			return await ctx.send(f"Error while saving your config ({e}). Your raw data is ```json\n{data}\n```\n"
								f"You can use the `verify setup fromdata` command and pass that data to save it "
								f"manually.")
		else:
			await message.edit(content="all done!.")

	@verification.command(name='toggle')
	@commands.has_permissions(manage_guild=True)
	async def verificiation_toggle(self, ctx, mode: bool = None):
		"""Toggle verification on/off

		passing `mode` as on/off will set it to that, rather then invert the current setting."""
		data = await self.getconfig(ctx, getguild=True)
		if list(data)[1] is None:
			return await ctx.send("You dont even have a system yet!")
		else:
			data = list(data)[1]
			cur = data['enabled']
			if cur:
				new = False
			else:
				new = True
			if mode is not None:
				new = mode
			data['enabled'] = new
			await self.setconfig(ctx, data=data)
			d = {
				True: "ON",
				False: "OFF"
			}
			await ctx.send(f"Verification is now: {d[data['enabled']]}")

	@verification_setup.command()
	@commands.has_permissions(administrator=True)
	async def fromdata(self, ctx, *, data):
		"""Set your guilds data from a predefined dict. this is advanced. be careful.."""
		msg = await ctx.send(f"sandboxing...")
		with open('./data/sandbox.json', 'w+') as sb_file:
			try:
				json.dump(data, sb_file)
			except Exception as e:
				return await msg.edit(content=f"Error: the provided data did not pass the sandbox test with error:\n"
				f"```py\n{e}\n```*what is sandboxing, and why do we do it? sandboxing is a burner file that we use to"
				f" `json.dump()` your data arguments from this command into to make sure the regular file would "
				f"not break.*")
			else:
				await msg.edit(content=f"Sandbox check: OK\nSimulating actual save conditions...")
			try:
				json.dump(data, sb_file, skipkeys=False, indent=2)
			except Exception as e:
				return await msg.edit(content=f"Sandbox check: OK\nError: the provided data did not pass the sandbox test with error:\n"
				f"```py\n{e}\n```*what is sandboxing, and why do we do it? sandboxing is a burner file that we use to"
				f" `json.dump()` your data arguments from this command into to make sure the regular file would "
				f"not break.*")
			else:
				await msg.edit(content=f"Sandbox check: OK\nSimulating actual save conditions: OK\nSimulating mass load...")
				for i in range(5):
					try:
						json.dump(data, sb_file, intent=2)
					except:
						await ctx.send("Mass-load check failed.")
				else:
					await msg.edit(content=f"all checks: OK - setting data.")
					await self.setconfig(ctx, data=data)
					return await ctx.send("All done!")

	@verification.command()
	@commands.has_permissions(manage_guild=True)
	async def edit(self, ctx, field: str, *, new_value: typing.Union[bool, int, str] = None):
		"""Edit a specific value of the verification. pass "list" as field to get the list of values.."""
		if new_value is None and field.lower() != 'list':
			return await ctx.send("If you aren't listing values you must pass a new one!")
		data = await self.getconfig(ctx, getguild=True)
		data = list(data)[1]
		if field.lower() == 'list':
			e = discord.Embed(title="Your current raw config:", description="", color=discord.Color.blue())
			for key in data.keys():
				e.description += f"**Field:** {key}, Value: {data[key]}\n"
			await ctx.send(embed=e)
		else:
			if field not in data.keys():
				return await ctx.send("That Field is not found! remember, its case sensitive.")
			else:
				data[field] = new_value
				await self.setconfig(ctx, data=data)
				return await ctx.send(f"Updated {field}.")

	@commands.Cog.listener(name='on_member_join')
	async def do_verify(self, member):
		if member.bot:
			return
		sid = str(member.guild.id)
		data = await self.getconfig(member, getguild=True)
		if list(data)[1] is None:
			return
		data = list(data)[1]
		if not data['enabled']:
			return
		try:
			role = member.guild.get_role(data["give_role"])
		except discord.NotFound:
			return
		channel = self.bot.get_channel(data['channel_id'])
		await channel.set_permissions(member, read_messages=True, read_message_history=True, send_messages=True)
		await channel.send(member.mention, delete_after=0.01)
		while True:
			try:
				msg = await self.bot.wait_for('message', check=lambda m: m.author == member, timeout=data['timeout'] if data['timeout'] > 0 else None)
			except asyncio.TimeoutError:
				return await member.kick(reason=f"did not verify within set timelimit.")
			content = msg.content if data['case_sensitive'] else msg.content.lower()
			if content == data['verify_text']:
				await msg.delete()
				await msg.channel.set_permissions(member, overwrite=None, reason="verification.")
				return await member.add_roles(role, reason="Verified.")
			else:
				await msg.delete()
				await msg.channel.send(f"{member.mention}: please say only the verify word(s)!\nIf you cant see it, "
									f"DM an admin.", delete_after=5)


def setup(bot):
	bot.add_cog(Verification(bot))
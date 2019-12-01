import discord, asyncio, json, aiohttp, typing
from utils.miniutils import safeSendEmbed
from discord.ext import commands
from discord import Webhook


def write(fp, data):
	with open(fp, 'w') as asdf:
		return json.dump(data, asdf)


class GCC(commands.Converter):
	async def convert(self, ctx, argument):
		if isinstance(argument, discord.TextChannel):
			return argument
		try:
			argument = int(argument)
		except:
			pass
		if isinstance(argument, int):
			c = ctx.bot.get_channel(argument)
			if c is None:
				raise commands.BadArgument(f"Can't get channel '{argument}'")
			else:
				return c
		else:
			if isinstance(argument, str):
				for channel in list(ctx.bot.get_all_channels()):
					if channel.name == argument.lower().replace('#', ''):
						return channel
				else:
					raise commands.BadArgument("cant convert to channel")
			else:
				raise commands.BadArgument()


class AutoFeeds(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		with open('./data/feeds.json', 'r') as a:
			x = json.load(a)
			self.feed_channels = x.keys()

	@commands.Cog.listener()
	async def on_message(self, message):
		if message.author.bot:
			return
		ctx = await self.bot.get_context(message)
		if ctx.valid:
			return
		if str(message.channel.id) not in self.feed_channels:
			return
		else:
			print(1)
			async with aiohttp.ClientSession() as session:
				with open('./data/feeds.json', 'r') as a:
					data = json.load(a)
					if str(message.channel.id) in data.keys():
						print(2)
						i = str(message.channel.id)
						webhook_ids = data[i]
						for opt in webhook_ids:
							webhook = Webhook.partial(opt[0], opt[1],
													adapter=discord.AsyncWebhookAdapter(session))
							try:
								print(3)
								await webhook.send(content="**"+str(message.author)+":**\n>>> "+message.clean_content,
												   embeds=message.embeds if len(message.embeds) > 0 else None)
							except:
								continue
							else:
								await asyncio.sleep(1)  # avoid ratelimits
			await session.close()

	@staticmethod
	def can_sub(ctx, targetchannel):
		member = targetchannel.guild.get_member(ctx.author.id)
		if member is None:
			return False
		x = targetchannel.permissions_for(member)
		y = targetchannel.permissions_for(targetchannel.guild.me)
		a = [x.read_messages, x.send_messages, x.manage_webhooks, y.read_messages, y.send_messages, y.manage_webhooks]
		return a == [True, True, True, True, True, True]

	@staticmethod
	async def has_feed(target: typing.Union[discord.TextChannel, GCC], feedData, feedChannels=None):
		targethooks = await target.webhooks()
		if not feedChannels:
			feedChannels = feedData.keys
		else:
			oldFeedChannels = feedChannels
			feedChannels = []
			for channel in oldFeedChannels:
				feedChannels.append(str(channel.id))
		for feedChannel in feedChannels:
			try:
				feedChannel = feedData[feedChannel]
			except:
				return False
			for webhook_data in feedChannel:
				for webhook in targethooks:
						if webhook.id in webhook_data:
							return True
		return False

	@commands.command(name='subscribe', aliases=['sub', '+feed'])
	async def subtofeed(self, ctx, *, feed: discord.TextChannel):
		"""Subscribe to a feed. this needs you to have manage webhooks in the target channel.

		```md
		# What are feeds?
		Feeds usually mean different things on other bots. but, we use them as discord's "announcement channel" setting
		that you get from develop license. each guild has up to 3 "feed" channels, but can have infinite receiving
		channels.
		```"""
		with open('./data/feeds.json', 'r') as a:
			self.feed_channels = json.load(a).keys()
		def ch(m):
			return m.author == ctx.author and m.channel == ctx.channel
		if str(feed.id) not in self.feed_channels:
			if ctx.author.guild_permissions.administrator:
				msg = f"That channel is not a feed channel!\n*want to set one? try `{ctx.prefix}setfeed`.*"
			else:
				msg = f"That channel is not a feed channel!"
			return await ctx.send(msg)

		m = await ctx.send("What channel would you like to receive feeds into?")
		chan = None
		while chan is None:
			try:
				c = await self.bot.wait_for('message', check=ch, timeout=60)
				x = c.channel_mentions[0] if len(c.channel_mentions) > 0 else c.content
				_ctx = ctx
				_ctx.guild = None  # make it check the global cache, not just the regular cache.
				chan = await GCC().convert(_ctx, x)
			except asyncio.TimeoutError:
				return await m.edit(content="Timeout.")
			except commands.BadArgument as e:
				await c.delete()  # pycharm (and probably other IDEs) highlight this as 'referenced before assignment'.
								# it isn't, trust me.
				await m.edit(content=f"That channel was not found.\n\nWhat channel would you like to receive feeds into?")
			else:
				await c.delete()

		c = self.can_sub(ctx, chan)
		with open('./data/feeds.json', 'r') as feedData:
			data = json.load(feedData)
			if await self.has_feed(chan, data, [feed]):
				await safeSendEmbed(ctx, discord.Embed(title="This channel is already subscribed to this feed", description="Did you mean to subscribe another channel?", color=0xaa0000))
			elif str(chan.id) in data.keys():
				await safeSendEmbed(ctx, discord.Embed(title="This channel is set as a feed channel so it can't be subscribed to feeds", description="Try running setfeed to remove the feed?", color=0xaa0000))
			elif c:
				webhook = await chan.create_webhook(name=f"{str(feed.guild)} #{feed.name}", avatar=await feed.guild.icon_url.read(),
																								reason=f"feed added by {ctx.author}")
				data[str(feed.id)].append((webhook.id, webhook.token))
				with open('./data/feeds.json', 'w') as writableFeedData:
					json.dump(data, writableFeedData, indent=1)
					await ctx.send("done.")
			else:
				return await safeSendEmbed(ctx, discord.Embed(title="You can't subscribe to feeds there",
									description="This could be for a couple of reasons.\n"
									"• I don't have read messages, send messages or manage "
									"webhooks there\n• You don't have read messages, send messages or"
									" manage webhooks there"))

	@commands.command(aliases=["addfeed"])
	@commands.has_permissions(administrator=True)
	async def setfeed(self, ctx, *, channel: discord.TextChannel):
		"""Set a channel as a feed.

		set one again to remove it."""
		p = channel.permissions_for(ctx.author)
		if not ctx.author.guild_permissions.administrator:
			return await ctx.send("You can't set that channel as a feed channel.")
		with open('./data/feeds.json', 'r') as d:
			data = json.load(d)
		await self.remfeed(self, ctx, channel)
		if str(channel.id) in data.keys():
			try:
				del data[str(channel.id)]
			except KeyError:
				pass
			await ctx.send(f"Removed {channel.mention} as a feed channel.")
		else:
			our_channels = 0
			for _channel in data.keys():
				ch = self.bot.get_channel(int(_channel))
				if ch:
					if ch.guild == ctx.guild:
						our_channels += 1
			if our_channels >= 3:
				return await ctx.send("Sorry, but you have the max amount of feed channels.")
			data[str(channel.id)] = []
			await ctx.send(f"Set {channel.mention} as a feed channel")
		with open('./data/feeds.json', 'w') as a:
			json.dump(data, a, indent=1)

	@commands.command(aliases=["unsub", "remfeed", "-feed"])
	@commands.has_permissions(manage_guild=True, manage_webhooks=True)
	async def unsubscribe(self, ctx, *, channel: typing.Union[discord.TextChannel, GCC]):
		"""Unsubscribe from feeds. this removes every feed being sent to that channel."""
		await self.remfeed(self, ctx, channel)

	@staticmethod
	async def remfeed(self, ctx, channel: typing.Union[discord.TextChannel, GCC]):
		"""stop receiving feeds in a channel."""
		if not self.can_sub(ctx, channel):
			return await ctx.send("You can't unsubscribe from feeds there. This could be for a couple of "
								  "reasons.\n```diff\n- I don't have read messages, send messages or manage webhooks "
								  "there\n- You don't have read messages, send messages or manage webhooks there```")
		else:  # all checks passed
			webs = await channel.webhooks()
			with open('./data/feeds.json', 'r') as a:
				data = json.load(a)
				for chan in data.keys():
					chan = data[chan]
					# [[webhook_id, webhook_token]]
					for webhook_data in chan:
						# [webhook_id, webhook_token]
						for webh in webs:
							if webh.id in webhook_data:
								await webh.delete()
								await ctx.send("Unsubscribed a feed")
		await ctx.send(f"{'This channel' if channel == ctx.channel else channel.mention} will no longer receive feeds.")

	@commands.command(name='feeds', aliases=['lf', 'listfeeds'])
	async def list_feeds(self, ctx):
		"""List this guild's feeds."""
		with open('./data/feeds.json', 'r') as a:
			data = json.load(a)  # god i wish i made my json wrapper a package then i can use it everywhere without
								# having to copy and paste
			ours = []
			for channel in data.keys():
				channel = self.bot.get_channel(int(channel))
				if channel:
					if channel.guild == ctx.guild:
						ours.append(channel)
			if len(ours) == 0:
				return await ctx.send("No Feeds.")
			return await ctx.send('\n'.join([x.mention for x in ours]))


def setup(bot):
	bot.add_cog(AutoFeeds(bot))

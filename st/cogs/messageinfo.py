import discord
import heapq
from io import BytesIO
import typing
import matplotlib
import time

matplotlib.use("agg")
import matplotlib.pyplot as plt

plt.switch_backend("agg")
from discord.ext import commands


class MessageInfo(commands.Cog):
	"""Show activity."""

	def __init__(self, bot):
		self.bot = bot

	def create_chart(self, top, others, channel):
		plt.clf()
		sizes = [x[1] for x in top]
		labels = ["{} {:g}%".format(x[0], x[1]) for x in top]
		if len(top) >= 20:
			sizes = sizes + [others]
			labels = labels + ["Others {:g}%".format(others)]
		if len(channel.name) >= 19:
			channel_name = "{}...".format(channel.name[:19])
		else:
			channel_name = channel.name
		title = plt.title("Stats in #{}".format(channel_name), color="white")
		title.set_va("top")
		title.set_ha("center")
		plt.gca().axis("equal")
		colors = [
			"#e74c3c",
			"#992d22",
			"#e67e22",
			"#a84300",
			"#f1c40f",
			"#c27c0e",
			"#1abc9c",
			"#11806a",
			"#2ecc71",
			"#1f8b4c",
			"#3498db",
			"#206694",
			"#e91e63",
			"#ad1457",
			"#9b59b6",
			"#71368a",
			"#7289da",
			"#99aab5"
		]
		pie = plt.pie(sizes, colors=colors, startangle=0)
		plt.legend(
			pie[0],
			labels,
			bbox_to_anchor=(0.7, 0.5),
			loc="center",
			fontsize=10,
			bbox_transform=plt.gcf().transFigure,
			facecolor="#99aab5",
		)
		plt.subplots_adjust(left=0.0, bottom=0.1, right=0.45)
		image_object = BytesIO()
		plt.savefig(image_object, format="PNG", facecolor="#99aab5")
		image_object.seek(0)
		return image_object

	@commands.command(aliases=['cc'])
	@commands.cooldown(1, 120, commands.BucketType.guild)
	async def chatchart(self, ctx, channel: discord.TextChannel = None, messages: typing.Union[int, str] = None):
		"""
		Generates a pie chart, representing the last <amount> messages in the specified channel.
		"""
		if messages is None:
			messages = 5000
		elif isinstance(messages, str):
			messages = None
		e = discord.Embed(description=f"Scanning {messages if messages else 'all'} messages...", colour=discord.Colour.blurple())
		em = await ctx.send(embed=e)

		if channel is None:
			channel = ctx.message.channel
		history = []
		if not channel.permissions_for(ctx.message.author).read_messages:
			await em.delete()
			return await ctx.send("You're not allowed to access that channel.")
		try:
			async with ctx.channel.typing():
				history = await channel.history(limit=messages).flatten()
		except discord.errors.Forbidden:
			await em.delete()
			return await ctx.send("No permissions to read that channel.")
		msg_data = {"total count": 0, "users": {}}

		for msg in history:
			if len(msg.author.display_name) >= 20:
				short_name = "{}...".format(msg.author.display_name[:20]).replace("$", "\$")
			else:
				short_name = msg.author.display_name.replace("$", "\$")
			whole_name = "{}#{}".format(short_name, msg.author.discriminator)
			if msg.author.bot:
				pass
			elif whole_name in msg_data["users"]:
				msg_data["users"][whole_name]["msgcount"] += 1
				msg_data["total count"] += 1
			else:
				msg_data["users"][whole_name] = {}
				msg_data["users"][whole_name]["msgcount"] = 1
				msg_data["total count"] += 1

		if msg_data['users'] == {}:
			await em.delete()
			return await ctx.message.channel.send(f'Only bots have sent messages in {channel.mention}')

		for usr in msg_data["users"]:
			pd = float(msg_data["users"][usr]["msgcount"]) / float(msg_data["total count"])
			msg_data["users"][usr]["percent"] = round(pd * 100, 1)

		top_ten = heapq.nlargest(
			20,
			[
				(x, msg_data["users"][x][y])
				for x in msg_data["users"]
				for y in msg_data["users"][x]
				if y == "percent"
			],
			key=lambda x: x[1],
		)
		others = 100 - sum(x[1] for x in top_ten)
		img = self.create_chart(top_ten, others, channel)
		await em.delete()
		await ctx.message.channel.send(file=discord.File(img, "chart.png"))

	@commands.command()
	@commands.cooldown(1, 120, commands.BucketType.user)
	async def msgstats(self, ctx, channel: discord.TextChannel = None, *, messages: int = 10000):
		"""Scan <channel> and get an overview of <messages>."""
		if channel is None:
			channel = ctx.channel
		a = time.time()
		embeds = 0
		ev_mentions = 0
		role_mentions = 0
		mentions = 0
		channel_mentions = 0
		words = {}
		authors = {}
		msg = await ctx.send("Indexing...")
		async with ctx.channel.typing():
			msgs = await channel.history(limit=messages).flatten()
		await msg.edit(content=f"Calculating statistics for {len(msgs)} messages...")
		for message in msgs:
			if message.author not in authors.keys():
				authors[message.author] = 0
			authors[message.author] += 1

			embeds += len([e for e in message.embeds if e.type == 'rich'])

			for role in message.role_mentions:
				if role.name in ['@everyone', '@here']:
					ev_mentions += 1
				else:
					role_mentions += 1

			mentions += len(message.mentions)

			channel_mentions += len(message.channel_mentions)

			for word in str(message.clean_content).split(' '):
				word = str(word).lower()
				if word not in words.keys():
					words[word] = 1
				else:

					words[word] += 1
		try:
			del words['']
		except KeyError:
			pass
		b = time.time()
		c = round(b - a, 2)
		e = discord.Embed(
			title=f"completed ({c}s):",
			color=discord.Color.blurple()
		)
		resolved_authors = {}
		for a in authors.keys():
			try:
				resolved_authors[a] = authors[a]
			except:
				continue
		resolved_words = {}
		for a in words.keys():
			try:
				resolved_words[a] = words[a]
			except:
				continue
		top_a = sorted(resolved_authors.keys(), key=lambda _a: resolved_authors[_a], reverse=True)[0]
		# await ctx.send(top_a)
		top_word = discord.utils.escape_mentions(sorted(resolved_words.keys(), key=lambda _b: resolved_words[_b], reverse=True)[0])
		e.add_field(name="Most Messages by:", value=f"{top_a.mention} (`{str(top_a)}`) with {authors[top_a]} messages!")
		e.add_field(name="Mentions information:", value=f"**Role mentions:** {role_mentions}\n**Everyone mentions:**"
							f" {ev_mentions}\n**User Mentions:** {mentions}\n**Channel Mentions:** {channel_mentions}",
					inline=False)
		e.add_field(name="Most Used Word:", value=f"\"`{top_word}`\" with {words[top_word]} uses!")
		e.add_field(name="Total embeds sent:", value=str(embeds))
		e.set_footer(text=f"Scanned {len(msgs)} messages. fields with \"*\" may be inaccurate.")
		await ctx.send("clearing the typing status...", delete_after=0.1)
		return await msg.edit(embed=e, content=None)


def setup(bot):
	bot.add_cog(MessageInfo(bot))

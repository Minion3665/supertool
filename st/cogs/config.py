import discord
import json
import os
import asyncio
import datetime
import random

from discord.ext import commands


class Fight(commands.Cog):
	"""The fight cog, so you can whack your "friends" """
	def __init__(self, bot):
		self.bot = bot

	@staticmethod
	def get_config():
		with open('./data/fight.json', 'r') as a:
			return json.load(a)

	@commands.command(aliases=['lb', 'top'])
	@commands.bot_has_permissions(embed_links=True)
	async def leaderboard(self, ctx):
		"""Get the leaderboard."""
		data = self.get_config()
		resolved_list = sorted(data.keys(), key=lambda f: data[f]['wins'], reverse=True)
		e = discord.Embed(title="Top 10 Users:", description="", color=discord.Color.blurple())
		for rank, user in enumerate(resolved_list[:10], start=1):
			_user = self.bot.get_user(int(user))
			if user is None:
				x = {"user": ["unknown", "@unknown"], "wins": data[user]['wins'], "lost": data[user]['lost']}
			else:
				x = {"user": [_user.name, user.mention]}
			e.description += f"**{rank}.** {x['user'][1]} ({x['user'][0]}\n"
		return await ctx.send(embed=e)
	@staticmethod
	async def check(reaction, user):
		if user == member and reaction in ["✔️ ", "❌ "]

	@commands.command(hidden=True)
	async def suicide(self, ctx):
		return await ctx.send("ok ur ded")

	@commands.command()
	@commands.cooldown(1, 60, commands.BucketType.category)
	async def fight(self, ctx, *, user: discord.Member = None):
		"""Fight someone! i dont really know what to say here."""
		player_1 = {'user': ctx.author, 'hp': 100, 'max_hp': 100}
		if user is None:
			return await ctx.send("You can't fight nobody! mention a member instead.")
		elif user == ctx.author:
			return await ctx.send("I mean... why? if you want to fight yourself just try the suicide command.")
		elif user.bot:
			return await ctx.send("Uhh... we have an issue there. I don't listen to bots because all the other bots are trash. "
								f"so, they cant really fight you back and ill give it to them, that would be a little "
								f"unfair.")
		else:  # ayyyyyyyy
			ConfirmMessage = await ctx.send(user.mention+", want to do battle with "+ctx.author.mention+"? (please wait until I have added both ✔️ and ❌ before reacting)")
			await ConfirmMessage.add_reaction("✔️")
			await ConfirmMessage.add_reaction("❌"



def setup(bot):
	bot.add_cog(Fight(bot))


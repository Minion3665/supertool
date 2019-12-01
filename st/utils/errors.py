import discord
from discord.ext import commands


class Blacklisted(commands.CheckFailure):
	pass


class BlacklistedUser(Blacklisted):
	def __init__(self, user: discord.User, reason: str = None):
		self.user = user
		self.reason = reason

	def __str__(self):
		return f"Sorry {self.user.display_name}, but you are blacklisted. reason: {self.reason}\nWant to appeal? " \
				f"go to the support guild at https://discord.gg/kxuScQz"

	def __int__(self):
		return 403


class BlacklistedGuild(Blacklisted):
	def __init__(self, guild: discord.Guild, reason: str = None):
		self.guild = guild
		self.reason = reason

	def __str__(self):
		return f"Sorry but {self.guild.name} is blacklisted from using me, with reason: {self.reason}\nWant to appeal? " \
				f"go to the support guild at https://discord.gg/kxuScQz"

	def __int__(self):
		return 403


class PremiumOnly(Blacklisted):
	def __str__(self):
		return "Only premium members can run this command!"

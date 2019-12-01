import discord
import datetime
from discord.ext import commands, tasks


class NotExclusiveGuild(commands.CommandInvokeError):
	def __init__(self, guild_id: int, ok_guilds,*,reason: str = None):
		self.guild_id = guild_id
		self.ok_guilds = ok_guilds
		self.reason = reason

	def str(self):
		if self.reason:
			return self.reason.format(self.guild_id, self.ok_guilds)
		else:
			return f"{self.guild_id} can't use this command as its not an exclusive guild. only guilds with the IDs " \
				f"{', '.join(self.ok_guilds)} can."

	def __cause__(self):
		return None


class ExclusiveGuildStuff(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.verified_guilds = [486910899756728320, 606866057998762023, 573240252177580032, 480959345601937410]
		self.verified_guilds_dict = []
		self.last_down_msg = {}
		self.check_if_tester.start()

	@commands.Cog.listener(name='on_member_update')
	async def chromebot_outage(self, before, member):
		now = datetime.datetime.utcnow().strftime('%d/%m/%Y, %I:%M%p')
		if member.id not in [499262934715727872, 555361766947815424, 613545011811844137]:
			return
		if member.guild.id == 480959345601937410:
			if str(before.status).lower() != 'offline' and str(member.status).lower() == 'offline':
				await member.guild.owner.send(f"Alert: {member.mention} went offline at {now}"
											f".")
				channel = self.bot.get_channel(584817867166449703)
				if channel:
					a = await channel.send(f"Alert: {member.mention} has gone offline. the current time is {now}."
										f" Chromebook has been alerted and this message will delete after a status is updated,"
										f"or {member.name} appears online again.")
					self.last_down_msg[member.id] = a
			elif str(before.status).lower() == 'offline' and str(member.status) != 'offline':
				if member.id in self.last_down_msg.keys():
					try:
						await self.last_down_msg[member.id].delete()
					except (discord.NotFound, discord.HTTPException, discord.Forbidden):
						return

	@commands.Cog.listener(name='on_message')
	async def ldm_del(self, message):
		if message.channel.id == 584817867166449703:
			e = message.embeds[0].description if len(message.embeds) > 0 else 'whatever'
			for mention in self.last_down_msg.keys():
				if str(mention) in e:  # not accurate but whatever
					try:
						await self.last_down_msg[mention].delete()
					except (discord.HTTPException, discord.NotFound):
						return
					finally:
						del self.last_down_msg[mention]

		elif message.guild.id == 620697381238734848:  # brick vent
			if message.author.bot or message.content.startswith('!bypass'):
				return
			if message.channel.name.endswith('add-partner'):
				try:
					a, *b = message.content.split(' ')
				except ValueError:
					return await message.channel.send("Please provide the message as `<members> <ad>`")
				try:
					members = int(a)
				except ValueError:
					await message.channel.send("Please provide the message in the following format:\n<member count> <ad>", delete_after=15)
					return await message.delete(delay=15)
				else:
					ad = ' '.join(b)
					channel = discord.utils.get(message.guild.text_channels, name='👑-partners')
					if channel:
						ctx = await self.bot.get_context(message)
						if members < 100:
							ad = await commands.clean_content().convert(ctx, ad)
						else:
							ad = ad
						await channel.send(ad)
						await channel.send("<------------------------------>")
						return await message.channel.send("Sent.")
					else:
						return await message.content.send("Unable to find partner channel.")

	@tasks.loop(minutes=10)
	async def check_if_tester(self):
		members = discord.utils.get(self.bot.guilds, id=606866057998762023).members
		role = discord.utils.get(members[0].guild.roles, name="Official Tester")
		for guild in self.bot.guilds:
			if guild.owner in members:
				member = discord.utils.get(members, id=guild.owner.id)
				if 'Official Tester' not in [x.name for x in member.roles]:
					await member.add_roles(role, reason="Auto add - bot in user's guild(s).")
				continue


def setup(bot):
	bot.add_cog(ExclusiveGuildStuff(bot))

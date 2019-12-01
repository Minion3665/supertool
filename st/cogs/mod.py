import datetime
import json
import typing
from random import choice
from typing import Union as U
import asyncio

import discord
from discord.ext import commands
from utils.converters import ago_time, fix_time
from utils import checks
import random

class CriticalDumpError(Exception):
	pass

class HierarchyError(Exception):
	pass
class TopHigher(HierarchyError):
	pass


class ModTools:

	@classmethod
	async def validate_hierarchy(cls, *, top: discord.Role, current: discord.Role, exact: bool = True):
		"""Validates role hierarchy.

		top should be the highest role, for example, target's top_role. current should be author's top_role. etc...
		`exact` = >= vs `fuzzy` = >"""
		if exact:
			if top >= current:
				raise TopHigher
			else:
				return True
		else:
			if top > current:
				raise TopHigher
			else:
				return True


class Mod(commands.Cog, name="Moderation"):
	def __init__(self, bot):
		self.bot = bot

	async def do_log(self, ctx, *, event: str, channel: discord.TextChannel, target: U[discord.Member, discord.User], reason):
		case_dict = {
			"event": event,
			"channel_id": channel.id,
			"target_id": [target.id],
			"mod_id": ctx.author.id,
			"reason": reason,
			"case_id": random.randint(0, 999)
		}
		e = discord.Embed(
			title=event,
			description=f"**Mod:** {ctx.author.mention} (`{ctx.author}`)\n**Target:** {target.mention} (`{str(target)}`)\n"
						f"**Reason:** {reason}",
			color=discord.Color.blurple(),
			timestamp=ctx.message.created_at,
			url=str(ctx.message.jump_url).replace(str(ctx.message.id), '')
		)
		e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(static_format='png'))
		try:
			modlogentry = await channel.send(embed=e)
			case_dict["entry_id"] = modlogentry.jump_url
		except:
			pass

		try:
			data = self.getdata(ctx)  # just check that they are in the modlog
		except:
			return
		else:
			_data = self.getdata(ctx, return_raw=True)
			_data[str(ctx.guild.id)]["cases"].append(case_dict)
			await self.setdata(ctx, data=_data)
			return True

	async def do_mass_user_log(self, ctx, *, users: list, event: str, channel: discord.TextChannel,
							target: U[discord.User, discord.Role]=None, reason=None, mod: discord.Member):
		case_dict = {
			"event": event,
			"channel_id": channel.id,
			"target_id": [x.id for x in users],
			"mod_id": ctx.author.id,
			"reason": reason,
			"case_id": random.randint(0, 999)
		}
		if len(users) > 5:
			target = f"{', '.join([str(us.mention) for us in users[:3]])} and {len(users) - 3} more..."
		else:
			target = ', '.join([str(us) for us in users])
		e = discord.Embed(
			title=event,
			description=f"**Mod:** {ctx.author.mention} (`{ctx.author}`)\n**Targets:** {target}\n"
						f"**Reason:** {reason}",
			color=discord.Color.blurple(),
			timestamp=ctx.message.created_at,
			url=str(ctx.message.jump_url).replace(str(ctx.message.id), '')
		)
		e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(static_format='png'))
		try:
			modlogentry = await channel.send(embed=e)
			case_dict["entry_id"] = modlogentry.jump_url
		except:
			pass

		try:
			data = self.getdata(ctx)  # just check that they are in the modlog
		except:
			return
		else:
			_data = self.getdata(ctx, return_raw=True)
			_data[str(ctx.guild.id)]["cases"].append(case_dict)
			await self.setdata(ctx, data=_data)
			return True

	@staticmethod
	def getdata(ctx=None, id=None, *, always_return: bool = False, return_raw: bool = False):
		"""Get the data entry of a guild.
		:param ctx:
		:param always_return:"""
		if ctx.guild is None:
			raise commands.NoPrivateMessage(f"The 'getdata' method can't be used in DMs - a guild instance is required")
		with open('./data/mod.json', 'r') as file:
			data = json.load(file)
			if return_raw:
				return data
		i = str(ctx.guild.id)
		if i not in data.keys():
			data[i] = {
					"modlog": None,
					"eventlog": None,
					"cases": [],
				}
			if not always_return:
				raise KeyError(f"'{i}' not found in mod.json")
			else:
				return data, i
		return data[i]

	@staticmethod
	async def setdata(ctx, *, data: dict):
		"""Adds a modification to the mod file."""
		if ctx.guild is None:
			raise commands.NoPrivateMessage(f"The 'setdata' method can't be used in DMs - a guild instance is required")
		with open('./data/mod.json', 'w') as file:
			try:
				json.dump(data, file, indent=1, skipkeys=True, ensure_ascii=True)
				return True
			except (discord.DiscordException, Exception) as e:
				raise CriticalDumpError(f"{e}")

	def getchannel(self, ctx):
		d = self.getdata(ctx)
		channel = self.bot.get_channel(d["modlog"])
		return channel

	@commands.group(invoke_without_command=True)
	@commands.has_permissions(manage_guild=True)
	@commands.guild_only()
	async def modlog(self, ctx):
		"""Get the guild's modlog!

		Required permissions: manage server"""
		try:
			data = self.getdata(ctx)
		except commands.NoPrivateMessage:
			return  # what
		except KeyError:
			modlog = None
		else:  # all stuff did successfully
			modlog_id = data["modlog"]
			if modlog_id is None:
				modlog = None
			else:
				modlog = self.bot.get_channel(modlog_id)

		e = discord.Embed(description="", color=discord.Color.blue())
		if modlog is not None:
			e.description += f"Modlog: {modlog.mention} (`#{modlog.name}`)"
		else:
			e.description += f"Modlog: None set (`None`)"
		return await ctx.send(embed=e)

	@modlog.command()
	@commands.has_permissions(manage_guild=True)
	@commands.bot_has_permissions(manage_messages=True)
	@commands.guild_only()
	async def set(self, ctx, *, new_channel: discord.TextChannel = None):
		"""Set the guilds modlog. don't tell me a channel to remove your modlog.

		Required permissions: manage server"""
		try:
			data = self.getdata(ctx)
		except KeyError:
			data = self.getdata(ctx, always_return=True)
			if isinstance(data, tuple):
				data, _ = list(data)[0], list(data)[1]
				data[str(ctx.guild.id)] = {
					"modlog": None,
					"cases": []
				}
				data = data[str(ctx.guild.id)]
		if new_channel is None:
			channel = self.bot.get_channel(data['modlog'])
			e = discord.Embed(title="Modlog Channel Removed.",
							  description=f"Old: #{channel}",
							  color=discord.Color.dark_blue(),
							  timestamp=datetime.datetime.utcnow())
			av = str(ctx.author.avatar_url_as(static_format='png'))
			e.set_author(icon_url=av, name=str(ctx.author), url=ctx.message.jump_url)
			await channel.send(embed=e)

		else:
			if not new_channel.permissions_for(ctx.me).all_channel():
				try:
					await new_channel.set_permissions(ctx.me, overwrite=discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), None),
												  reason="ModLog Config")
				except discord.Forbidden:
					return await ctx.send("Sorry, but i couldn't add my permissions to the channel. please give me `manage roles` and try again.")
		if data["modlog"] is not None:
			try:
				channel = self.bot.get_channel(data['modlog'])
				e = discord.Embed(title="Modlog Channel Changed",
								description=f"Old: {channel.mention}\nNew: {new_channel.mention}",
								color=discord.Color.dark_blue(),
								timestamp=datetime.datetime.utcnow())
				av = str(ctx.author.avatar_url_as(static_format='png'))
				e.set_author(icon_url=av, name=str(ctx.author), url=ctx.message.jump_url)
				await channel.send(embed=e)
			except:  # eat errors, we dont care
				pass

		data["modlog"] = new_channel.id if new_channel else None
		_data = self.getdata(ctx, return_raw=True)
		_data[str(ctx.guild.id)] = data
		await self.setdata(ctx, data=_data)
		await ctx.send(f"Successfully {f'set your modlog channel to {new_channel.mention}' if new_channel else 'removed your modlog channel'}")

	@commands.command()
	@commands.has_permissions(ban_members=True)
	@commands.bot_has_permissions(ban_members=True, create_instant_invite=True)
	@commands.guild_only()
	async def softban(self, ctx, user: typing.Union[discord.Member, discord.User], *, reason: str = 'No Reason'):
		"""Soft Ban someone. this deletes the last 7 days of their messages by banning and instantly unbanning.

		the user will be DMd if they were in the server with a new invite, unless they weren't in the server in which
		case they will just be un/banned as normal.

		Required permissions: ban members"""
		if isinstance(user, discord.Member):
			try:
				await ModTools.validate_hierarchy(top=user.top_role, current=ctx.author.top_role)
			except TopHigher:
				return await ctx.send("You can't softban that person; they are too high.")
		if ctx.guild.system_channel is None:
			channel = choice([c for c in ctx.guild.text_channels if c.permissions_for(ctx.me).create_instant_invite])
			try:
				invite = await channel.create_invite(max_age=86400, max_uses=1)
			except:
				return await ctx.send("Unable to create invite.")
		else:
			try:
				invite = await ctx.guild.system_channel.create_invite(max_age=86400, max_uses=1)
			except:
				return await ctx.send("unable to get invite.")
		try:
			data = self.getdata(ctx, return_raw=True)
			i = str(ctx.guild.id)
			channel = await self.bot.fetch_channel(data[i]["modlog"])
			try:
				await self.do_log(ctx, event="softban", target=user, reason=reason, channel=channel)
			except Exception as e:
				try:
					await ctx.author.send(f"There was an error logging this case to your modlog channel.\n"
										  f"Please notify an administrator of the following error: {str(e)}")
				except discord.Forbidden:
					pass

		except KeyError:

			pass
		except (discord.NotFound, discord.Forbidden, discord.HTTPException):
			pass

		clean_reason = reason.replace('@eve', '@\u200Beve').replace('@&', '@\u200B&').replace('@he', '@\u200Bhe')
		await ctx.message.delete()
		if isinstance(user, discord.Member):
			try:
				await user.send(f"You have been SoftBanned in {ctx.guild} for {reason}. You can rejoin with {invite.url}")
			except discord.Forbidden:
				return
		await ctx.guild.ban(user, reason=reason, delete_message_days=7)
		await ctx.guild.unban(user, reason=f"Softban series 1 episode 2")
		await ctx.send(f"\U00002705 softbanned {user} for: {clean_reason}")

	@commands.command()
	@commands.bot_has_permissions(kick_members=True)
	@commands.has_permissions(kick_members=True)
	@commands.guild_only()
	async def kick(self, ctx, user: discord.Member, *, reason: str = 'No Reason'):
		"""Kick somebody from the server.

		your and the bot's top role must be higher then the user you are kicking.

		Required permissions: kick members"""
		c = await ModTools.validate_hierarchy(top=user.top_role, current=ctx.author.top_role)
		b = await ModTools.validate_hierarchy(top=user.top_role, current=ctx.guild.me.top_role)
		try:
			data = self.getdata(ctx, return_raw=True)
			i = str(ctx.guild.id)
			channel = await self.bot.fetch_channel(data[i]["modlog"])
			try:
				await self.do_log(ctx, event="kick", target=user, reason=reason, channel=channel)
			except Exception as e:
				try:
					await ctx.author.send(f"There was an error logging this case to your modlog channel.\n"
										  f"Please notify an administrator of the following error: {str(e)}")
				except discord.Forbidden:
					pass
		except KeyError:
			pass
		except (discord.NotFound, discord.Forbidden, discord.HTTPException):
			pass

		clean_reason = reason.replace('@eve', '@\u200Beve').replace('@&', '@\u200B&').replace('@he', '@\u200Bhe')
		await ctx.message.delete()
		if isinstance(user, discord.Member):
			try:
				await user.send(f"You have been kicked from {ctx.guild.name} with reason: {reason}")
			except discord.Forbidden as error:
				pass
		await user.kick(reason=reason)
		await ctx.send(f"\U00002705 kicked {user} for: {clean_reason}")

	@commands.command()
	@commands.has_permissions(ban_members=True)
	@commands.bot_has_permissions(ban_members=True, create_instant_invite=True)
	@commands.guild_only()
	async def ban(self, ctx, user: typing.Union[discord.Member, discord.User], *, reason: str = 'No Reason'):
		"""Ban someone. this deletes the last 7 days of their messages..


		Required permissions: ban members"""
		if isinstance(user, discord.Member):
			try:
				await ModTools.validate_hierarchy(top=user.top_role, current=ctx.author.top_role)
			except TopHigher:
				return await ctx.send("You can't ban that person; they are too high.")
		try:
			data = self.getdata(ctx, return_raw=True)
			i = str(ctx.guild.id)
			channel = await self.bot.fetch_channel(data[i]["modlog"])
			try:
				await self.do_log(ctx, event="ban", target=user, reason=reason, channel=channel)
			except Exception as e:
				try:
					await ctx.author.send(f"There was an error logging this case to your modlog channel.\n"
										  f"Please notify an administrator of the following error: {str(e)}")
				except discord.Forbidden:
					pass

		except KeyError:

			pass
		except (discord.NotFound, discord.Forbidden, discord.HTTPException):
			pass

		clean_reason = reason.replace('@eve', '@\u200Beve').replace('@&', '@\u200B&').replace('@he', '@\u200Bhe')
		await ctx.message.delete()
		if isinstance(user, discord.Member):
			try:
				await user.send(f"You have been Banned in {ctx.guild} for {reason}.")
			except discord.Forbidden:
				return
		await ctx.guild.ban(user, reason=reason, delete_message_days=7)
		await ctx.send(f"\U00002705 banned {user} for: {clean_reason}")

	# role management
	@commands.command()
	@commands.has_permissions(manage_roles=True)
	@commands.bot_has_permissions(manage_roles=True)
	@commands.guild_only()
	@checks.is_super_premium()
	async def massrole(self, ctx, roles: commands.Greedy[discord.Role], users: commands.Greedy[typing.Union[discord.Member, str]], forceadd: bool = False):
		"""Gives someone roles.

		user can be a member, 'all', 'bots' or 'humans.
		'forceadd' can be true/false. if true it will always give the user the role even if its in their roles, in which case false would remove it.

		Required Permissions: manage roles"""
		if len(roles) == 0:
			return await ctx.send(f"No roles detected. Remember roles are case sensitive.")
		paginator = commands.Paginator(prefix='```diff')
		async with ctx.channel.typing():
			for user in users:
				paginator.add_line(empty=True)
				if isinstance(user, str):
					if user.lower() not in ['all', 'bots', 'humans']:
						paginator.add_line(f"- {user.lower()}: not member, not in 'all', 'bots', 'humans'.")
						continue
					else:
						if user.lower() == 'all':
							users = ctx.guild.members
						elif user.lower() == 'bots':
							users = [x for x in ctx.guild.members if x.bot]
						elif user.lower() in 'humans':
							users = [x for x in ctx.guild.members if not x.bot]
						return await ctx.invoke(ctx.command, roles, users, forceadd)
				else:
					for role in roles:
						if role >= ctx.author.top_role:
							paginator.add_line(f"- @{role.name}: Your role is too low to add this role!")
							continue
						elif role >= ctx.guild.me.top_role:
							paginator.add_line(f"- @{role.name}: My role is too low!")
							continue
						else:
							if role in user.roles and not forceadd:
								try:
									await user.remove_roles(role, reason=f'addrole command, executed by {ctx.author}.')
									paginator.add_line(f'+ {user.display_name}, {role.name}: removed, success!')
									continue
								except (discord.Forbidden, Exception) as error:
									paginator.add_line(f'- {user.display_name}, {role.name}: {error}')
									continue
							elif role not in user.roles or forceadd:
								try:
									await user.add_roles(role, reason=f'addrole command, executed by {ctx.author}.')
									paginator.add_line(f'+ {user.display_name}, {role.name}: success!')
									continue
								except (discord.Forbidden, Exception) as error:
									paginator.add_line(f'- {user.display_name}, {role.name}: {error}')
									continue

		for page_num, page in enumerate(paginator.pages, start=1):
			await ctx.send(page)
			await asyncio.sleep(2)
		await self.do_mass_user_log(ctx, users=users, event='addrole', channel=self.getchannel(ctx), mod=ctx.author)

	@commands.command(aliases=['ii', 'inviteinfo'])
	async def invite_info(self, ctx, *, invite: discord.Invite):
		"""Get an invite's information."""
		e = discord.Embed(title=invite.guild.name)
		try:
			max_age = fix_time(invite.max_age if invite.max_age else 0)
		except TypeError:
			max_age = 'Not Available (error)'
		max_uses = invite.max_uses
		cur_uses = invite.uses
		creator = invite.inviter
		channel = invite.channel
		temp = invite.temporary
		code = invite.code
		url = invite.url
		msg = await ctx.send(embed=discord.Embed(), delete_after=60)

		_ctx = ctx
		_ctx.guild = invite.guild
		try:
			creator = await commands.MemberConverter().convert(_ctx, str(creator))
		except:
			pass
		e.color = creator.color if isinstance(creator, discord.Member) else discord.Color.blurple()
		e.set_author(name=creator.display_name, icon_url=creator.avatar_url_as(static_format='png'))
		e.description = f"**Max Age:** {max_age}\n**Uses:** {cur_uses}/{max_uses}\n**Creator:** {creator.display_name}\n" \
						f"**Channel:** {channel.name}\n**temporary?:** {temp}\n[**Url:**]({url}) {url}"
		e.timestamp = invite.created_at if invite.created_at else datetime.datetime.utcnow()
		e.set_footer(text="This message will automatically delete after 60 seconds.")
		await msg.edit(embed=e)
		return await ctx.message.delete()

	@commands.group()
	@commands.has_permissions(manage_messages=True)
	@checks.is_premium()
	async def vcban(self, ctx, user: discord.Member, channel: typing.Optional[discord.VoiceChannel], *, reason: str = 'No Reason'):
		"""Ban someone from joining the Voice chat

		Premium only
		required permissions: mute members"""
		try:
			await ModTools.validate_hierarchy(top=user.top_role, current=ctx.author.top_role)
		except TopHigher:
			return await ctx.send("You can't vcban that person; they are too high.")
		else:
			if channel is None and user.voice is None:
				return await ctx.send("That user isnt connected to a voice channel.\nSupply a voice channel to ban them from that.")
			elif channel is None:
				channel = user.voice.channel
			try:
				await channel.set_permissions(user, connect=False, read_messages=False, reason=reason)
				if user.voice:
					if user.voice.channel == channel:
						await user.move_to(None, reason=reason)
			except:
				raise

			try:
				data = self.getdata(ctx)
			except KeyError:
				return await ctx.send(f"Invalid data received.")

			try:
				_reason = f'**Banned channel: {channel.name}**\n{reason}'
				status = await self.do_log(ctx, event='vuncban', channel=self.bot.get_channel(data['modlog']), target=user, reason=_reason)
			except Exception as e:
				await ctx.author.send(f"Error while logging. please inform an administrator of the following error: {e}")
		await ctx.message.delete()
		await ctx.send(f"Banned {user.display_name.replace('@', '@:')} from {channel.name}.")

	@commands.command()
	@commands.has_permissions(manage_messages=True)
	@checks.is_premium()
	async def vcunban(self, ctx, user: discord.Member, channel: typing.Optional[discord.VoiceChannel], *, reason: str = 'No Reasson'):
		"""Unban someone from joining the Voice chat

		Premium only
		required permissions: mute members"""
		try:
			await ModTools.validate_hierarchy(top=user.top_role, current=ctx.author.top_role)
		except TopHigher:
			return await ctx.send("You can't vcunban that person; they are too high.")
		else:
			if channel is None and user.voice is None:
				return await ctx.send("That user isnt connected to a voice channel.\nSupply a voice channel to ban them from that.")
			elif channel is None:
				channel = user.voice.channel
			try:
				await channel.set_permissions(user, overwrite=None, reason=reason)
			except:
				raise
			data = None
			_daa = None
			try:
				data = self.getdata(ctx)
				_data = self.getdata(ctx, return_raw=True)
				for case in _data[str(ctx.guild.id)]['cases']:
					if case['event'] == 'vcban' and case['target_id'][0] == user.id:
						_data[str(ctx.guild.id)]['cases'].remove(case)
				await self.setdata(ctx, data=_data)
			except KeyError as e:
				await ctx.send(e)
				return await ctx.send(f"Invalid data received.\n{data}\n\n{_data}")

			try:
				_reason = f'**Banned channel: {channel.name}**\n{reason}'
				status = await self.do_log(ctx, event='vuncban', channel=self.bot.get_channel(data['modlog']), target=user, reason=_reason)
			except Exception as e:
				await ctx.author.send(f"Error while logging. please inform an administrator of the following error: {e}")
		await ctx.message.delete()
		await ctx.send(f"Unanned {user.display_name.replace('@', '@:')} from {channel.name}.")

	@commands.command()
	@commands.bot_has_permissions(manage_messages=True)
	@commands.has_permissions(manage_messages=True)
	async def purge(self, ctx, amount: int, *, user: discord.User = None):
		"""Purge messages."""
		amount += 1
		def check(m):
			return m.author == user if user else m.author == m.author
		deleted = await ctx.channel.purge(limit=amount, check=check)
		await ctx.send(f"Deleted {len(deleted)} messages.\n*this message will close in 5 seconds.*", delete_after=7.5)

	@commands.Cog.listener(name="on_voice_state_update")
	async def on_vc_join(self, member, before, after):
		if before.channel is None and after.channel is not None:
			with open('./data/mod.json','r') as data:
				data = json.load(data)
				if str(member.guild.id) not in data.keys():
					return
				data = data[str(member.guild.id)]
			for case in data['cases']:
				if case['event'] == 'vcban' and member.id == case['target_id'][0]:
					await member.move_to(None, reason="Vc ban.")
					try:
						await member.send(f"You are forbidden from joining {str(after.channel)} for reason: "
											f"{case['reason']}. please ask an administrator to vcunban you.")
					except discord.Forbidden:
						return

	@commands.command()
	@commands.bot_has_permissions(ban_members=True)
	@commands.has_permissions(ban_members=True)
	async def unban(self, ctx, user: discord.User, *, reason: commands.clean_content = "No Reason."):
		"""Unban somebody from the guild. takes an ID, name or name#tags."""
		cleanreason = reason
		reason = str(reason)
		bans = await ctx.guild.bans()
		# await ctx.send(str(bans)[:2000])
		for reason, _user in bans:
			if _user.id == user.id:
				await ctx.guild.unban(_user, reason=reason)
				break
			else:
				continue
		else:
			return await ctx.send(f"That user is not in your ban list.")
		try:
			channel = self.getchannel(ctx)
			await self.do_log(ctx, event='Unban', channel=channel, reason=reason, target=user)
		except:
			await ctx.send(f"Error while logging.")
			raise
		finally:
			await ctx.send(f"Unbanned {user.display_name.replace('@', '@:')}, with reason: {cleanreason}.")

def setup(bot):
	bot.add_cog(Mod(bot))

# Nothing much here yet... come back later
import discord

async def safeSendEmbed(ctx, embed):
	embed.title = embed.title.strip()
	embed.description = embed.description.strip()
	if len(embed.title) > 256:
		embed.description = "..." + embed.title[253:] + " " + embed.description
		embed.title = embed.title[:253] + "..."
	if len(embed.description) > 2048:
		embed.description = embed.description[:2045] + "..."
	fields = embed.fields
	embed.clear_fields()
	newEmbed = embed.copy()
	messageList = []
	for field in fields:
		if len(field.name) > 256:
			field.value = "..." + field.name[253:] + " " + field.value
			field.name = field.name[:253] + "..."
		if len(field.value) > 1024:
			field.value = field.value[:1021] + "..."
		newEmbed.add_field(field.name, field.value, False)
		if len(newEmbed) > 6000 or len(newEmbed.fields > 25):
			newEmbed.remove_field(len(newEmbed.fields)-1)
			messageList.append(await ctx.send(embed=newEmbed))
			newEmbed = embed.copy()
			newEmbed.add_field(field.name, field.value, False)
	return messageList + [await ctx.send(embed=newEmbed)]

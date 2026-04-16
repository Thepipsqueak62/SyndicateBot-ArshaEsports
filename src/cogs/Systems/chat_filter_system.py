import discord
from discord.ext import commands


class WordBlacklist(commands.Cog):
    def __init__(self, client, blacklist_words):
        self.client = client
        self.blacklist_words = set(blacklist_words)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return  # Ignore messages from bots

        content_lower = message.content.lower()
        if any(word in content_lower for word in self.blacklist_words):
            await message.delete()

            # Send a direct message to the user
            dm_channel = await message.author.create_dm()
            await dm_channel.send(f"{message.author.mention}, please refrain from using inappropriate language.")


async def setup(client):
    # Set your blacklist words here
    blacklist_words = ["nigger"]

    # Add the cog to the client
    await client.add_cog(WordBlacklist(client, blacklist_words))

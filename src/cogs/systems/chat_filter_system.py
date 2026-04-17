import discord
import re
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
        if any(re.search(rf'\b{re.escape(word)}\b', content_lower) for word in self.blacklist_words):
            await message.delete()
            await message.channel.send(f"{message.author.mention}, please refrain from using inappropriate language.")

        await self.client.process_commands(message)


async def setup(client):
    blacklist_words = ["nigger"]
    await client.add_cog(WordBlacklist(client, blacklist_words))
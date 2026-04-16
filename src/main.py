import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.cogs.server_interactions.persistent.SetEventNotification import ArcheRage_Event_Notification
from cogs.PersistentEmbeds.SupportTicket import OpenTicketView
from src.cogs.server_interactions.persistent.classMenu_Dropdown import ClassSelectMenu
from shared_code.read_config import guild_id as get_guild_id  # Rename to avoid confusion
from webserver.web_server import keep_alive  # Removed 'src.' from path

load_dotenv()

intents = discord.Intents.all()


class Client(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            owner_id=1162664356232831007,
            intents=intents,
            case_insensitive=False,
            help_command=None,
        )

    async def on_ready(self):
        print(f"{self.user} Has Logged In")

        # Print the number of guilds the bot is in
        guild_count = len(self.guilds)
        print(f"Connected to {guild_count} guilds:")

        # Print information for each guild
        for guild in self.guilds:
            print(f" - {guild.name} (ID: {guild.id}) - {len(guild.members)} members")

        # Print the total number of users
        user_count = sum(len(guild.members) for guild in self.guilds)
        print(f"Total users across all guilds: {user_count}")

        await self.change_presence(
            activity=discord.Streaming(name="Throne & Liberty", url="https://www.twitch.tv/trashdarkrunner"),
            status=discord.Status.online
        )

        # FIXED: Call the function to get the actual guild_id value
        guild_id_value = get_guild_id()
        try:
            synced = await self.tree.sync(guild=discord.Object(id=int(guild_id_value)))
            print(f"Synced {len(synced)} command(s) to guild {guild_id_value}")
        except Exception as e:
            print(f"Sync error: {e}")

    async def setup_hook(self):
        self.add_view(OpenTicketView())
        self.add_view(ArcheRage_Event_Notification())
        self.add_view(ClassSelectMenu())

    async def load_cogs(self, path="cogs"):
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            if os.path.isdir(file_path):
                await self.load_cogs(file_path)
            elif filename.endswith(".py") and filename != "__init__.py":
                cog_name = file_path.replace(os.path.sep, '.')[:-3]
                try:
                    await self.load_extension(cog_name)
                    print(f"Loaded cog: {cog_name}")
                except Exception as e:
                    print(f"Failed to load {cog_name}: {e}")


async def main():
    bot = Client()
    await bot.load_cogs()

    # Start webserver in background if it's blocking
    # Option 1: If keep_alive is non-blocking
    keep_alive()

    # Option 2: If keep_alive blocks (starts Flask server)
    # import threading
    # threading.Thread(target=keep_alive, daemon=True).start()

    await bot.start(os.getenv("DISCORD_API_TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
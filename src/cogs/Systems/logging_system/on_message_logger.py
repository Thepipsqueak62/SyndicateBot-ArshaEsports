import discord
import pytz
from discord import app_commands
from discord.ext import commands
import sqlite3
from configparser import ConfigParser

from shared_code.read_config import get_guild_id


class MessageLogger(commands.Cog):
    def __init__(self, client, db_file):
        self.bot = client
        self.db_file = db_file

        # Connect to SQLite database
        self.conn = sqlite3.connect(self.db_file)
        self.c = self.conn.cursor()

        # Create table if not exists
        self.c.execute('''CREATE TABLE IF NOT EXISTS MessageLog (
                         guild_id TEXT,
                         log_channel_id TEXT,
                         PRIMARY KEY (guild_id, log_channel_id)
                         )''')
        self.conn.commit()

    def save_log_channel_id(self, guild_id, log_channel_id):
        self.c.execute("INSERT OR REPLACE INTO MessageLog (guild_id, log_channel_id) VALUES (?, ?)",
                       (guild_id, log_channel_id))
        self.conn.commit()

    def get_log_channel_id(self, guild_id):
        self.c.execute("SELECT log_channel_id FROM MessageLog WHERE guild_id = ?", (guild_id,))
        row = self.c.fetchone()
        return row[0] if row else None

    @app_commands.command(name="set-message-log", description="Sets the log channel for message logs")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx: discord.Interaction, channel_name: discord.TextChannel):
        try:
            guild = ctx.guild
            member = guild.get_member(ctx.user.id)

            if not member.guild_permissions.administrator and ctx.user.id != guild.owner_id:
                await ctx.response.send_message("Only server owners and administrators can use this command.",
                                                ephemeral=True)
                return

            log_channel = discord.utils.get(guild.channels, name=channel_name.name)
            guild_id = str(ctx.guild.id)
            self.save_log_channel_id(guild_id, str(channel_name.id))

            embed = discord.Embed(
                title="Message Log Channel Set",
                description=f"Log channel set to {channel_name.mention} for message logs.",
                color=discord.Color.green()
            )
            await ctx.response.send_message(embed=embed)
        except commands.MissingPermissions:
            await ctx.response.send_message("You don't have the required permissions to use this command.",
                                            ephemeral=True)
        except Exception as e:
            await ctx.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="reset-message-log", description="Resets the log channel for message logs")
    @commands.has_permissions(administrator=True)
    async def reset_log_channel(self, ctx: discord.Interaction, channel_name: discord.TextChannel):
        try:
            guild = ctx.guild
            member = guild.get_member(ctx.user.id)

            if not member.guild_permissions.administrator and ctx.user.id != guild.owner_id:
                await ctx.response.send_message("Only server owners and administrators can use this command.",
                                                ephemeral=True)
                return

            guild_id = str(ctx.guild.id)
            self.save_log_channel_id(guild_id, None)

            embed = discord.Embed(
                title="Message Log Channel Reset",
                description="Log channel for message logs has been reset.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)
        except commands.MissingPermissions:
            await ctx.response.send_message("You don't have the required permissions to use this command.",
                                            ephemeral=True)
        except Exception as e:
            await ctx.response.send_message(f"An error occurred: {e}", ephemeral=True)

    async def log_message(self, message, action):
        log_channel_id = self.get_log_channel_id(str(message.guild.id))
        if log_channel_id:
            log_channel = self.bot.get_channel(int(log_channel_id))
            if log_channel:
                author = message.author
                content = message.clean_content
                channel_mention = message.channel.mention
                channel_link = f"[#{message.channel.name}](https://discord.com/channels/{message.guild.id}/{message.channel.id})"

                embed = discord.Embed(
                    title=f"Message {action}",
                    description=f"**User**: {author.mention}\n**Content**: {content}\n**Channel**: {channel_mention} ({channel_link})",
                    color=discord.Color.blue()
                )
                timestamp = message.created_at.astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %I:%M %p %Z")
                embed.set_footer(text=f"Date/Time: {timestamp}")

                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        await self.log_message(message, "Deleted")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self.log_message(after, "Edited")


async def setup(client):
    db_file = DatabaseFile
    guild_id = get_guild_id()
    await client.add_cog(MessageLogger(client, db_file),guilds=[discord.Object(id=guild_id)])

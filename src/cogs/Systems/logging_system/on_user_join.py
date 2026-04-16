import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
from configparser import ConfigParser
from shared_code.read_config import get_guild_id

class MemberLogger(commands.Cog):
    def __init__(self, client, db_file):
        self.bot = client
        self.db_file = db_file

        # Connect to SQLite database
        self.conn = sqlite3.connect(self.db_file)
        self.c = self.conn.cursor()

        # Create tables if not exists
        self.c.execute('''CREATE TABLE IF NOT EXISTS JoinLeaveLog (
                         guild_id TEXT PRIMARY KEY,
                         log_channel_id TEXT
                         )''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS JoinLeaveEvents (
                         guild_id TEXT,
                         event_type TEXT,
                         user_id TEXT,
                         timestamp TEXT
                         )''')
        self.conn.commit()

    def save_log_channel_id(self, guild_id, log_channel_id):
        self.c.execute("INSERT OR REPLACE INTO JoinLeaveLog (guild_id, log_channel_id) VALUES (?, ?)", (guild_id, log_channel_id))
        self.conn.commit()

    def get_log_channel_id(self, guild_id):
        self.c.execute("SELECT log_channel_id FROM JoinLeaveLog WHERE guild_id = ?", (guild_id,))
        row = self.c.fetchone()
        return row[0] if row else None

    async def send_embed(self, channel, title, description, footer_text, color):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text=footer_text)
        await channel.send(embed=embed)

    @app_commands.command(name="set-join-leave-log-channel", description="Sets the log channel for member join and leave events")
    async def set_log_channel(self, ctx: discord.Interaction, channel_name: discord.TextChannel):
        try:
            guild = ctx.guild
            member = guild.get_member(ctx.user.id)

            if not member.guild_permissions.administrator and ctx.user.id != guild.owner_id:
                await ctx.response.send_message("Only server owners and administrators can use this command.",
                                                ephemeral=True)
                return

            guild_id = str(guild.id)
            self.save_log_channel_id(guild_id, str(channel_name.id))
            embed = discord.Embed(
                title="Join / Leave user Log has been Set",
                description=f"Log channel set to {channel_name.mention} for message logs.",
                color=discord.Color.green()
            )
            await ctx.response.send_message(embed=embed)

        except commands.MissingPermissions:
            await ctx.response.send_message("You don't have the required permissions to use this command.",
                                            ephemeral=True)
        except Exception as e:
            await ctx.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="reset-join-leave-log-channel",
                          description="Resets the log channel for member join and leave events")
    async def reset_log_channel(self, ctx: discord.Interaction, channel_name: discord.TextChannel):
        try:
            guild = ctx.guild
            member = guild.get_member(ctx.user.id)

            if not member.guild_permissions.administrator and ctx.user.id != guild.owner_id:
                await ctx.response.send_message("Only server owners and administrators can use this command.",
                                                ephemeral=True)
                return

            guild_id = str(guild.id)
            self.save_log_channel_id(guild_id, None)
            embed = discord.Embed(
                title="Join / Leave user Log has been Reset",
                description="Log channel has been reset for message logs.",
                color=discord.Color.green()
            )
            await ctx.response.send_message(embed=embed)

        except commands.MissingPermissions:
            await ctx.response.send_message("You don't have the required permissions to use this command.",
                                            ephemeral=True)
        except Exception as e:
            await ctx.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        log_channel_id = self.get_log_channel_id(str(member.guild.id))
        if log_channel_id:
            log_channel = self.bot.get_channel(int(log_channel_id))
            if log_channel:
                join_date = member.joined_at.strftime('%Y-%m-%d %H:%M:%S')
                footer_text = f"Joined: {join_date} UTC"
                await self.send_embed(log_channel, "Member Joined", f"{member.mention} has joined the server.", footer_text, discord.Color.green())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log_channel_id = self.get_log_channel_id(str(member.guild.id))
        if log_channel_id:
            log_channel = self.bot.get_channel(int(log_channel_id))
            if log_channel:
                leave_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                footer_text = f"Left: {leave_date} UTC"
                await self.send_embed(log_channel, "Member Left", f"{member.mention} has left the server.", footer_text, discord.Color.red())


async def setup(client):
    db_file = DatabaseFile
    guild_id = get_guild_id()
    await client.add_cog(MemberLogger(client, db_file),guilds=[discord.Object(id=guild_id)])

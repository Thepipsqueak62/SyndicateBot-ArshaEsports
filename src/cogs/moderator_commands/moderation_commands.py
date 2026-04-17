import discord
from discord import app_commands
from discord.ext import commands

from shared_code.data_handlers.read_config import get_guild_id
# NEED TO REFACTOR THIS INTO SINGULAR FILES



class Utility(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Utility Cog Loaded")

    @commands.command()
    async def sync(self, ctx) -> None:
        fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"Synced{len(fmt)} commands to the current guild")
        return

    @app_commands.command(name="ping", description="Ping Slash")
    async def ping(self, interactions: discord.Interaction):
        await interactions.response.send_message(f'Pong! {round(self.client.latency * 1000)}ms')

    @app_commands.command(name="edit-channel-name", description="Edit a channel's name")
    async def edit_channel_name(self, interaction: discord.Interaction, channel: discord.VoiceChannel, name: str):
        try:
            guild = interaction.guild
            executor = guild.get_member(interaction.user.id)

            # Define the required roles
            required_roles = ["Admin"]

            # Check if the user has any of the required roles
            if not any(discord.utils.get(guild.roles, name=role) in executor.roles for role in required_roles):
                # Additional checks for administrator or server owner
                if not executor.guild_permissions.administrator and executor.id != guild.owner_id:
                    await interaction.response.send_message(
                        "You don't have the required permissions to use this command.", ephemeral=True)
                    return
            await channel.edit(name=name)
            await interaction.response.send_message(f"Channel name changed to {name}")

        except discord.Forbidden:
            await interaction.response.send_message("I don't have sufficient permissions to edit the channel name.",
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)


    @app_commands.command(name='clear', description='Deletes a Set Amount of Messages')
    @commands.cooldown(1, 30, commands.BucketType.guild)  # 1 use per 30 seconds per guild
    async def delete_message(self, interaction: discord.Interaction, amount: int):
        try:
            guild = interaction.guild
            member = guild.get_member(interaction.user.id)

            if not member.guild_permissions.administrator and interaction.user.id != guild.owner_id:
                await interaction.response.send_message("Only server owners and administrators can use this command.",
                                                        ephemeral=True)
                return

            channel = interaction.channel
            if amount < 1:
                await interaction.response.send_message("Please provide a positive number.", ephemeral=True)
                return
            if amount > 100:
                await interaction.response.send_message("You cannot delete more than 100 messages at a time.",
                                                        ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)
            deleted_messages = await channel.purge(limit=amount)
            await interaction.followup.send(f"✅ Successfully deleted {len(deleted_messages)} messages")
        except discord.errors.Forbidden:
            await interaction.response.send_message("I don't have sufficient permissions to delete messages.",
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name='massdelete', description='Delete all messages in the chat')
    @commands.cooldown(1, 30, commands.BucketType.guild)  # 1 use per 30 seconds per guild
    async def mass_delete_messages(self, interaction):
        try:
            guild = interaction.guild
            member = guild.get_member(interaction.user.id)

            if not member.guild_permissions.administrator and interaction.user.id != guild.owner_id:
                await interaction.response.send_message("Only server owners and administrators can use this command.",
                                                        ephemeral=True)
                return

            channel = interaction.channel
            await interaction.response.defer(ephemeral=True)

            deleted_message_count = 0
            async for message in channel.history(limit=None):
                await message.delete()
                deleted_message_count += 1

            response_message = f"Successfully deleted {deleted_message_count} messages."
            await interaction.followup.send(response_message)
        except commands.MissingPermissions:
            await interaction.response.send_message("You don't have the required permissions to manage messages.",
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name='ban', description='Ban User From Guild')
    async def ban(self, interaction, member: discord.Member, *, reason: str = None):
        try:
            guild = interaction.guild
            executor = guild.get_member(interaction.user.id)  # The member who invoked the command

            # Check if the user has the required role or is the server owner or has administrator permissions
            required_role = discord.utils.get(guild.roles, name="Community Manager")
            if required_role not in executor.roles and not executor.guild_permissions.administrator and executor.id != guild.owner_id:
                await interaction.response.send_message("You don't have the required permissions to use this command.",
                                                        ephemeral=True)
                return

            # Ban the member
            await member.ban(reason=reason)
            await interaction.response.send_message(f"User {member} has been banned", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have sufficient permissions to ban members.",
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @ban.error
    async def ban_error(self, ctx, error):
        embed = discord.Embed(
            title="Permissions Error",
            description="You Don't Have Permissions to Use that ",
            colour=discord.Colour.green()
        )
        embed.set_footer(text="© Asicc.co")
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=embed,ephemeral=True)

    @app_commands.command(name='direct_message', description='Direct Message Announcements')
    @commands.has_permissions(manage_messages=True)
    async def dm(self, interaction, *, message: str = None):
        try:
            guild = interaction.guild
            executor = guild.get_member(interaction.user.id)  # The member who invoked the command

            # Check if the user has the required role or is the server owner or has administrator permissions
            required_role = discord.utils.get(guild.roles, name="Community Manager")
            if required_role not in executor.roles and not executor.guild_permissions.administrator and executor.id != guild.owner_id:
                await interaction.response.send_message("You don't have the required permissions to use this command.",
                                                        ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)  # Defer the initial response

            if message is not None:
                members = interaction.guild.members
                for member in members:
                    try:
                        await member.send(message)
                    except discord.Forbidden:
                        print(f"Failed to send message to {member}. User has DMs disabled or blocked the bot.")
                    except Exception as e:
                        print(f"An error occurred while sending a message to {member}: {e}")

                await interaction.followup.send("Messages sent to all members.", ephemeral=True)
            else:
                await interaction.followup.send("Please provide a message!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have sufficient permissions to send direct messages.",
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @dm.error
    async def dm_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="Permissions Error",
                description="You Don't Have Permissions to Use That Command",
                colour=discord.Colour.red()
            )
            await ctx.send(embed=embed,ephemeral=True)


async def setup(client):
    guild_id = get_guild_id()
    await client.add_cog(Utility(client), guilds=[discord.Object(id=guild_id)])


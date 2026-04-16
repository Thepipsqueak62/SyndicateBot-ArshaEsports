import discord
from discord.ext import commands
from discord import app_commands,ui
from shared_code.read_config import get_guild_id


class MyModal(ui.Modal, title="hello world"):
    name = ui.TextInput(label="Please Enter Name",
                        placeholder="John Doe",
                        custom_id="nameField",
                        style=discord.TextStyle.short)
    age = ui.TextInput(label="Please Enter Age",
                       placeholder="18+",
                       custom_id="ageField",
                       style=discord.TextStyle.short)
    about = ui.TextInput(label="Tell me about Yourself",
                         placeholder="I'm gay",
                         custom_id="aboutField",
                         style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        # Acknowledge the interaction with an ephemeral message
        await interaction.response.send_message("Processing your request...", ephemeral=True)

        # Replace with your desired channel ID
        target_channel_id = 1096075647312461835

        # Try to get the channel from the guild
        target_channel = interaction.guild.get_channel(target_channel_id)

        if target_channel:
            # Send the message to the specified channel
            await target_channel.send(
                f"Hello **{self.name.value}**! You are **{self.age.value}** years old and **{self.about.value}** about yourself")
        else:
            print("Target channel not found.")


class ModalTest(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Slash Cogs Loaded")

    @app_commands.command(name="modals", description="Ping Slash")
    async def modal(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MyModal())


async def setup(client):
    client.remove_command("help")
    guild_id = get_guild_id()
    await client.add_cog(ModalTest(client), guilds=[discord.Object(id=guild_id)])

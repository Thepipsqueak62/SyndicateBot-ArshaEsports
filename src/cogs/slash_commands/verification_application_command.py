import discord
from discord.ext import commands
from discord import app_commands
from shared_code.data_handlers.read_config import get_guild_id


class GuildApplicationCmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="guild_application", description="Application for NHF")
    async def guild_application(self, interaction, game_name: str, guild_pitch: str, character_info: discord.Attachment,
                                character_select_screen:discord.Attachment):
        # Fetch the member who used the command
        member = interaction.user
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url

        # First embed with member info
        main_EmbedForm = discord.Embed(title="✅ Guild Application Request",
                               description=f"{member.mention}",
                               color=discord.Color.blurple())
        main_EmbedForm.add_field(name="In-game Name:", value=f"{game_name}", inline=False)
        main_EmbedForm.add_field(name="Application Pitch", value=f"**{guild_pitch}**", inline=False)

        main_EmbedForm.set_thumbnail(url=avatar_url)

        # Image Embeds
        _charInfoEmbed = discord.Embed(color=discord.Color.blurple())
        _charInfoEmbed.set_image(url=character_info.url)
        # Second embed for the additional image
        _charSelectEmbed = discord.Embed(color=discord.Color.blurple())
        _charSelectEmbed.set_image(url=character_select_screen.url)

        # Send both embeds in one message
        await interaction.response.send_message(embeds=[main_EmbedForm,_charInfoEmbed,_charSelectEmbed])


async def setup(bot):
    guild_id = get_guild_id()
    await bot.add_cog(GuildApplicationCmd(bot), guilds=[discord.Object(id=guild_id)])

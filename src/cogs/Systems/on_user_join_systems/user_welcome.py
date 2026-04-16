import discord
from discord.ext import commands


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Create a welcome Embed
        welcome_embed = discord.Embed(
            title=f"Welcome to the server, {member.display_name}!",
            description="We're glad to have you here!",
            color=0x00ff00  # Green color
        )

        # Add a field to explain verification process
        welcome_embed.add_field(
            name="Verification Process",
            value="To complete your verification, Match Server Name to In-game Name please navigate to "
                  "<#1210487753196707921> and use the Slash Command `/verify` be sure to upload a picture of your "
                  "character"
                  "info in the field `character_info`"
                  "to upload a picture of your character info for verification "

        )

        # Fetch avatar URL from member.avatar
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        welcome_embed.set_thumbnail(url=avatar_url)

        # Send the welcome Embed via Direct Message
        try:
            await member.send(embed=welcome_embed)
        except discord.errors.Forbidden:
            print(f"Failed to send welcome DM to {member.name}#{member.discriminator}. Direct Messages are disabled.")

        # Get the welcome channel (you need to replace 'welcome_channel_id' with the actual ID of your welcome channel)
        welcome_channel = member.guild.get_channel(1210432912525099031)

        if welcome_channel:
            # Send the welcome Embed in the welcome channel
            await welcome_channel.send(embed=welcome_embed)


async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))

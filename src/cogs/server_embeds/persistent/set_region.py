import discord
from discord.ext import commands
from discord import app_commands


from shared_code.data_handlers.read_config import get_guild_id


class ClassSelectMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    options = [
        discord.SelectOption(label="NA", value="na", description="North American Region"),
        discord.SelectOption(label="EU", value="eu", description="Europe Region"),

    ]

    @discord.ui.select(placeholder="Please select your region", options=options, custom_id="select_region")
    async def menu_callback(self, interaction: discord.Interaction, select):
        select.disabled = True
        user = interaction.user
        guild = interaction.guild
        selected_value = select.values[0]

        # Define your role IDs corresponding to the options
        role_ids = {
            'na': 1494503660174970910,  # Replace with your role ID
            'eu': 1494503688839106651,

        }

        role_id = role_ids.get(selected_value)

        if role_id:
            role = guild.get_role(role_id)

            if role:
                # Check if the user already has the role
                for existing_role_id in role_ids.values():
                    existing_role = guild.get_role(existing_role_id)
                    if existing_role in user.roles:
                        await user.remove_roles(existing_role)

                # Add the role to the user
                await user.add_roles(role)
                await interaction.response.send_message(content=f"Region role <@&{role.id}> added.", ephemeral=True)
            else:
                await interaction.response.send_message(content="Error: Role not found.", ephemeral=True)
        else:
            await interaction.response.send_message(content="Error: Invalid selection.", ephemeral=True)


class drop_Down(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Select_Role_Dropdown")

    @app_commands.command(name="regionselection", description="Select your class of choice")
    @app_commands.checks.has_any_role("testrole2", "Helper")
    async def select_region(self, interaction: discord.Interaction):
        view = ClassSelectMenu()
        embed = discord.Embed(title="Region Selection", description="Use the dropdown menu to select your Region.",
                              color=0x00ff00)
        embed.add_field(name="Note",value="One Role Minimum")
        embed.set_image(url="https://i.ibb.co/zJrqKbf/sgfsdfgfdg.png")
        await interaction.response.send_message(embed=embed, view=view)

    @select_region.error
    async def select_region_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )


async def setup(client):
    guild_id = get_guild_id()
    await client.add_cog(drop_Down(client), guilds=[discord.Object(id=guild_id)])

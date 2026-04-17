import sqlite3
import discord
from discord.ext import commands
from discord import ui

from shared_code.data_handlers.read_config import get_database_file

DatabaseFile = get_database_file()

# SQLite3 database connection
conn = sqlite3.connect(DatabaseFile)
cursor = conn.cursor()


class shipsApplication(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Create separate tables if they don't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS apex_legends_users (
                            user_id INTEGER PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS valorant_users (
                            user_id INTEGER PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS counter_strike_users (
                            user_id INTEGER PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS overwatch_users (
                            user_id INTEGER PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS leauge_of_legends_users (
                                    user_id INTEGER PRIMARY KEY
                                )''')
        conn.commit()

    @commands.command()
    @commands.has_permissions(manage_messages=True)  # Permission Settings
    async def ships(self, ctx):
        embed = discord.Embed(title="Select Your Favorite Game",
                              description="Some description")
        embed.set_image(url="https://github.com/Moonsight91/discrap/blob/main/enoan.png?raw=true")
        embed.add_field(name=f" Game Selection", value="**Game List**\n"
                                                                           "- Apex legends\n"
                                                                           "- CS2\n"
                                                                           "- Valorant\n"
                                                                           "- Leauge of Legends\n"
                                                                           "- Overwatch\n")
        embed.set_thumbnail(url="https://na.archerage.to/static/images/logonew.png")
        view = Buttons()
        message = await ctx.send(embed=embed, view=view)
        await ctx.message.delete()

    @ships.error
    async def d_error(self, ctx, error):
        await ctx.send(str(error), ephemeral=True)


class Buttons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # Database Check
    def check_user_in_database(self, user_id, table_name):
        cursor.execute(f"SELECT user_id FROM {table_name} WHERE user_id =?", (user_id,))
        return cursor.fetchone() is not None

    # Button CallBack
    async def handle_button_click(self, interaction, button_label, table_name):
        errorIco = '<:icon_x:1238013626883899402>'
        user_id = interaction.user.id
        if self.check_user_in_database(user_id, table_name):
            await interaction.response.send_message(f"{errorIco} You have already applied for {button_label}.",
                                                    ephemeral=True)
        else:
            cursor.execute(f"INSERT INTO {table_name} (user_id) VALUES (?)", (user_id,))
            conn.commit()
            await interaction.response.send_message(f"✅You have successfully applied for {button_label}.",
                                                    ephemeral=True)

    @discord.ui.button(label="Apex Legends", custom_id="apexlegendsbtn", style=discord.ButtonStyle.blurple)
    async def enoan_button(self, interaction, button):
        await self.handle_button_click(interaction, "Apex Legends", "apex_legends_users")

    @discord.ui.button(label="Valorant", custom_id="valorantbtn", style=discord.ButtonStyle.blurple)
    async def growling_yawl_button(self, interaction, button):
        await self.handle_button_click(interaction, "Valorant", "valorant_users")

    @discord.ui.button(label="CS2", custom_id="cs2btn", style=discord.ButtonStyle.blurple)
    async def lutesong_junk_button(self, interaction, button):
        await self.handle_button_click(interaction, "CS2", "counter_strike_users")

    @discord.ui.button(label="Overwatch", custom_id="overwatchbtn", style=discord.ButtonStyle.blurple)
    async def eznan_cutter_button(self, interaction, button):
        await self.handle_button_click(interaction, "Overwatch", "overwatch_users")

    @discord.ui.button(label="Leauge of Legends", custom_id="lolbtn", style=discord.ButtonStyle.blurple)
    async def battle_clipper_button(self, interaction, button):
        await self.handle_button_click(interaction, "Leauge of Legends", "leauge_of_legends_users")

async def setup(client):
    await client.add_cog(shipsApplication(client))

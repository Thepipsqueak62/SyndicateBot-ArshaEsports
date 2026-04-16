import sqlite3
import discord
from discord.ext import commands
from discord import ui
from configparser import ConfigParser
config = ConfigParser()
config.read('config.ini')

DatabaseFile = config['Database']['DBName']


# SQLite3 database connection
conn = sqlite3.connect(DatabaseFile)
cursor = conn.cursor()


class shipsApplication(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Create separate tables if they don't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS enoan_users (
                            user_id INTEGER PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS growling_yawl_users (
                            user_id INTEGER PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS lutesong_junk_users (
                            user_id INTEGER PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS eznan_cutter_users (
                            user_id INTEGER PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS battle_clipper_users (
                                    user_id INTEGER PRIMARY KEY
                                )''')
        conn.commit()

    @commands.command()
    @commands.has_permissions(manage_messages=True)  # Permission Settings
    async def ships(self, ctx):
        embed = discord.Embed(title="Ship Application",
                              description="East Faction Ship Application")
        embed.set_image(url="https://github.com/Moonsight91/discrap/blob/main/enoan.png?raw=true")
        embed.add_field(name=f" (ONLY) Select Ships That you Own", value="**Ship List**\n"
                                                                           "- Enoan\n"
                                                                           "- Growling Yawl\n"
                                                                           "- Lutesong Junk\n"
                                                                           "- Eznan Cutter\n"
                                                                           "- Battle Clipper\n")
        embed.set_thumbnail(url="https://na.archerage.to/static/images/logonew.png")
        view = ShipButtons()
        message = await ctx.send(embed=embed, view=view)
        await ctx.message.delete()

    @ships.error
    async def d_error(self, ctx, error):
        await ctx.send(str(error), ephemeral=True)


class ShipButtons(discord.ui.View):
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

    @discord.ui.button(label="Enoan", custom_id="enoanBtn", style=discord.ButtonStyle.blurple)
    async def enoan_button(self, interaction, button):
        await self.handle_button_click(interaction, "Enoan", "enoan_users")

    @discord.ui.button(label="Growling Yawl", custom_id="growlingYawlBtn", style=discord.ButtonStyle.blurple)
    async def growling_yawl_button(self, interaction, button):
        await self.handle_button_click(interaction, "Growling Yawl", "growling_yawl_users")

    @discord.ui.button(label="Lutesong Junk", custom_id="lutesonJunk", style=discord.ButtonStyle.blurple)
    async def lutesong_junk_button(self, interaction, button):
        await self.handle_button_click(interaction, "Lutesong Junk", "lutesong_junk_users")

    @discord.ui.button(label="Eznan Cutter", custom_id="eznanBtn", style=discord.ButtonStyle.blurple)
    async def eznan_cutter_button(self, interaction, button):
        await self.handle_button_click(interaction, "Eznan Cutter", "eznan_cutter_users")

    @discord.ui.button(label="Battle Clipper", custom_id="battle_clipper_Btn", style=discord.ButtonStyle.blurple)
    async def battle_clipper_button(self, interaction, button):
        await self.handle_button_click(interaction, "battle_clipper", "battle_clipper_users")

async def setup(client):
    await client.add_cog(shipsApplication(client))

import sqlite3

import discord
import pytz
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import Embed, app_commands
from shared_code.read_config import guild_id as get_guild_id


class EventScheduler(commands.Cog):
    def __init__(self, client):
        self.client = client

        # Initialize database
        self.conn = sqlite3.connect('ArcheRageBotData.db')
        self.create_tables()

        # Setup scheduler
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('US/Eastern'))
        self._scheduler_started = False  # To track if the scheduler has been started already
        self.setup_scheduled_events()

    def create_tables(self):
        """Create tables to store event scheduling information."""
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_schedules (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_title TEXT NOT NULL,
            title_embed_icon TEXT NOT NULL,
            description TEXT,
            hour INTEGER NOT NULL,
            minute INTEGER NOT NULL,
            days_of_week TEXT NOT NULL,
            channel_id INTEGER NOT NULL,
            add_field_title,
            ping_role_id INTEGER,
            image_url TEXT,
            thumbnail_url TEXT,
            event_details_url TEXT,
            embed_color INTEGER DEFAULT 65280,
            is_active BOOLEAN DEFAULT 1,
            field_event_details TEXT,
            add_field_spawn_times TEXT
        )
        ''')
        self.conn.commit()

    def setup_scheduled_events(self):
        """Retrieve and schedule active events from the database."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM event_schedules WHERE is_active = 1')
        events = cursor.fetchall()

        for event in events:
            (event_id, event_title, title_embed_icon, description, hour, minute, days_of_week,
             channel_id, ping_role_id, image_url, thumbnail_url,
             event_details_url, embed_color, is_active,field_event_details,add_field_spawn_times) = event

            # Create cron trigger
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                day_of_week=days_of_week,
                timezone=pytz.timezone('US/Eastern')
            )

            # Add job to scheduler
            self.scheduler.add_job(
                self.create_send_message_func(
                    event_title, description, channel_id,
                    ping_role_id, image_url, thumbnail_url,
                    embed_color, title_embed_icon,field_event_details,add_field_spawn_times
                ),
                trigger
            )

    def create_send_message_func(self, event_title, description,
                                 channel_id, ping_role_id, image_url,
                                 thumbnail_url, embed_color, title_embed_icon,field_event_details,
                                 add_field_spawn_times
                                 ):
        """Create a customized send message function for each event."""

        async def send_message():
            channel = self.client.get_channel(channel_id)
            if not channel:
                print(f"Channel not found for event: {event_title}")
                return

            embed = Embed(
                title=f"{event_title} {title_embed_icon}!",
                description=f"{description} Event Starting",
                color=embed_color
            )
            if field_event_details:
                embed.add_field(name="Event Details",value=field_event_details,inline=False)
            if add_field_spawn_times:
                embed.add_field(name="Spawn Times", value=add_field_spawn_times,inline=False)
            # Conditionally add a field if provided
            if image_url:
                embed.set_image(url=image_url)

            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            if ping_role_id:
                await channel.send(f"<@&{ping_role_id}>", embed=embed)
            else:
                await channel.send(embed=embed)

        return send_message

    def add_event(self, event_title, title_embed_icon, description, hour, minute, days_of_week,
                  channel_id, ping_role_id=None, image_url=None,
                  thumbnail_url=None, event_details_url=None, embed_color=65280, field_event_details=None):
        """Add a new event to the database."""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO event_schedules 
        (event_title, title_embed_icon, description, hour, minute, days_of_week, 
        channel_id, ping_role_id, image_url, thumbnail_url, 
        event_details_url, embed_color,field_event_details,add_field_spawn_times) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event_title, title_embed_icon, description, hour, minute, days_of_week,
              channel_id, ping_role_id, image_url, thumbnail_url,
              event_details_url, embed_color,field_event_details))
        self.conn.commit()

        # Restart scheduler to include new event
        self.scheduler.shutdown()
        self.setup_scheduled_events()
        self.scheduler.start()

    @commands.command(name="add_event")
    async def add_event_command(self, ctx, event_title: str, title_embed_icon: str, hour: int, minute: int, days_of_week: str):
        """Basic command to add an event."""
        try:
            # Use the channel where the command was invoked
            channel_id = ctx.channel.id

            # Add event to the database
            self.add_event(
                event_title=event_title,
                title_embed_icon=title_embed_icon,
                description=None,  # Optional fields can be omitted for simplicity
                hour=hour,
                minute=minute,
                days_of_week=days_of_week,
                channel_id=channel_id,
            )

            await ctx.send(f"✅ Event '{event_title}' scheduled at {hour:02d}:{minute:02d} on {days_of_week}.")
        except Exception as e:
            await ctx.send(f"❌ Failed to add event: {e}")

    @app_commands.command(name="add_event", description="Add event to the database")
    async def add_event_command(self, interaction: discord.Interaction, event_title: str, title_embed_icon: str, hour: int, minute: int, days_of_week: str):
        """Basic command to add an event."""
        try:
            # Use the channel where the command was invoked
            channel_id = interaction.channel.id

            # Add event to the database
            self.add_event(
                event_title=event_title,
                title_embed_icon=title_embed_icon,
                description=None,  # Optional fields can be omitted for simplicity
                hour=hour,
                minute=minute,
                days_of_week=days_of_week,
                channel_id=channel_id,
            )

            await interaction.response.send_message(f"✅ Event '{event_title}' scheduled at {hour:02d}:{minute:02d} on {days_of_week}.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to add event: {e}")

    @commands.command(name="test_task")
    async def test_task_command(self, ctx):
        """Command to test if the scheduler is running."""
        try:
            self.scheduler.add_job(self.test_task, 'interval', seconds=10)
            await ctx.send("✅ Test task added to the scheduler!")
        except Exception as e:
            await ctx.send(f"❌ Failed to add test task: {e}")

    async def test_task(self):
        """A test task that runs every 10 seconds."""
        print("Test task executed!")

    @commands.Cog.listener()
    async def on_ready(self):
        print("Event Scheduler is ready.")
        if not self._scheduler_started:
            self.scheduler.start()
            self._scheduler_started = True


    def cog_unload(self):
        """Ensure database connection is closed when cog is unloaded."""
        self.conn.close()
        self.scheduler.shutdown()


async def setup(client):
    guild_id = get_guild_id()
    await client.add_cog(EventScheduler(client), guilds=[discord.Object(id=guild_id)])

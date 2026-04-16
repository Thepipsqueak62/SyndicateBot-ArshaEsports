import discord
from discord.ext import commands
from discord import ui, app_commands
import asyncio

from shared_code.read_config import get_guild_id

# ── Configuration ──────────────────────────────────────────────────────────────
ALLOWED_ROLES   = ["testrole2", "Helper"]          # Roles that can manage tickets
TICKET_CATEGORY = "Tickets"                    # Category name for ticket channels (set None to disable)
MAX_TICKETS     = 1                            # Max open tickets per user
# ───────────────────────────────────────────────────────────────────────────────


class CloseConfirmModal(ui.Modal, title="Close Ticket"):
    """Asks for an optional closing reason before deleting the channel."""

    reason = ui.TextInput(
        label="Closing reason (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="e.g. Issue resolved, no response, etc.",
        required=False,
        max_length=200,
    )

    def __init__(self, cog: "TicketSystem", channel: discord.TextChannel):
        super().__init__()
        self.cog     = cog
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        reason_text = str(self.reason) or "No reason provided."
        embed = discord.Embed(
            title="Ticket Closing",
            description=f"This ticket will be deleted in **5 seconds**.\n**Reason:** {reason_text}",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await self.cog._delete_ticket(self.channel)


class TicketControlView(ui.View):
    """Persistent view shown inside every ticket channel with a close button."""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket:close",
    )
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        cog: TicketSystem = interaction.client.cogs.get("TicketSystem")
        if cog is None:
            await interaction.response.send_message("Internal error — cog not found.", ephemeral=True)
            return

        # Only the ticket owner or staff may close
        if not cog._is_staff(interaction.user) and interaction.channel.id not in cog.tickets:
            await interaction.response.send_message("You don't have permission to close this ticket.", ephemeral=True)
            return

        if interaction.channel.id not in cog.tickets:
            await interaction.response.send_message("This is not a tracked ticket channel.", ephemeral=True)
            return

        await interaction.response.send_modal(CloseConfirmModal(cog, interaction.channel))


class OpenTicketView(ui.View):
    """Persistent view for the support panel message."""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Open a Ticket",
        style=discord.ButtonStyle.blurple,
        emoji="🎫",
        custom_id="ticket:create",
    )
    async def open_button(self, interaction: discord.Interaction, button: ui.Button):
        cog: TicketSystem = interaction.client.cogs.get("TicketSystem")
        if cog:
            await cog.create_ticket(interaction)


class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot              = bot
        # channel_id  → user_id
        self.tickets: dict[int, int]            = {}
        # user_id     → open ticket count
        self.user_ticket_count: dict[int, int]  = {}

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _is_staff(self, member: discord.Member) -> bool:
        return any(r.name in ALLOWED_ROLES for r in member.roles)

    async def _get_or_create_category(self, guild: discord.Guild) -> discord.CategoryChannel | None:
        if not TICKET_CATEGORY:
            return None
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY)
        return category

    async def _delete_ticket(self, channel: discord.TextChannel) -> None:
        user_id = self.tickets.pop(channel.id, None)
        if user_id is not None:
            self.user_ticket_count[user_id] = max(0, self.user_ticket_count.get(user_id, 1) - 1)
            if self.user_ticket_count[user_id] == 0:
                self.user_ticket_count.pop(user_id, None)
        try:
            await channel.delete(reason="Ticket closed.")
        except discord.HTTPException:
            pass

    # ── Core ticket creation ───────────────────────────────────────────────────

    async def create_ticket(self, interaction: discord.Interaction) -> None:
        user_id      = interaction.user.id
        open_tickets = self.user_ticket_count.get(user_id, 0)

        if open_tickets >= MAX_TICKETS:
            embed = discord.Embed(
                title="Ticket Limit Reached",
                description=f"You already have **{open_tickets}** open ticket(s). "
                            "Please wait for it to be resolved before opening another.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        # Defer so we have time to create the channel
        await interaction.response.defer(ephemeral=True)

        # Build permission overwrites
        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user:   discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            ),
        }
        # Grant staff roles read/send access
        for role in guild.roles:
            if role.name in ALLOWED_ROLES:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                )

        category     = await self._get_or_create_category(guild)
        channel_name = f"ticket-{interaction.user.name}".lower().replace(" ", "-")
        channel      = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"Support ticket for {interaction.user} (ID: {user_id})",
            reason=f"Ticket opened by {interaction.user}",
        )

        # Register ticket
        self.tickets[channel.id]             = user_id
        self.user_ticket_count[user_id]      = open_tickets + 1

        # Notify user (ephemeral follow-up)
        notify_embed = discord.Embed(
            title="Ticket Opened",
            description=f"Your ticket has been created: {channel.mention}\n"
                        "Our support team will be with you shortly.",
            color=discord.Color.blurple(),
        )
        await interaction.followup.send(embed=notify_embed, ephemeral=True)

        # Welcome message inside the ticket channel
        welcome_embed = discord.Embed(
            title="Support Ticket",
            description=(
                f"Welcome, {interaction.user.mention}!\n\n"
                "Please describe your issue in as much detail as possible. "
                "A member of our support team will assist you shortly.\n\n"
                "When your issue is resolved, press **Close Ticket** below."
            ),
            color=discord.Color.blurple(),
        )
        welcome_embed.set_footer(text=f"Opened by {interaction.user} • {interaction.user.id}")
        await channel.send(
            content=interaction.user.mention,
            embed=welcome_embed,
            view=TicketControlView(),
        )

    # ── Listeners ──────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        # Re-register persistent views so they survive restarts
        self.bot.add_view(OpenTicketView())
        self.bot.add_view(TicketControlView())
        print(f"[TicketSystem] Ready. Logged in as {self.bot.user}.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Clean up state when a ticket channel is deleted externally."""
        if not isinstance(channel, discord.TextChannel):
            return
        if channel.id not in self.tickets:
            return
        user_id = self.tickets.pop(channel.id)
        self.user_ticket_count[user_id] = max(0, self.user_ticket_count.get(user_id, 1) - 1)
        if self.user_ticket_count[user_id] == 0:
            self.user_ticket_count.pop(user_id, None)

    # ── Commands ───────────────────────────────────────────────────────────────

    @app_commands.command(name="support", description="Post the support panel in this channel.")
    @app_commands.checks.has_any_role(*ALLOWED_ROLES)
    async def support_slash(self, interaction: discord.Interaction):
        """Sends the ticket panel. Staff only."""
        embed = discord.Embed(
            title="Support",
            description=(
                "Need help? Click the button below to open a private support ticket.\n"
                "Our team will respond as soon as possible."
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="One ticket per member.")
        await interaction.channel.send(embed=embed, view=OpenTicketView())
        await interaction.response.send_message("Support panel posted.", ephemeral=True)

    @support_slash.error
    async def support_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)

    @app_commands.command(name="close", description="Close the current ticket channel.")
    @app_commands.checks.has_any_role(*ALLOWED_ROLES)
    async def close_slash(self, interaction: discord.Interaction):
        """Closes the ticket the command is used in. Staff only."""
        if interaction.channel.id not in self.tickets:
            await interaction.response.send_message("This is not an active ticket channel.", ephemeral=True)
            return
        await interaction.response.send_modal(CloseConfirmModal(self, interaction.channel))

    @close_slash.error
    async def close_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)

    # Legacy prefix command kept for convenience
    @commands.command(name="close_ticket")
    @commands.has_any_role(*ALLOWED_ROLES)
    async def close_prefix(self, ctx: commands.Context, channel: discord.TextChannel | None = None):
        """[prefix] Close a ticket. Defaults to the current channel."""
        target = channel or ctx.channel
        if target.id not in self.tickets:
            await ctx.send("That is not an active ticket channel.", delete_after=8)
            return
        embed = discord.Embed(
            title="Ticket Closing",
            description="This ticket will be deleted in **5 seconds**.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await self._delete_ticket(target)

    @close_prefix.error
    async def close_prefix_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingAnyRole):
            embed = discord.Embed(
                title="Permission Denied",
                description="You don't have permission to use that command.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed, delete_after=10)


async def setup(bot: commands.Bot):
    guild_id = get_guild_id()
    await bot.add_cog(TicketSystem(bot), guilds=[discord.Object(id=guild_id)])
    # Sync app commands — remove this after first run if you prefer manual syncing
    # await bot.tree.sync()
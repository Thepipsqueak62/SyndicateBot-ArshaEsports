import discord
from discord.ext import commands
import sqlite3
import random
from datetime import datetime, timedelta
from typing import Optional


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "economy.db"
        self._init_database()

    # ────────────────────────────────────────────────────────────────────────
    # DATABASE SETUP
    # ────────────────────────────────────────────────────────────────────────

    def _init_database(self):
        """Initialize all database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Users table - stores balances and timestamps
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS users
                           (
                               user_id
                               INTEGER
                               PRIMARY
                               KEY,
                               balance
                               INTEGER
                               DEFAULT
                               0,
                               last_daily
                               TIMESTAMP,
                               last_work
                               TIMESTAMP,
                               total_gambled
                               INTEGER
                               DEFAULT
                               0,
                               total_won
                               INTEGER
                               DEFAULT
                               0,
                               total_lost
                               INTEGER
                               DEFAULT
                               0
                           )
                           """)

            # Shop items table
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS shop_items
                           (
                               item_id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               name
                               TEXT
                               NOT
                               NULL,
                               description
                               TEXT,
                               price
                               INTEGER
                               NOT
                               NULL,
                               stock
                               INTEGER
                               DEFAULT
                               -
                               1,
                               role_id
                               INTEGER,
                               emoji
                               TEXT
                           )
                           """)

            # Inventory table
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS inventory
                           (
                               inventory_id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               user_id
                               INTEGER
                               NOT
                               NULL,
                               item_name
                               TEXT
                               NOT
                               NULL,
                               quantity
                               INTEGER
                               DEFAULT
                               1,
                               purchased_at
                               TIMESTAMP
                               DEFAULT
                               CURRENT_TIMESTAMP,
                               FOREIGN
                               KEY
                           (
                               user_id
                           ) REFERENCES users
                           (
                               user_id
                           )
                               )
                           """)

            # Transaction history
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS transactions
                           (
                               transaction_id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               sender_id
                               INTEGER,
                               receiver_id
                               INTEGER,
                               amount
                               INTEGER
                               NOT
                               NULL,
                               transaction_type
                               TEXT
                               NOT
                               NULL,
                               timestamp
                               TIMESTAMP
                               DEFAULT
                               CURRENT_TIMESTAMP
                           )
                           """)

            conn.commit()

    # ────────────────────────────────────────────────────────────────────────
    # HELPER FUNCTIONS
    # ────────────────────────────────────────────────────────────────────────

    def _get_user(self, user_id: int) -> dict:
        """Get user data from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "user_id": row[0],
                    "balance": row[1],
                    "last_daily": row[2],
                    "last_work": row[3],
                    "total_gambled": row[4],
                    "total_won": row[5],
                    "total_lost": row[6]
                }
            return None

    def _ensure_user(self, user_id: int) -> dict:
        """Ensure user exists, create if not."""
        user = self._get_user(user_id)
        if not user:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (user_id, balance) VALUES (?, ?)",
                    (user_id, 100)  # Starting bonus!
                )
                conn.commit()
            user = self._get_user(user_id)
        return user

    def _update_balance(self, user_id: int, amount: int, transaction_type: str = "admin", sender_id: int = None):
        """Update user balance and log transaction."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Update balance
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, user_id)
            )

            # Log transaction
            cursor.execute("""
                           INSERT INTO transactions (sender_id, receiver_id, amount, transaction_type)
                           VALUES (?, ?, ?, ?)
                           """, (sender_id, user_id, amount, transaction_type))

            conn.commit()

    def _add_item(self, user_id: int, item_name: str, quantity: int = 1):
        """Add item to user's inventory."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if user already has this item
            cursor.execute(
                "SELECT inventory_id, quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item_name)
            )
            row = cursor.fetchone()

            if row:
                # Update quantity
                cursor.execute(
                    "UPDATE inventory SET quantity = quantity + ? WHERE inventory_id = ?",
                    (quantity, row[0])
                )
            else:
                # Insert new item
                cursor.execute(
                    "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
                    (user_id, item_name, quantity)
                )

            conn.commit()

    def _format_coins(self, amount: int) -> str:
        """Format number with commas."""
        return f"{amount:,}"

    def _can_claim_daily(self, user_id: int) -> tuple[bool, Optional[timedelta]]:
        """Check if user can claim daily reward."""
        user = self._get_user(user_id)
        if not user or not user["last_daily"]:
            return True, None

        last_claim = datetime.fromisoformat(user["last_daily"])
        time_since = datetime.now() - last_claim
        cooldown = timedelta(hours=24)

        if time_since >= cooldown:
            return True, None

        return False, cooldown - time_since

    # ────────────────────────────────────────────────────────────────────────
    # CORE COMMANDS
    # ────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Economy Cog Loaded")

    @commands.command(name="bal", aliases=["balance", "money"])
    async def balance(self, ctx, target: Optional[discord.Member] = None):
        """Check your balance or someone else's."""
        target = target or ctx.author
        user = self._ensure_user(target.id)

        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Balance",
            description=f"**{self._format_coins(user['balance'])}** coins",
            color=discord.Color.gold()
        )

        # Add stats if it's the user checking themselves
        if target.id == ctx.author.id and user['total_gambled'] > 0:
            win_rate = (user['total_won'] / user['total_gambled']) * 100
            embed.add_field(
                name="📊 Gambling Stats",
                value=f"Win Rate: {win_rate:.1f}%\n"
                      f"Total Gambled: {self._format_coins(user['total_gambled'])}\n"
                      f"Won: {self._format_coins(user['total_won'])}\n"
                      f"Lost: {self._format_coins(user['total_lost'])}",
                inline=False
            )

        embed.set_footer(text=f"User ID: {target.id}")
        await ctx.send(embed=embed)

    @commands.command(name="daily")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def daily(self, ctx):
        """Claim your daily reward!"""
        user_id = ctx.author.id
        self._ensure_user(user_id)

        can_claim, remaining = self._can_claim_daily(user_id)

        if not can_claim:
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            embed = discord.Embed(
                title="⏰ Daily Reward on Cooldown",
                description=f"Come back in **{hours}h {minutes}m**!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Random reward between 200-1000 coins
        reward = random.randint(200, 1000)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?",
                (reward, datetime.now().isoformat(), user_id)
            )
            cursor.execute("""
                           INSERT INTO transactions (receiver_id, amount, transaction_type)
                           VALUES (?, ?, ?)
                           """, (user_id, reward, "daily"))
            conn.commit()

        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"You received **{self._format_coins(reward)}** coins!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Come back in 24 hours for more!")
        await ctx.send(embed=embed)

    @commands.command(name="work")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour cooldown
    async def work(self, ctx):
        """Work to earn some coins!"""
        user_id = ctx.author.id
        self._ensure_user(user_id)

        # Random jobs with different payouts
        jobs = [
            ("🍕 Pizza Delivery", random.randint(50, 150)),
            ("💻 Freelance Coding", random.randint(100, 300)),
            ("🏪 Convenience Store Clerk", random.randint(60, 180)),
            ("🚗 Uber Driver", random.randint(80, 250)),
            ("📦 Warehouse Worker", random.randint(70, 200)),
            ("☕ Barista", random.randint(50, 140)),
        ]

        job_name, payout = random.choice(jobs)

        # Bonus chance (10% chance for double pay)
        if random.random() < 0.1:
            payout *= 2
            bonus_text = " **BONUS! Double pay!** 🌟"
        else:
            bonus_text = ""

        self._update_balance(user_id, payout, "work")

        embed = discord.Embed(
            title=f"💼 {job_name}",
            description=f"You earned **{self._format_coins(payout)}** coins!{bonus_text}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Come back in 1 hour to work again!")
        await ctx.send(embed=embed)

    @commands.command(name="pay", aliases=["send", "transfer"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pay(self, ctx, target: discord.Member, amount: int):
        """Send money to another user."""
        if target.id == ctx.author.id:
            await ctx.send("❌ You can't send money to yourself!")
            return

        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return

        sender = self._ensure_user(ctx.author.id)

        if sender["balance"] < amount:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=f"You only have **{self._format_coins(sender['balance'])}** coins!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        self._ensure_user(target.id)
        self._update_balance(ctx.author.id, -amount, "transfer_sent", target.id)
        self._update_balance(target.id, amount, "transfer_received", ctx.author.id)

        embed = discord.Embed(
            title="💸 Payment Successful!",
            description=f"You sent **{self._format_coins(amount)}** coins to {target.mention}!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

        # Notify receiver
        try:
            notify_embed = discord.Embed(
                title="💰 Payment Received!",
                description=f"{ctx.author.mention} sent you **{self._format_coins(amount)}** coins!",
                color=discord.Color.gold()
            )
            await target.send(embed=notify_embed)
        except:
            pass  # DMs might be closed

    # ────────────────────────────────────────────────────────────────────────
    # GAMBLE COMMANDS
    # ────────────────────────────────────────────────────────────────────────

    @commands.command(name="gamble", aliases=["bet"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gamble(self, ctx, amount: int):
        """Gamble your coins for a 50/50 chance to double!"""
        user_id = ctx.author.id
        user = self._ensure_user(user_id)

        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return

        if amount > user["balance"]:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=f"You only have **{self._format_coins(user['balance'])}** coins!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # 50/50 chance
        won = random.random() < 0.5

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if won:
                # Win: Add amount (double the bet)
                new_balance = user["balance"] + amount
                transaction_type = "gamble_win"
                result_text = "WON"
                result_color = discord.Color.green()

                cursor.execute(
                    """UPDATE users
                       SET balance       = ?,
                           total_gambled = total_gambled + ?,
                           total_won     = total_won + ?
                       WHERE user_id = ?""",
                    (new_balance, amount, amount, user_id)
                )
            else:
                # Lose: Subtract amount
                new_balance = user["balance"] - amount
                transaction_type = "gamble_loss"
                result_text = "LOST"
                result_color = discord.Color.red()

                cursor.execute(
                    """UPDATE users
                       SET balance       = ?,
                           total_gambled = total_gambled + ?,
                           total_lost    = total_lost + ?
                       WHERE user_id = ?""",
                    (new_balance, amount, amount, user_id)
                )

            cursor.execute("""
                           INSERT INTO transactions (receiver_id, amount, transaction_type)
                           VALUES (?, ?, ?)
                           """, (user_id, amount if won else -amount, transaction_type))

            conn.commit()

        embed = discord.Embed(
            title=f"🎲 Gambling Result: You {result_text}!",
            description=f"Bet: **{self._format_coins(amount)}** coins\n"
                        f"New Balance: **{self._format_coins(new_balance)}** coins",
            color=result_color
        )

        if won:
            embed.add_field(name="🎉 Congratulations!", value="You doubled your bet!")
        else:
            embed.add_field(name="😢 Better luck next time!", value="50/50 odds weren't in your favor!")

        await ctx.send(embed=embed)

    @commands.command(name="slots")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slots(self, ctx, bet: int):
        """Play the slot machine! Match 3 for big wins."""
        user_id = ctx.author.id
        user = self._ensure_user(user_id)

        if bet <= 0:
            await ctx.send("❌ Bet must be positive!")
            return

        if bet > user["balance"]:
            await ctx.send(f"❌ You only have **{self._format_coins(user['balance'])}** coins!")
            return

        # Slot symbols with emojis
        symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]

        # Roll the slots
        roll1 = random.choice(symbols)
        roll2 = random.choice(symbols)
        roll3 = random.choice(symbols)

        # Determine winnings
        if roll1 == roll2 == roll3:
            if roll1 == "7️⃣":
                multiplier = 10  # JACKPOT!
            elif roll1 == "💎":
                multiplier = 5
            else:
                multiplier = 3
            won = True
            winnings = bet * multiplier
        elif roll1 == roll2 or roll2 == roll3 or roll1 == roll3:
            multiplier = 1.5
            won = True
            winnings = int(bet * multiplier)
        else:
            won = False
            winnings = bet

        if won:
            self._update_balance(user_id, winnings, "slots_win")
            result_color = discord.Color.green()
            result_text = f"You won **{self._format_coins(winnings)}** coins!"
        else:
            self._update_balance(user_id, -bet, "slots_loss")
            result_color = discord.Color.red()
            result_text = f"You lost **{self._format_coins(bet)}** coins!"

        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"**{roll1} | {roll2} | {roll3}**\n\n{result_text}",
            color=result_color
        )

        if roll1 == roll2 == roll3 == "7️⃣":
            embed.add_field(name="🎊 JACKPOT!!! 🎊", value="You hit the 7-7-7!", inline=False)

        await ctx.send(embed=embed)

    # ────────────────────────────────────────────────────────────────────────
    # SHOP COMMANDS
    # ────────────────────────────────────────────────────────────────────────

    @commands.group(name="shop", invoke_without_command=True)
    async def shop(self, ctx):
        """View items available in the shop."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, description, price, emoji FROM shop_items WHERE stock != 0 OR stock = -1 ORDER BY price")
            items = cursor.fetchall()

        if not items:
            embed = discord.Embed(
                title="🏪 Shop",
                description="The shop is currently empty!\nAdmins can add items with `!shop add`",
                color=discord.Color.blurple()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="🏪 Server Shop",
            description="Use `!buy <item>` to purchase an item!",
            color=discord.Color.blurple()
        )

        for name, desc, price, emoji in items[:10]:  # Limit to 10 items
            emoji_display = emoji if emoji else "🛒"
            embed.add_field(
                name=f"{emoji_display} {name} - {self._format_coins(price)} coins",
                value=desc or "No description",
                inline=False
            )

        embed.set_footer(text=f"Use !inventory to see your items")
        await ctx.send(embed=embed)

    @shop.command(name="add")
    @commands.has_permissions(administrator=True)
    async def shop_add(self, ctx, name: str, price: int, *, description: str = "No description"):
        """[Admin] Add an item to the shop."""
        if price <= 0:
            await ctx.send("❌ Price must be positive!")
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO shop_items (name, description, price) VALUES (?, ?, ?)",
                (name, description, price)
            )
            item_id = cursor.lastrowid
            conn.commit()

        embed = discord.Embed(
            title="✅ Item Added to Shop",
            description=f"**{name}**\nPrice: {self._format_coins(price)} coins\nDescription: {description}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Item ID: {item_id}")
        await ctx.send(embed=embed)

    @shop.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def shop_remove(self, ctx, *, name: str):
        """[Admin] Remove an item from the shop."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shop_items WHERE name = ?", (name,))

            if cursor.rowcount == 0:
                await ctx.send(f"❌ No item named '{name}' found!")
                return

            conn.commit()

        await ctx.send(f"✅ Removed '{name}' from the shop!")

    @commands.command(name="buy")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def buy(self, ctx, *, item_name: str):
        """Purchase an item from the shop."""
        user_id = ctx.author.id
        user = self._ensure_user(user_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, price, stock, role_id FROM shop_items WHERE name = ?",
                (item_name,)
            )
            item = cursor.fetchone()

            if not item:
                await ctx.send(f"❌ Item '{item_name}' not found in shop!")
                return

            name, price, stock, role_id = item

            if stock == 0:
                await ctx.send(f"❌ '{name}' is out of stock!")
                return

            if user["balance"] < price:
                await ctx.send(f"❌ You need **{self._format_coins(price)}** coins to buy this!\n"
                               f"You have: **{self._format_coins(user['balance'])}**")
                return

            # Process purchase
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))

            if stock > 0:
                cursor.execute("UPDATE shop_items SET stock = stock - 1 WHERE name = ?", (name,))

            cursor.execute("""
                           INSERT INTO transactions (sender_id, receiver_id, amount, transaction_type)
                           VALUES (?, ?, ?, ?)
                           """, (user_id, self.bot.user.id, price, "shop_purchase"))

            conn.commit()

        # Add to inventory
        self._add_item(user_id, name)

        # Give role if applicable
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                try:
                    await ctx.author.add_roles(role)
                except:
                    pass

        embed = discord.Embed(
            title="🛍️ Purchase Successful!",
            description=f"You bought **{name}** for **{self._format_coins(price)}** coins!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="New Balance",
            value=f"**{self._format_coins(user['balance'] - price)}** coins"
        )
        await ctx.send(embed=embed)

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx, target: Optional[discord.Member] = None):
        """View your inventory or someone else's."""
        target = target or ctx.author

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT item_name, quantity FROM inventory WHERE user_id = ? ORDER BY item_name",
                (target.id,)
            )
            items = cursor.fetchall()

        if not items:
            embed = discord.Embed(
                title=f"📦 {target.display_name}'s Inventory",
                description="This inventory is empty!\nBuy items from `!shop`",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title=f"📦 {target.display_name}'s Inventory",
                color=discord.Color.blue()
            )

            item_list = "\n".join([f"• {name} x{quantity}" for name, quantity in items])
            embed.description = item_list

        await ctx.send(embed=embed)

    # ────────────────────────────────────────────────────────────────────────
    # LEADERBOARD
    # ────────────────────────────────────────────────────────────────────────

    @commands.command(name="leaderboard", aliases=["lb", "rich", "top"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def leaderboard(self, ctx):
        """View the richest users in the server."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10"
            )
            top_users = cursor.fetchall()

        if not top_users:
            await ctx.send("No users found in the economy system yet!")
            return

        embed = discord.Embed(
            title="🏆 Richest Users Leaderboard",
            color=discord.Color.gold()
        )

        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"] + ["📊"] * 7

        for i, (user_id, balance) in enumerate(top_users, 1):
            user = self.bot.get_user(user_id)
            username = user.name if user else f"Unknown User ({user_id})"

            leaderboard_text += f"{medals[i - 1]} **#{i}** {username}: {self._format_coins(balance)} coins\n"

        embed.description = leaderboard_text
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        await ctx.send(embed=embed)

    # ────────────────────────────────────────────────────────────────────────
    # ADMIN COMMANDS
    # ────────────────────────────────────────────────────────────────────────

    @commands.command(name="addcoins", aliases=["give"])
    @commands.has_permissions(administrator=True)
    async def add_coins(self, ctx, target: discord.Member, amount: int):
        """[Admin] Add coins to a user."""
        self._ensure_user(target.id)
        self._update_balance(target.id, amount, "admin_add", ctx.author.id)

        embed = discord.Embed(
            title="✅ Coins Added",
            description=f"Added **{self._format_coins(amount)}** coins to {target.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="removecoins", aliases=["take"])
    @commands.has_permissions(administrator=True)
    async def remove_coins(self, ctx, target: discord.Member, amount: int):
        """[Admin] Remove coins from a user."""
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return

        self._ensure_user(target.id)
        self._update_balance(target.id, -amount, "admin_remove", ctx.author.id)

        embed = discord.Embed(
            title="✅ Coins Removed",
            description=f"Removed **{self._format_coins(amount)}** coins from {target.mention}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command(name="reseteco")
    @commands.has_permissions(administrator=True)
    async def reset_economy(self, ctx):
        """[Admin] Reset a user's economy data."""
        await ctx.send("⚠️ This will delete ALL economy data! Type `CONFIRM` to proceed.")

        def check(m):
            return m.author == ctx.author and m.content == "CONFIRM"

        try:
            await self.bot.wait_for('message', timeout=30.0, check=check)
        except:
            await ctx.send("Reset cancelled.")
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users")
            cursor.execute("DELETE FROM transactions")
            cursor.execute("DELETE FROM inventory")
            conn.commit()

        await ctx.send("✅ Economy data has been reset!")


async def setup(bot):
    await bot.add_cog(Economy(bot))
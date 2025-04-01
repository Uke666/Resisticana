import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
import logging
import random
import sqlalchemy as sa
from datetime import datetime, timedelta

from cogs.base_cog import BaseCog
from models import ItemCategory, Item, InventoryItem, Guild, User, GuildMember, CompanyInvestment, Transaction
from app import db

class Items(BaseCog):
    """Item shop and inventory management commands."""

    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

    def with_app_context(self, func):
        """Decorator to run a function within Flask application context."""
        from app import app
        with app.app_context():
            return func()

    @commands.command(name="shop", help="Browse the item shop")
    async def shop_prefix(self, ctx, category=None):
        """Browse the item shop with traditional prefix command."""
        await self.show_shop_categories(ctx) if not category else await self.show_category_items(ctx, category)

    @app_commands.command(name="shop", description="Browse the item shop")
    @app_commands.describe(category="Category of items to view")
    @app_commands.choices(category=[
        app_commands.Choice(name="Collectibles", value="Collectibles"),
        app_commands.Choice(name="Power-Ups", value="Power-Ups"),
        app_commands.Choice(name="Gameplay", value="Gameplay"),
        app_commands.Choice(name="Investments", value="Investments"),
        app_commands.Choice(name="Loot Boxes", value="Loot Boxes"),
        app_commands.Choice(name="Special Power-ups", value="Special Power-ups"),
    ])
    async def shop_slash(self, interaction: discord.Interaction, category: str = None):
        """Browse the item shop with slash command."""
        logging.info(f"Shop slash command called with category: '{category}'")
        if not category:
            await self.show_shop_categories_slash(interaction)
        else:
            # When category is provided through choices, it will be the exact name
            # which is more reliable than trying to match by ID or case-insensitive search
            await self.show_category_items_slash(interaction, category)

    async def show_shop_categories(self, ctx):
        """Show all item categories in the shop."""
        from app import app

        with app.app_context():
            # Get all categories from database
            categories = ItemCategory.query.all()

            if not categories:
                await ctx.send(embed=self.error_embed("No item categories found in the shop."))
                return

            # Create embed message
            embed = self.create_embed("Item Shop Categories", "Browse items by category:")

            for category in categories:
                # Get item count for this category
                item_count = Item.query.filter_by(category_id=category.id).count()
                embed.add_field(
                    name=f"{category.name} ({item_count} items)",
                    value=f"{category.description}\nUse `!shop {category.name}` to browse",
                    inline=False
                )

            embed.set_footer(text="Type the category name to browse items or 'exit' to cancel")

            # Send embed message
            message = await ctx.send(embed=embed)

            # Wait for user response
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                response = await self.bot.wait_for('message', check=check, timeout=60.0)

                if response.content.lower() == 'exit':
                    await ctx.send(embed=self.success_embed("Shop browsing canceled."))
                    return

                # Try to find category
                selected_category = None
                for category in categories:
                    if category.name.lower() == response.content.lower():
                        selected_category = category.name
                        break

                if selected_category:
                    await self.show_category_items(ctx, selected_category)
                else:
                    await ctx.send(embed=self.error_embed("Category not found. Please try again."))

            except asyncio.TimeoutError:
                await ctx.send(embed=self.error_embed("Shop browsing timed out."))

    async def show_shop_categories_slash(self, interaction: discord.Interaction):
        """Show all item categories in the shop (slash command version)."""
        from app import app

        with app.app_context():
            # Get all categories from database
            categories = ItemCategory.query.all()

            if not categories:
                await interaction.response.send_message(
                    embed=self.error_embed("No item categories found in the shop."),
                    ephemeral=True
                )
                return

            # Create embed message
            embed = self.create_embed("Item Shop Categories", "Browse items by category:")

            # Create dropdown for categories
            class CategorySelect(discord.ui.Select):
                def __init__(self, cog):
                    self.cog = cog
                    options = []

                    for category in categories:
                        # Get item count for this category
                        item_count = Item.query.filter_by(category_id=category.id).count()
                        # Log the category name that we're adding to options
                        logging.info(f"Adding category option: {category.name} with value {category.name}")
                        options.append(discord.SelectOption(
                            label=category.name,
                            description=f"{item_count} items available",
                            # Store exact category name to avoid case sensitivity issues
                            value=category.name
                        ))

                    super().__init__(
                        placeholder="Choose a category to browse",
                        min_values=1,
                        max_values=1,
                        options=options
                    )

                async def callback(self, interaction: discord.Interaction):
                    selected_category = self.values[0]
                    logging.info(f"Category dropdown selected: '{selected_category}'")
                    # Log the exact value that will be sent to show_category_items_slash
                    logging.info(f"Selected category value (unmodified): '{selected_category}'")
                    await self.cog.show_category_items_slash(interaction, selected_category)

            class CategoryView(discord.ui.View):
                def __init__(self, cog, timeout=60):
                    super().__init__(timeout=timeout)
                    self.add_item(CategorySelect(cog))

            for category in categories:
                # Get item count for this category
                item_count = Item.query.filter_by(category_id=category.id).count()
                embed.add_field(
                    name=f"{category.name} ({item_count} items)",
                    value=category.description,
                    inline=False
                )

            await interaction.response.send_message(
                embed=embed,
                view=CategoryView(self),
                ephemeral=False  # Make it visible to everyone
            )

    async def show_category_items(self, ctx, category_name):
        """Show items in a specific category."""
        from app import app

        with app.app_context():
            # Find category
            category = ItemCategory.query.filter(sa.func.lower(ItemCategory.name) == category_name.lower()).first()

            if not category:
                await ctx.send(embed=self.error_embed(f"Category '{category_name}' not found."))
                return

            # Get items in this category
            items = Item.query.filter_by(category_id=category.id).all()

            if not items:
                await ctx.send(embed=self.error_embed(f"No items found in category '{category.name}'."))
                return

            # Create embed message
            embed = self.create_embed(
                f"Shop: {category.name} Items",
                f"{category.description}\n\n*Use `!buy <item_id>` to purchase an item*"
            )

            for item in items:
                status = ""
                if item.is_limited and item.quantity is not None:
                    status = f" | {item.quantity} left" if item.quantity > 0 else " | **SOLD OUT**"

                consumable = " | Consumable" if item.is_consumable else ""
                tradeable = "" if item.is_tradeable else " | Not tradeable"

                embed.add_field(
                    name=f"ID: {item.id} - {item.name} - {item.price} coins{status}{consumable}{tradeable}",
                    value=item.description,
                    inline=False
                )

            # Add navigation buttons
            embed.set_footer(text="Type 'back' to return to categories or 'exit' to close the shop")

            # Send embed message
            await ctx.send(embed=embed)

            # Wait for user response
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                response = await self.bot.wait_for('message', check=check, timeout=60.0)

                if response.content.lower() == 'exit':
                    await ctx.send(embed=self.success_embed("Shop closed."))
                    return
                elif response.content.lower() == 'back':
                    await self.show_shop_categories(ctx)
                    return

                # Check if trying to buy
                if response.content.lower().startswith('!buy '):
                    try:
                        item_id = int(response.content.split(' ')[1])
                        await self.purchase_item(ctx, item_id)
                    except (IndexError, ValueError):
                        await ctx.send(embed=self.error_embed("Invalid item ID format. Use `!buy <item_id>`."))
                else:
                    await ctx.send(embed=self.error_embed("Invalid command. Type 'back' to return or 'exit' to close."))

            except asyncio.TimeoutError:
                await ctx.send(embed=self.error_embed("Shop browsing timed out."))

    async def show_category_items_slash(self, interaction: discord.Interaction, category_name):
        """Show items in a specific category (slash command version)."""
        from app import app
        from datetime import datetime

        with app.app_context():
            # Log the requested category name for debugging
            logging.info(f"Searching for category: '{category_name}'")

            # Get all categories for logging
            all_categories = ItemCategory.query.all()
            category_names = [c.name for c in all_categories]
            logging.info(f"Available categories: {category_names}")

            # Try direct match first
            category = ItemCategory.query.filter_by(name=category_name).first()
            logging.info(f"Direct exact name match result: {category}")

            # If not found (which should be rare with choices), try case-insensitive match
            if not category:
                category = ItemCategory.query.filter(sa.func.lower(ItemCategory.name) == category_name.lower()).first()
                logging.info(f"Case-insensitive match result: {category}")

            # If still not found, try normalized name matching
            if not category:
                normalized_input = category_name.lower().replace('-', '').replace('_', '').replace(' ', '')
                for c in all_categories:
                    normalized_cat = c.name.lower().replace('-', '').replace('_', '').replace(' ', '')
                    if normalized_cat == normalized_input:
                        category = c
                        break

                # Special handling for specific categories
                if normalized_input in ['specialpowerups', 'specialpowerup', 'specialpower-ups']:
                    category = next((c for c in all_categories if c.name.lower().replace(' ', '').replace('-', '') == 'specialpowerups'), None)
                elif normalized_input in ['lootboxes', 'lootbox', 'loot-boxes']:
                    category = next((c for c in all_categories if c.name.lower().replace(' ', '').replace('-', '') == 'lootboxes'), None)

            # If we still don't have a category after all our attempts, notify the user
            if not category:
                await interaction.response.send_message(
                    embed=self.error_embed(f"Category '{category_name}' not found."),
                    ephemeral=True
                )
                return

            # Get items in this category
            items = Item.query.filter_by(category_id=category.id).all()

            if not items:
                await interaction.response.send_message(
                    embed=self.error_embed(f"No items found in category '{category.name}'."),
                    ephemeral=True
                )
                return

            # Create embed message
            embed = self.create_embed(
                f"Shop: {category.name} Items",
                f"{category.description}\n\nClick the buttons below to purchase or go back"
            )

            for item in items:
                status = ""
                if item.is_limited and item.quantity is not None:
                    status = f" | {item.quantity} left" if item.quantity > 0 else " | **SOLD OUT**"

                consumable = " | Consumable" if item.is_consumable else ""
                tradeable = "" if item.is_tradeable else " | Not tradeable"

                embed.add_field(
                    name=f"ID: {item.id} - {item.name} - {item.price} coins{status}{consumable}{tradeable}",
                    value=item.description,
                    inline=False
                )

            # Create buttons for actions
            class ItemShopView(discord.ui.View):
                def __init__(self, cog, timeout=60):
                    super().__init__(timeout=timeout)
                    self.cog = cog

                @discord.ui.button(label="Back to Categories", style=discord.ButtonStyle.secondary)
                async def back_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("This is not your shop menu.", ephemeral=True)
                        return

                    await self.cog.show_shop_categories_slash(button_interaction)

                @discord.ui.button(label="Buy an Item", style=discord.ButtonStyle.primary)
                async def buy_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("This is not your shop menu.", ephemeral=True)
                        return

                    # Create item selection dropdown
                    options = []
                    for item in items:
                        if not (item.is_limited and item.quantity is not None and item.quantity <= 0):
                            options.append(discord.SelectOption(
                                label=f"{item.name} - {item.price} coins",
                                description=item.description[:50] + "..." if len(item.description) > 50 else item.description,
                                value=str(item.id)
                            ))

                    if not options:
                        await button_interaction.response.send_message(
                            embed=self.cog.error_embed("No items are available for purchase in this category."),
                            ephemeral=True
                        )
                        return

                    # Create and send dropdown
                    class ItemSelect(discord.ui.Select):
                        def __init__(self):
                            super().__init__(
                                placeholder="Choose an item to buy",
                                min_values=1,
                                max_values=1,
                                options=options
                            )

                        async def callback(self, select_interaction: discord.Interaction):
                            item_id = int(self.values[0])
                            await self.cog.purchase_item_slash(select_interaction, item_id)

                    class ItemSelectView(discord.ui.View):
                        def __init__(self, timeout=60):
                            super().__init__(timeout=timeout)
                            self.add_item(ItemSelect())

                    await button_interaction.response.send_message(
                        "Select an item to purchase:",
                        view=ItemSelectView(),
                        ephemeral=True
                    )

            # Send the embed with buttons
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=ItemShopView(self))
            else:
                await interaction.response.send_message(embed=embed, view=ItemShopView(self))

    async def show_category_items_by_id_slash(self, interaction: discord.Interaction, category_id: int):
        """Show items in a specific category by category ID (slash command version)."""
        from app import app
        from datetime import datetime

        with app.app_context():
            # Log the requested category ID for debugging
            logging.info(f"Searching for category with ID: {category_id}")

            # Get category by ID - direct database lookup
            category = ItemCategory.query.get(category_id)
            logging.info(f"Category lookup by ID result: {category}")

            if not category:
                await interaction.response.send_message(
                    embed=self.error_embed(f"Category with ID {category_id} not found."),
                    ephemeral=True
                )
                return

            # Get items in this category
            items = Item.query.filter_by(category_id=category.id).all()

            if not items:
                await interaction.response.send_message(
                    embed=self.error_embed(f"No items found in category '{category.name}'."),
                    ephemeral=True
                )
                return

            # Create embed message
            embed = self.create_embed(
                f"Shop: {category.name} Items",
                f"{category.description}\n\nClick the buttons below to purchase or go back"
            )

            for item in items:
                status = ""
                if item.is_limited and item.quantity is not None:
                    status = f" | {item.quantity} left" if item.quantity > 0 else " | **SOLD OUT**"

                consumable = " | Consumable" if item.is_consumable else ""
                tradeable = "" if item.is_tradeable else " | Not tradeable"

                embed.add_field(
                    name=f"ID: {item.id} - {item.name} - {item.price} coins{status}{consumable}{tradeable}",
                    value=item.description,
                    inline=False
                )

            # Create buttons for actions
            class ItemShopView(discord.ui.View):
                def __init__(self, cog, timeout=60):
                    super().__init__(timeout=timeout)
                    self.cog = cog

                @discord.ui.button(label="Back to Categories", style=discord.ButtonStyle.secondary)
                async def back_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("This is not your shop menu.", ephemeral=True)
                        return

                    await self.cog.show_shop_categories_slash(button_interaction)

                @discord.ui.button(label="Buy an Item", style=discord.ButtonStyle.primary)
                async def buy_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("This is not your shop menu.", ephemeral=True)
                        return

                    # Create item selection dropdown
                    options = []
                    for item in items:
                        if not (item.is_limited and item.quantity is not None and item.quantity <= 0):
                            options.append(discord.SelectOption(
                                label=f"{item.name} - {item.price} coins",
                                description=item.description[:50] + "..." if len(item.description) > 50 else item.description,
                                value=str(item.id)
                            ))

                    if not options:
                        await button_interaction.response.send_message(
                            embed=self.cog.error_embed("No items are available for purchase in this category."),
                            ephemeral=True
                        )
                        return

                    # Create and send dropdown
                    class ItemSelect(discord.ui.Select):
                        def __init__(self):
                            super().__init__(
                                placeholder="Choose an item to buy",
                                min_values=1,
                                max_values=1,
                                options=options
                            )

                        async def callback(self, select_interaction: discord.Interaction):
                            item_id = int(self.values[0])
                            await self.cog.purchase_item_slash(select_interaction, item_id)

                    class ItemSelectView(discord.ui.View):
                        def __init__(self, timeout=60):
                            super().__init__(timeout=timeout)
                            self.add_item(ItemSelect())

                    await button_interaction.response.send_message(
                        "Select an item to purchase:",
                        view=ItemSelectView(),
                        ephemeral=True
                    )

            # Send the embed with buttons
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=ItemShopView(self))
            else:
                await interaction.response.send_message(embed=embed, view=ItemShopView(self))

    @commands.command(name="buy", help="Buy an item from the shop")
    async def buy_prefix(self, ctx, item_id: int):
        """Buy an item from the shop with traditional prefix command."""
        await self.purchase_item(ctx, item_id)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item_id="The ID of the item to purchase")
    async def buy_slash(self, interaction: discord.Interaction, item_id: int):
        """Buy an item from the shop with slash command."""
        await self.purchase_item_slash(interaction, item_id)

    async def purchase_item(self, ctx, item_id: int):
        """Handle the purchase of an item."""
        guild_id = ctx.guild.id
        user_id = ctx.author.id

        from app import app
        from datetime import datetime

        with app.app_context():
            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()

            if not db_guild or not db_user:
                await ctx.send(embed=self.error_embed("Database error. Please try again later."))
                return

            # Get the item from database
            item = Item.query.get(item_id)

            if not item:
                await ctx.send(embed=self.error_embed(f"Item with ID {item_id} not found."))
                return

            # Check if item is limited and out of stock
            if item.is_limited and item.quantity is not None and item.quantity <= 0:
                await ctx.send(embed=self.error_embed(f"{item.name} is sold out!"))
                return

            # Check if user has enough money
            guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()

            if not guild_member:
                await ctx.send(embed=self.error_embed("Could not find your economy profile."))
                return

            if guild_member.wallet < item.price:
                await ctx.send(
                    embed=self.error_embed(
                        f"You don't have enough coins to buy {item.name}. " +
                        f"You need {item.price - guild_member.wallet} more coins."
                    )
                )
                return

            # Deduct price from user's wallet
            guild_member.wallet -= item.price

            # Add item to user's inventory
            inventory_item = InventoryItem.query.filter_by(
                user_id=db_user.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()

            if inventory_item:
                # User already has this item, increment quantity
                inventory_item.quantity += 1
                inventory_item.updated_at = datetime.utcnow()
            else:
                # First time user is buying this item
                inventory_item = InventoryItem(
                    user_id=db_user.id,
                    item_id=item.id,
                    guild_id=db_guild.id,
                    quantity=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(inventory_item)

            # If item is limited, decrease available quantity
            if item.is_limited and item.quantity is not None:
                item.quantity -= 1

            # Add transaction record
            transaction = Transaction(
                user_id=db_user.id,
                guild_id=db_guild.id,
                transaction_type="purchase",
                amount=-item.price,
                description=f"Purchased {item.name}"
            )
            db.session.add(transaction)

            # Commit changes to database
            db.session.commit()

            # Send success message
            await ctx.send(
                embed=self.success_embed(
                    f"You purchased {item.name} for {item.price} coins!\n\n" +
                    f"Your new balance: {guild_member.wallet} coins"
                )
            )

    async def purchase_item_slash(self, interaction: discord.Interaction, item_id: int):
        """Handle the purchase of an item (slash command version)."""
        guild_id = interaction.guild_id
        user_id = interaction.user.id

        from app import app
        from datetime import datetime

        with app.app_context():
            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()

            if not db_guild or not db_user:
                await interaction.response.send_message(
                    embed=self.error_embed("Database error. Please try again later."),
                    ephemeral=True
                )
                return

            # Get the item from database
            item = Item.query.get(item_id)

            if not item:
                await interaction.response.send_message(
                    embed=self.error_embed(f"Item with ID {item_id} not found."),
                    ephemeral=True
                )
                return

            # Check if item is limited and out of stock
            if item.is_limited and item.quantity is not None and item.quantity <= 0:
                await interaction.response.send_message(
                    embed=self.error_embed(f"{item.name} is sold out!"),
                    ephemeral=True
                )
                return

            # Check if user has enough money
            guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()

            if not guild_member:
                await interaction.response.send_message(
                    embed=self.error_embed("Could not find your economy profile."),
                    ephemeral=True
                )
                return

            if guild_member.wallet < item.price:
                await interaction.response.send_message(
                    embed=self.error_embed(
                        f"You don't have enough coins to buy {item.name}. " +
                        f"You need {item.price - guild_member.wallet} more coins."
                    ),
                    ephemeral=True
                )
                return

            # Deduct price from user's wallet
            guild_member.wallet -= item.price

            # Add item to user's inventory
            inventory_item = InventoryItem.query.filter_by(
                user_id=db_user.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()

            if inventory_item:
                # User already has this item, increment quantity
                inventory_item.quantity += 1
                inventory_item.updated_at = datetime.utcnow()
            else:
                # First time user is buying this item
                inventory_item = InventoryItem(
                    user_id=db_user.id,
                    item_id=item.id,
                    guild_id=db_guild.id,
                    quantity=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(inventory_item)

            # If item is limited, decrease available quantity
            if item.is_limited and item.quantity is not None:
                item.quantity -= 1

            # Add transaction record
            transaction = Transaction(
                user_id=db_user.id,
                guild_id=db_guild.id,
                transaction_type="purchase",
                amount=-item.price,
                description=f"Purchased {item.name}"
            )
            db.session.add(transaction)

            # Commit changes to database
            db.session.commit()

            # Send success message
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=self.success_embed(
                        f"You purchased {item.name} for {item.price} coins!\n\n" +
                        f"Your new balance: {guild_member.wallet} coins"
                    ),
                    ephemeral=False  # Show to everyone
                )
            else:
                await interaction.response.send_message(
                    embed=self.success_embed(
                        f"You purchased {item.name} for {item.price} coins!\n\n" +
                        f"Your new balance: {guild_member.wallet} coins"
                    ),
                    ephemeral=False  # Show to everyone
                )

    @commands.command(name="inventory", help="View your inventory")
    async def inventory_prefix(self, ctx):
        """View your inventory with traditional prefix command."""
        await self.show_inventory(ctx)

    @app_commands.command(name="inventory", description="View your inventory")
    async def inventory_slash(self, interaction: discord.Interaction):
        """View your inventory with slash command."""
        await self.show_inventory_slash(interaction)

    async def show_inventory(self, ctx):
        """Show a user's inventory."""
        guild_id = ctx.guild.id
        user_id = ctx.author.id

        from app import app

        with app.app_context():
            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()

            if not db_guild or not db_user:
                await ctx.send(embed=self.error_embed("Database error. Please try again later."))
                return

            # Get user's inventory items
            inventory_items = InventoryItem.query.filter_by(
                user_id=db_user.id,
                guild_id=db_guild.id
            ).all()

            if not inventory_items:
                await ctx.send(embed=self.error_embed("Your inventory is empty. Visit the shop to buy items!"))
                return

            # Create categories
            categories = {}

            for inv_item in inventory_items:
                item = Item.query.get(inv_item.item_id)
                if not item:
                    continue

                category_name = item.category.name if item.category else "Miscellaneous"

                if category_name not in categories:
                    categories[category_name] = []

                categories[category_name].append({
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "quantity": inv_item.quantity,
                    "consumable": item.is_consumable,
                    "tradeable": item.is_tradeable
                })

            # Create embed message
            embed = self.create_embed(
                f"{ctx.author.display_name}'s Inventory",
                "Your collection of items\n\n*Use `!use <item_id>` to use a consumable item*"
            )

            for category, items in categories.items():
                # Create formatted list of items for this category
                item_list = ""
                for item in items:
                    consumable = " | Consumable" if item["consumable"] else ""
                    tradeable = "" if item["tradeable"] else " | Not tradeable"

                    item_list += f"ID: {item['id']} - {item['name']} (x{item['quantity']}){consumable}{tradeable}\n"
                    item_list += f"*{item['description']}*\n\n"

                # Add field for this category
                embed.add_field(
                    name=f"📦 {category} ({len(items)} items)",
                    value=item_list or "No items",
                    inline=False
                )

            # Send embed message
            await ctx.send(embed=embed)

    async def show_inventory_slash(self, interaction: discord.Interaction):
        """Show a user's inventory (slash command version)."""
        guild_id = interaction.guild_id
        user_id = interaction.user.id

        from app import app

        with app.app_context():
            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()

            if not db_guild or not db_user:
                await interaction.response.send_message(
                    embed=self.error_embed("Database error. Please try again later."),
                    ephemeral=True
                )
                return

            # Get user's inventory items
            inventory_items = InventoryItem.query.filter_by(
                user_id=db_user.id,
                guild_id=db_guild.id
            ).all()

            if not inventory_items:
                await interaction.response.send_message(
                    embed=self.error_embed("Your inventory is empty. Visit the shop to buy items!"),
                    ephemeral=True
                )
                return

            # Create categories
            categories = {}

            for inv_item in inventory_items:
                item = Item.query.get(inv_item.item_id)
                if not item:
                    continue

                category_name = item.category.name if item.category else "Miscellaneous"

                if category_name not in categories:
                    categories[category_name] = []

                categories[category_name].append({
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "quantity": inv_item.quantity,
                    "consumable": item.is_consumable,
                    "tradeable": item.is_tradeable
                })

            # Create embed message
            embed = self.create_embed(
                f"{interaction.user.display_name}'s Inventory",
                "Your collection of items"
            )

            for category, items in categories.items():
                # Create formatted list of items for this category
                item_list = ""
                for item in items:
                    consumable = " | Consumable" if item["consumable"] else ""
                    tradeable = "" if item["tradeable"] else " | Not tradeable"

                    item_list += f"ID: {item['id']} - {item['name']} (x{item['quantity']}){consumable}{tradeable}\n"
                    item_list += f"*{item['description']}*\n\n"

                # Add field for this category
                embed.add_field(
                    name=f"📦 {category} ({len(items)} items)",
                    value=item_list or "No items",
                    inline=False
                )

            # Create buttons for actions
            class InventoryView(discord.ui.View):
                def __init__(self, cog, items, timeout=60):
                    super().__init__(timeout=timeout)
                    self.cog = cog
                    self.usable_items = [item for cat in categories.values() for item in cat if item["consumable"] and item["quantity"] > 0]

                @discord.ui.button(label="Use an Item", style=discord.ButtonStyle.primary, disabled=len([item for cat in categories.values() for item in cat if item["consumable"] and item["quantity"] > 0]) == 0)
                async def use_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("This is not your inventory.", ephemeral=True)
                        return

                    if not self.usable_items:
                        await button_interaction.response.send_message(
                            embed=self.cog.error_embed("You don't have any usable items in your inventory."),
                            ephemeral=True
                        )
                        return

                    # Create item selection dropdown
                    options = []
                    for item in self.usable_items:
                        options.append(discord.SelectOption(
                            label=f"{item['name']} (x{item['quantity']})",
                            description=item['description'][:50] + "..." if len(item['description']) > 50 else item['description'],
                            value=str(item['id'])
                        ))

                    # Create and send dropdown
                    class ItemSelect(discord.ui.Select):
                        def __init__(self):
                            super().__init__(
                                placeholder="Choose an item to use",
                                min_values=1,
                                max_values=1,
                                options=options
                            )

                        async def callback(self, select_interaction: discord.Interaction):
                            item_id = int(self.values[0])
                            await self.cog.use_item_slash(select_interaction, item_id)

                    class ItemSelectView(discord.ui.View):
                        def __init__(self, timeout=60):
                            super().__init__(timeout=timeout)
                            self.add_item(ItemSelect())

                    await button_interaction.response.send_message(
                        "Select an item to use:",
                        view=ItemSelectView(),
                        ephemeral=True
                    )

                @discord.ui.button(label="Gift an Item", style=discord.ButtonStyle.secondary, disabled=len([item for cat in categories.values() for item in cat if item["tradeable"] and item["quantity"] > 0]) == 0)
                async def gift_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("This is not your inventory.", ephemeral=True)
                        return

                    tradeable_items = [item for cat in categories.values() for item in cat if item["tradeable"] and item["quantity"] > 0]

                    if not tradeable_items:
                        await button_interaction.response.send_message(
                            embed=self.cog.error_embed("You don't have any tradeable items in your inventory."),
                            ephemeral=True
                        )
                        return

                    # We'll implement the gift UI later - it's more complex as it needs user selection
                    await button_interaction.response.send_message(
                        "To gift an item, use the `/gift` command with the item ID, quantity, and recipient.",
                        ephemeral=True
                    )

            # Send the embed with buttons
            await interaction.response.send_message(
                embed=embed,
                view=InventoryView(self, inventory_items),
                ephemeral=False  # Show to everyone
            )

    @commands.command(name="use", help="Use an item from your inventory")
    async def use_prefix(self, ctx, item_id: int):
        """Use an item from your inventory with traditional prefix command."""
        await self.use_item(ctx, item_id)

    @app_commands.command(name="use", description="Use an item from your inventory")
    @app_commands.describe(item_id="The ID of the item to use")
    async def use_slash(self, interaction: discord.Interaction, item_id: int):
        """Use an item from your inventory with slash command."""
        await self.use_item_slash(interaction, item_id)

    async def use_item(self, ctx, item_id: int):
        """Handle using an item from inventory."""
        guild_id = ctx.guild.id
        user_id = ctx.author.id

        from app import app

        with app.app_context():
            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()

            if not db_guild or not db_user:
                await ctx.send(embed=self.error_embed("Database error. Please try again later."))
                return

            # Get the item from database
            item = Item.query.get(item_id)

            if not item:
                await ctx.send(embed=self.error_embed(f"Item with ID {item_id} not found."))
                return

            # Check if user has the item
            inventory_item = InventoryItem.query.filter_by(
                user_id=db_user.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()

            if not inventory_item or inventory_item.quantity <= 0:
                await ctx.send(embed=self.error_embed(f"You don't have {item.name} in your inventory."))
                return

            # Check if item is consumable
            if not item.is_consumable:
                await ctx.send(embed=self.error_embed(f"{item.name} cannot be used. It's not a consumable item."))
                return

        # Process item usage based on its type
        try:
            # Get item properties
            properties = item.get_properties()
            effect_message = "You used " + item.name

            # Process different item types based on properties
            from models import GuildMember, Transaction
            guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()

            if not guild_member:
                await ctx.send(embed=self.error_embed("Could not find your economy profile."))
                return

            # Handle Company Shares
            if item.name == 'Company Shares':
                from models import Company
                # Get list of companies in guild
                companies = Company.query.filter_by(guild_id=db_guild.id).all()

                if not companies:
                    await ctx.send(embed=self.error_embed("There are no companies in this guild to invest in."))
                    return

                # Create embed with companies
                embed = self.create_embed(
                    "Select a Company to Invest In",
                    "Type the number of the company you want to invest in:"
                )

                for i, company in enumerate(companies):
                    embed.add_field(
                        name=f"{i+1}. {company.name}",
                        value=f"Value: {company.value} coins\nOwner: {company.owner_name}",
                        inline=False
                    )

                await ctx.send(embed=embed)

                # Wait for user selection
                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

                try:
                    selection = await self.bot.wait_for('message', check=check, timeout=60.0)
                    selection_num = int(selection.content)

                    if selection_num < 1 or selection_num > len(companies):
                        await ctx.send(embed=self.error_embed("Invalid selection. Please try again."))
                        return

                    selected_company = companies[selection_num - 1]

                    # Process company investment
                    # Get investment parameters
                    passive_income_rate = properties.get('passive_income_rate', 0.05)
                    duration_days = properties.get('duration_days', 30)

                    # Check if user already has shares in this company
                    try:
                        # Create investment record in database
                        from datetime import datetime, timedelta

                        import sqlalchemy as sa
                        with sa.create_engine(db.engine.url).connect() as conn:
                            existing = conn.execute(sa.text(
                                "SELECT * FROM company_investment WHERE investor_id = :investor_id AND company_id = :company_id"
                            ), {"investor_id": guild_member.id, "company_id": selected_company.id}).fetchone()

                            if existing:
                                await ctx.send(embed=self.error_embed(f"You already own shares in {selected_company.name}."))
                                return

                            # Create new investment
                            expires_at = datetime.utcnow() + timedelta(days=duration_days)
                            conn.execute(sa.text(
                                """
                                INSERT INTO company_investment 
                                (investor_id, company_id, amount_invested, percent_ownership, created_at, expires_at)
                                VALUES (:investor_id, :company_id, :amount, :percent, :created_at, :expires_at)
                                """
                            ), {
                                "investor_id": guild_member.id,
                                "company_id": selected_company.id,
                                "amount": item.price,  # Use item price as investment amount
                                "percent": passive_income_rate,
                                "created_at": datetime.utcnow(),
                                "expires_at": expires_at
                            })

                    except Exception as e:
                        logging.error(f"Error creating investment: {e}")
                        await ctx.send(embed=self.error_embed("Error creating investment. Please try again."))
                        return

                    effect_message += f" and invested in {selected_company.name}! You'll receive passive income for {duration_days} days."

                except ValueError:
                    await ctx.send(embed=self.error_embed("Invalid selection. Please enter a number."))
                    return

                except asyncio.TimeoutError:
                    await ctx.send(embed=self.error_embed("Investment timed out. Please try again."))
                    return

            # Handle Loot Boxes
            if hasattr(item, 'category') and item.category and item.category.name == 'Loot Boxes':
                min_reward = properties.get('min_reward', 100)
                max_reward = properties.get('max_reward', 500)
                import random
                reward_amount = random.randint(min_reward, max_reward)

                # Add money to user's wallet
                guild_member.wallet += reward_amount
                effect_message += f" and received {reward_amount} coins!"

                # Add transaction record
                transaction = Transaction(
                    user_id=db_user.id,
                    guild_id=db_guild.id,
                    transaction_type="loot_box",
                    amount=reward_amount,
                    description=f"Opened {item.name}"
                )
                db.session.add(transaction)

            # Handle Double Daily
            if item.name == 'Double Daily':
                # Store effect in user's instance properties
                instance_props = inventory_item.get_instance_properties()
                duration_days = properties.get('duration_days', 7)

                # Calculate expiration date
                from datetime import datetime, timedelta
                expiry_date = datetime.utcnow() + timedelta(days=duration_days)

                # Save to instance properties
                instance_props['double_daily'] = True
                instance_props['double_daily_expiry'] = expiry_date.isoformat()
                inventory_item.set_instance_properties(instance_props)

                effect_message += f" and will receive double daily rewards for {duration_days} days!"

            # Handle Robbery Shield
            if item.name == 'Robbery Shield':
                # Store effect in user's instance properties
                instance_props = inventory_item.get_instance_properties()
                duration_days = properties.get('duration_days', 3)

                # Calculate expiration date
                from datetime import datetime, timedelta
                expiry_date = datetime.utcnow() + timedelta(days=duration_days)

                # Save to instance properties
                instance_props['robbery_shield'] = True
                instance_props['robbery_shield_expiry'] = expiry_date.isoformat()
                inventory_item.set_instance_properties(instance_props)

                effect_message += f" and are now protected from robbery for {duration_days} days!"

            # Handle Quest Skip Token
            if item.name == 'Quest Skip Token':
                from models import ActiveQuest
                # Find active quest
                active_quest = ActiveQuest.query.filter_by(
                    user_id=db_user.id,
                    guild_id=db_guild.id,
                    completed=False
                ).first()

                if active_quest:
                    # Mark quest as completed and give reward
                    active_quest.completed = True
                    guild_member.wallet += active_quest.reward

                    # Add transaction for reward
                    transaction = Transaction(
                        user_id=db_user.id,
                        guild_id=db_guild.id,
                        transaction_type="quest_reward",
                        amount=active_quest.reward,
                        description=f"Quest completed (skipped): {active_quest.quest_title}"
                    )
                    db.session.add(transaction)

                    effect_message += f" and skipped quest '{active_quest.quest_title}', earning {active_quest.reward} coins!"
                else:
                    effect_message += " but you don't have any active quests to skip!"

            # Handle Bet Insurance
            if item.name == 'Bet Insurance':
                # Store effect in user's instance properties
                instance_props = inventory_item.get_instance_properties()
                refund_percent = properties.get('refund_percent', 75)

                # Set bet insurance
                instance_props['bet_insurance'] = True
                instance_props['refund_percent'] = refund_percent
                inventory_item.set_instance_properties(instance_props)

                effect_message += f" and will receive {refund_percent}% back if you lose your next bet!"

            # Legacy items support
            if "effect_type" in properties:
                effect_type = properties["effect_type"]

                # Economy boost items
                if effect_type == "money":
                    if "amount" in properties:
                        amount = int(properties["amount"])

                        # Add money to wallet
                        guild_member.wallet += amount
                        effect_message += f" and received {amount} coins!"

                        # Add transaction record
                        transaction = Transaction(
                            user_id=db_user.id,
                            guild_id=db_guild.id,
                            transaction_type="item_use",
                            amount=amount,
                            description=f"Used {item.name}"
                        )
                        db.session.add(transaction)

                # Role temp items
                elif effect_type == "temp_role":
                    if "role_id" in properties and "duration" in properties:
                        role_id = properties["role_id"]
                        duration = int(properties["duration"])  # Duration in minutes

                        try:
                            # Add role to user
                            role = ctx.guild.get_role(int(role_id))
                            if role:
                                await ctx.author.add_roles(role)
                                effect_message += f" and received the {role.name} role for {duration} minutes!"

                                # Schedule role removal
                                async def remove_role_later():
                                    await asyncio.sleep(duration * 60)
                                    try:
                                        await ctx.author.remove_roles(role)
                                        await ctx.author.send(f"Your temporary {role.name} role has expired.")
                                    except:
                                        pass

                                asyncio.create_task(remove_role_later())
                        except Exception as e:
                            logging.error(f"Error handling temporary role item: {e}")
                            effect_message += f", but there was an error applying the role effect."

            # Update inventory
            inventory_item.quantity -= 1
            inventory_item.last_used_at = datetime.utcnow()

            # If quantity is zero, consider removing the item
            if inventory_item.quantity <= 0:
                db.session.delete(inventory_item)

            # Commit changes
            db.session.commit()

            # Notify user of successful usage
            await ctx.send(embed=self.success_embed(effect_message))

        except Exception as e:
            with app.app_context():
                db.session.rollback()
            logging.error(f"Error during item usage: {e}")
            await ctx.send(embed=self.error_embed("An error occurred while using the item. Please try again."))

    async def use_item_slash(self, interaction: discord.Interaction, item_id: int):
        """Handle using an item from inventory (slash command version)."""
        guild_id = interaction.guild_id
        user_id = interaction.user.id

        from app import app

        with app.app_context():
            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()

            if not db_guild or not db_user:
                await interaction.response.send_message(
                    embed=self.error_embed("Database error. Please try again later."),
                    ephemeral=True
                )
                return

            # Get the item from database
            item = Item.query.get(item_id)

            if not item:
                await interaction.response.send_message(
                    embed=self.error_embed(f"Item with ID {item_id} not found."),
                    ephemeral=True
                )
                return

            # Check if user has the item
            inventory_item = InventoryItem.query.filter_by(
                user_id=db_user.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()

            if not inventory_item or inventory_item.quantity <= 0:
                await interaction.response.send_message(
                    embed=self.error_embed(f"You don't have {item.name} in your inventory."),
                    ephemeral=True
                )
                return

            # Check if item is consumable
            if not item.is_consumable:
                await interaction.response.send_message(
                    embed=self.error_embed(f"{item.name} cannot be used. It's not a consumable item."),
                    ephemeral=True
                )
                return

        # Process item usage based on its type
        try:
            # Get item properties
            properties = item.get_properties()
            effect_message = "You used " + item.name

            # Process different item types based on properties
            from models import GuildMember, Transaction
            guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()

            if not guild_member:
                await interaction.response.send_message(
                    embed=self.error_embed("Could not find your economy profile."),
                    ephemeral=True
                )
                return

            # Handle Company Shares
            if item.name == 'Company Shares':
                # We can't handle complex interactions in slash command response
                # Need to defer and follow up
                await interaction.response.defer()

                from models import Company
                # Get list of companies in guild
                companies = Company.query.filter_by(guild_id=db_guild.id).all()

                if not companies:
                    await interaction.followup.send(
                        embed=self.error_embed("There are no companies in this guild to invest in.")
                    )
                    return

                # Create a dropdown for company selection
                select_embed = self.create_embed(
                    "Select a Company",
                    f"Please select a company to invest in using the dropdown menu below."
                )

                # Create company selection options
                options = []
                for i, company in enumerate(companies):
                    options.append(discord.SelectOption(
                        label=company.name,
                        value=str(company.id),
                        description=f"Invest in {company.name}"
                    ))

                # Create the dropdown view
                class CompanySelectView(discord.ui.View):
                    def __init__(self, cog, timeout=60):
                        super().__init__(timeout=timeout)
                        self.cog = cog
                        self.selected_company = None

                    @discord.ui.select(
                        placeholder="Choose a company",
                        min_values=1,
                        max_values=1,
                        options=options
                    )
                    async def select_company(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                        if select_interaction.user.id != interaction.user.id:
                            await select_interaction.response.send_message(
                                "This is not your selection menu.", ephemeral=True
                            )
                            return

                        selected_id = int(select.values[0])
                        self.selected_company = next((c for c in companies if c.id == selected_id), None)

                        if self.selected_company:
                            # Process company investment
                            # Get investment parameters
                            passive_income_rate = properties.get('passive_income_rate', 0.05)
                            duration_days = properties.get('duration_days', 30)

                            # Check if user already has shares in this company
                            try:
                                # Create investment record in database
                                from datetime import datetime, timedelta

                                with sa.create_engine(db.engine.url).connect() as conn:
                                    existing = conn.execute(sa.text(
                                        "SELECT * FROM company_investment WHERE investor_id = :investor_id AND company_id = :company_id"
                                    ), {"investor_id": guild_member.id, "company_id": self.selected_company.id}).fetchone()

                                    if existing:
                                        await select_interaction.response.send_message(
                                            embed=self.cog.error_embed(f"You already own shares in {self.selected_company.name}."),
                                            ephemeral=True
                                        )
                                        return

                                    # Create new investment
                                    expires_at = datetime.utcnow() + timedelta(days=duration_days)
                                    conn.execute(sa.text(
                                        """
                                        INSERT INTO company_investment 
                                        (investor_id, company_id, amount_invested, percent_ownership, created_at, expires_at)
                                        VALUES (:investor_id, :company_id, :amount, :percent, :created_at, :expires_at)
                                        """
                                    ), {
                                        "investor_id": guild_member.id,
                                        "company_id": self.selected_company.id,
                                        "amount": item.price,  # Use item price as investment amount
                                        "percent": passive_income_rate,
                                        "created_at": datetime.utcnow(),
                                        "expires_at": expires_at
                                    })

                                # Use the item (reduce quantity)
                                inventory_item.quantity -= 1
                                if inventory_item.quantity <= 0:
                                    db.session.delete(inventory_item)
                                else:
                                    inventory_item.last_used_at = datetime.utcnow()

                                db.session.commit()

                                await select_interaction.response.send_message(
                                    embed=self.cog.success_embed(f"You invested in {self.selected_company.name}! You'll receive passive income for {duration_days} days.")
                                )

                                # Disable the view after use
                                self.stop()

                            except Exception as e:
                                logging.error(f"Error creating investment: {e}")
                                await select_interaction.response.send_message(
                                    embed=self.cog.error_embed("Error creating investment. Please try again."),
                                    ephemeral=True
                                )

                # Send the dropdown view
                await interaction.followup.send(embed=select_embed, view=CompanySelectView(self))
                return  # Early return to avoid further processing

            # Handle Loot Boxes
            if hasattr(item, 'category') and item.category and item.category.name == 'Loot Boxes':
                min_reward = properties.get('min_reward', 100)
                max_reward = properties.get('max_reward', 500)
                import random
                reward_amount = random.randint(min_reward, max_reward)

                # Add money to user's wallet
                guild_member.wallet += reward_amount
                effect_message += f" and received {reward_amount} coins!"

                # Add transaction record
                transaction = Transaction(
                    user_id=db_user.id,
                    guild_id=db_guild.id,
                    transaction_type="loot_box",
                    amount=reward_amount,
                    description=f"Opened {item.name}"
                )
                db.session.add(transaction)

            # Handle Double Daily
            if item.name == 'Double Daily':
                # Store effect in user's instance properties
                instance_props = inventory_item.get_instance_properties()
                duration_days = properties.get('duration_days', 7)

                # Calculate expiration date
                from datetime import datetime, timedelta
                expiry_date = datetime.utcnow() + timedelta(days=duration_days)

                # Save to instance properties
                instance_props['double_daily'] = True
                instance_props['double_daily_expiry'] = expiry_date.isoformat()
                inventory_item.set_instance_properties(instance_props)

                effect_message += f" and will receive double daily rewards for {duration_days} days!"

            # Handle Robbery Shield
            if item.name == 'Robbery Shield':
                # Store effect in user's instance properties
                instance_props = inventory_item.get_instance_properties()
                duration_days = properties.get('duration_days', 3)

                # Calculate expiration date
                from datetime import datetime, timedelta
                expiry_date = datetime.utcnow() + timedelta(days=duration_days)

                # Save to instance properties
                instance_props['robbery_shield'] = True
                instance_props['robbery_shield_expiry'] = expiry_date.isoformat()
                inventory_item.set_instance_properties(instance_props)

                effect_message += f" and are now protected from robbery for {duration_days} days!"

            # Handle Quest Skip Token
            if item.name == 'Quest Skip Token':
                from models import ActiveQuest
                # Find active quest
                active_quest = ActiveQuest.query.filter_by(
                    user_id=db_user.id,
                    guild_id=db_guild.id,
                    completed=False
                ).first()

                if active_quest:
                    # Mark quest as completed and give reward
                    active_quest.completed = True
                    guild_member.wallet += active_quest.reward

                    # Add transaction for reward
                    transaction = Transaction(
                        user_id=db_user.id,
                        guild_id=db_guild.id,
                        transaction_type="quest_reward",
                        amount=active_quest.reward,
                        description=f"Quest completed (skipped): {active_quest.quest_title}"
                    )
                    db.session.add(transaction)

                    effect_message += f" and skipped quest '{active_quest.quest_title}', earning {active_quest.reward} coins!"
                else:
                    effect_message += " but you don't have any active quests to skip!"

            # Handle Bet Insurance
            if item.name == 'Bet Insurance':
                # Store effect in user's instance properties
                instance_props = inventory_item.get_instance_properties()
                refund_percent = properties.get('refund_percent', 75)

                # Set bet insurance
                instance_props['bet_insurance'] = True
                instance_props['refund_percent'] = refund_percent
                inventory_item.set_instance_properties(instance_props)

                effect_message += f" and will receive {refund_percent}% back if you lose your next bet!"

            # Legacy items support
            if "effect_type" in properties:
                effect_type = properties["effect_type"]

                # Economy boost items
                if effect_type == "money":
                    if "amount" in properties:
                        amount = int(properties["amount"])

                        # Add money to wallet
                        guild_member.wallet += amount
                        effect_message += f" and received {amount} coins!"

                        # Add transaction record
                        transaction = Transaction(
                            user_id=db_user.id,
                            guild_id=db_guild.id,
                            transaction_type="item_use",
                            amount=amount,
                            description=f"Used {item.name}"
                        )
                        db.session.add(transaction)

                # Role temp items
                elif effect_type == "temp_role":
                    if "role_id" in properties and "duration" in properties:
                        role_id = properties["role_id"]
                        duration = int(properties["duration"])  # Duration in minutes

                        try:
                            # Add role to user
                            guild = self.bot.get_guild(interaction.guild_id)
                            role = guild.get_role(int(role_id))
                            member = guild.get_member(interaction.user.id)

                            if role and member:
                                await member.add_roles(role)
                                effect_message += f" and received the {role.name} role for {duration} minutes!"

                                # Schedule role removal
                                async def remove_role_later():
                                    await asyncio.sleep(duration * 60)
                                    try:
                                        await member.remove_roles(role)
                                        await member.send(f"Your temporary {role.name} role has expired.")
                                    except:
                                        pass

                                asyncio.create_task(remove_role_later())
                        except Exception as e:
                            logging.error(f"Error handling temporary role item: {e}")
                            effect_message += f", but there was an error applying the role effect."

            # Update inventory if not already updated (Company Shares updates it during processing)
            if item.name != 'Company Shares':
                inventory_item.quantity -= 1
                inventory_item.last_used_at = datetime.utcnow()

                # If quantity is zero, consider removing the item
                if inventory_item.quantity <= 0:
                    db.session.delete(inventory_item)

                # Commit changes
                db.session.commit()

            # Notify user of successful usage
            if item.name != 'Company Shares':  # Company shares already responded
                if interaction.response.is_done():
                    await interaction.followup.send(embed=self.success_embed(effect_message))
                else:
                    await interaction.response.send_message(embed=self.success_embed(effect_message))

        except Exception as e:
            with app.app_context():
                db.session.rollback()
            logging.error(f"Error during item usage: {e}")
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=self.error_embed("An error occurred while using the item. Please try again."),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=self.error_embed("An error occurred while using the item. Please try again."),
                    ephemeralTrue)

    @commands.command(name="gift", help="Gift an item to another user")
    async def gift_prefix(self, ctx, item_id: int, quantity: int, *, target: discord.Member):
        """Gift an item to another user with traditional prefix command."""
        await self.gift_item(ctx, item_id, quantity, target)

    @app_commands.command(name="gift", description="Gift an item to another user")
    @app_commands.describe(
        item_id="The ID of the item to gift",
        target="The user to gift the item to",
        quantity="The number of items to gift (default: 1)"
    )
    async def gift_slash(self, interaction: discord.Interaction, item_id: int, target: discord.Member, quantity: int = 1):
        """Gift an item to another user with slash command."""
        await self.gift_item_slash(interaction, item_id, quantity, target)

    async def gift_item(self, ctx, item_id: int, quantity: int, target: discord.Member):
        """Handle gifting an item to another user."""
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        target_id = target.id

        # Validate input
        if quantity <= 0:
            await ctx.send(embed=self.error_embed("Quantity must be greater than 0."))
            return

        if user_id == target_id:
            await ctx.send(embed=self.error_embed("You cannot gift items to yourself."))
            return

        from app import app

        with app.app_context():
            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()
            db_target = User.query.filter_by(discord_id=str(target_id)).first()

            if not db_guild or not db_user or not db_target:
                await ctx.send(embed=self.error_embed("Database error. Please try again later."))
                return

            # Get the item from database
            item = Item.query.get(item_id)

            if not item:
                await ctx.send(embed=self.error_embed(f"Item with ID {item_id} not found."))
                return

            # Check if item is tradeable
            if not item.is_tradeable:
                await ctx.send(embed=self.error_embed(f"{item.name} cannot be traded."))
                return

            # Check if user has enough of the item
            inventory_item = InventoryItem.query.filter_by(
                user_id=db_user.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()

            if not inventory_item or inventory_item.quantity < quantity:
                await ctx.send(
                    embed=self.error_embed(
                        f"You don't have enough {item.name} to gift. " +
                        f"You have {inventory_item.quantity if inventory_item else 0}, but tried to gift {quantity}."
                    )
                )
                return

            # Remove item from user's inventory
            inventory_item.quantity -= quantity

            if inventory_item.quantity <= 0:
                db.session.delete(inventory_item)
            else:
                inventory_item.updated_at = datetime.utcnow()

            # Add item to target's inventory
            target_inventory_item = InventoryItem.query.filter_by(
                user_id=db_target.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()

            if target_inventory_item:
                # Target already has this item, increment quantity
                target_inventory_item.quantity += quantity
                target_inventory_item.updated_at = datetime.utcnow()
            else:
                # First time target is receiving this item
                target_inventory_item = InventoryItem(
                    user_id=db_target.id,
                    item_id=item.id,
                    guild_id=db_guild.id,
                    quantity=quantity,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(target_inventory_item)

            # Commit changes to database
            db.session.commit()

            # Send success message
            await ctx.send(
                embed=self.success_embed(
                    f"You gifted {quantity}x {item.name} to {target.display_name}!"
                )
            )

            # Try to notify the target
            try:
                await target.send(
                    embed=self.info_embed(
                        f"Gift Received",
                        f"{ctx.author.display_name} has gifted you {quantity}x {item.name}!"
                    )
                )
            except:
                pass  # Don't worry if DM fails

    async def gift_item_slash(self, interaction: discord.Interaction, item_id: int, quantity: int, target: discord.Member):
        """Handle gifting an item to another user (slash command version)."""
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        target_id = target.id

        # Validate input
        if quantity <= 0:
            await interaction.response.send_message(
                embed=self.error_embed("Quantity must be greater than 0."),
                ephemeral=True
            )
            return

        if user_id == target_id:
            await interaction.response.send_message(
                embed=self.error_embed("You cannot gift items to yourself."),
                ephemeral=True
            )
            return

        from app import app

        with app.app_context():
            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()
            db_target = User.query.filter_by(discord_id=str(target_id)).first()

            if not db_guild or not db_user or not db_target:
                await interaction.response.send_message(
                    embed=self.error_embed("Database error. Please try again later."),
                    ephemeral=True
                )
                return

            # Get the item from database
            item = Item.query.get(item_id)

            if not item:
                await interaction.response.send_message(
                    embed=self.error_embed(f"Item with ID {item_id} not found."),
                    ephemeral=True
                )
                return

            # Check if item is tradeable
            if not item.is_tradeable:
                await interaction.response.send_message(
                    embed=self.error_embed(f"{item.name} cannot be traded."),
                    ephemeral=True
                )
                return

            # Check if user has enough of the item
            inventory_item = InventoryItem.query.filter_by(
                user_id=db_user.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()

            if not inventory_item or inventory_item.quantity < quantity:
                await interaction.response.send_message(
                    embed=self.error_embed(
                        f"You don't have enough {item.name} to gift. " +
                        f"You have {inventory_item.quantity if inventory_item else 0}, but tried to gift {quantity}."
                    ),
                    ephemeral=True
                )
                return

            # Remove item from user's inventory
            inventory_item.quantity -= quantity

            if inventory_item.quantity <= 0:
                db.session.delete(inventory_item)
            else:
                inventory_item.updated_at = datetime.utcnow()

            # Add item to target's inventory
            target_inventory_item = InventoryItem.query.filter_by(
                user_id=db_target.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()

            if target_inventory_item:
                # Target already has this item, increment quantity
                target_inventory_item.quantity += quantity
                target_inventory_item.updated_at = datetime.utcnow()
            else:
                # First time target is receiving this item
                target_inventory_item = InventoryItem(
                    user_id=db_target.id,
                    item_id=item.id,
                    guild_id=db_guild.id,
                    quantity=quantity,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(target_inventory_item)

            # Commit changes to database
            db.session.commit()

            # Send success message
            await interaction.response.send_message(
                embed=self.success_embed(
                    f"You gifted {quantity}x {item.name} to {target.display_name}!"
                ),
                ephemeral=False  # Show to everyone
            )

            # Try to notify the target
            try:
                await target.send(
                    embed=self.info_embed(
                        f"Gift Received",
                        f"{interaction.user.display_name} has gifted you {quantity}x {item.name}!"
                    )
                )
            except:
                pass  # Don't worry if DM fails

    # Admin commands for item management

    @commands.command(name="addcategory", help="Add a new item category")
    @commands.has_permissions(administrator=True)
    async def addcategory_prefix(self, ctx, name: str, *, description: str):
        """Add a new item category with traditional prefix command."""
        await self.add_category(ctx, name, description)

    @app_commands.command(name="addcategory", description="Add a new item category")
    @app_commands.describe(
        name="The name of the category",
        description="The description of the category"
    )
    @app_commands.default_permissions(administrator=True)
    async def addcategory_slash(self, interaction: discord.Interaction, name: str, description: str):
        """Add a new item category with slash command."""
        await self.add_category_slash(interaction, name, description)

    async def add_category(self, ctx, name: str, description: str):
        """Handle adding a new item category."""
        from app import app

        with app.app_context():
            # Check if category already exists
            existing_category = ItemCategory.query.filter(sa.func.lower(ItemCategory.name) == name.lower()).first()

            if existing_category:
                await ctx.send(embed=self.error_embed(f"Category '{name}' already exists."))
                return

            # Create new category
            new_category = ItemCategory(
                name=name,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_category)
            db.session.commit()

            # Send success message
            await ctx.send(
                embed=self.success_embed(
                    f"Category '{name}' has been created!"
                )
            )

    async def add_category_slash(self, interaction: discord.Interaction, name: str, description: str):
        """Handle adding a new item category (slash command version)."""
        from app import app

        with app.app_context():
            # Check if category already exists
            existing_category = ItemCategory.query.filter(sa.func.lower(ItemCategory.name) == name.lower()).first()

            if existing_category:
                await interaction.response.send_message(
                    embed=self.error_embed(f"Category '{name}' already exists."),
                    ephemeral=True
                )
                return

            # Create new category
            new_category = ItemCategory(
                name=name,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_category)
            db.session.commit()

            # Send success message
            await interaction.response.send_message(
                embed=self.success_embed(
                    f"Category '{name}' has been created!"
                ),
                ephemeral=False  # Show to everyone
            )

    @commands.command(name="additem", help="Add a new item to the shop")
    @commands.has_permissions(administrator=True)
    async def additem_prefix(self, ctx, name: str, price: int, category: str, *, description: str):
        """Add a new item to the shop with traditional prefix command."""
        await self.add_item(ctx, name, price, category, description)

    @app_commands.command(name="additem", description="Add a new item to the shop")
    @app_commands.describe(
        name="The name of the item",
        price="The price of the item in coins",
        category="The category of the item",
        description="The description of the item",
        is_consumable="Whether the item can be used/consumed",
        is_tradeable="Whether the item can be traded/gifted",
        is_limited="Whether the item has limited quantity",
        quantity="The available quantity if the item is limited"
    )
    @app_commands.default_permissions(administrator=True)
    async def additem_slash(self, interaction: discord.Interaction, 
                          name: str, 
                          price: int, 
                          category: str, 
                          description: str,
                          is_consumable: bool = False,
                          is_tradeable: bool = True,
                          is_limited: bool = False,
                          quantity: int = None):
        """Add a new item to the shop with slash command."""
        await self.add_item_slash(interaction, name, price, category, description, 
                                is_consumable, is_tradeable, is_limited, quantity)

    async def add_item(self, ctx, name: str, price: int, category_name: str, description: str):
        """Handle adding a new item to the shop."""
        from app import app

        with app.app_context():
            # Validate input
            if price < 0:
                await ctx.send(embed=self.error_embed("Price cannot be negative."))
                return

            # Find category
            category = ItemCategory.query.filter(sa.func.lower(ItemCategory.name) == category_name.lower()).first()

            if not category:
                await ctx.send(
                    embed=self.error_embed(
                        f"Category '{category_name}' not found. Use `!addcategory` to create it first."
                    )
                )
                return

            # Check if item already exists
            existing_item = Item.query.filter(
                sa.func.lower(Item.name) == name.lower(), 
                Item.category_id == category.id
            ).first()

            if existing_item:
                await ctx.send(embed=self.error_embed(f"Item '{name}' already exists in category '{category.name}'."))
                return

            # Create new item (simple version without extended properties)
            new_item = Item(
                name=name,
                description=description,
                price=price,
                category_id=category.id,
                is_consumable=False,  # Default values for prefix command
                is_tradeable=True,
                is_limited=False,
                quantity=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_item)
            db.session.commit()

            # Send success message
            await ctx.send(
                embed=self.success_embed(
                    f"Item '{name}' has been added to the shop under category '{category.name}'!"
                )
            )

    async def add_item_slash(self, interaction: discord.Interaction, 
                          name: str, 
                          price: int, 
                          category_name: str, 
                          description: str,
                          is_consumable: bool = False,
                          is_tradeable: bool = True,
                          is_limited: bool = False,
                          quantity: int = None):
        """Handle adding a new item to the shop (slash command version)."""
        from app import app

        with app.app_context():
            # Validate input
            if price < 0:
                await interaction.response.send_message(
                    embed=self.error_embed("Price cannot be negative."),
                    ephemeral=True
                )
                return

            if is_limited and quantity is None:
                await interaction.response.send_message(
                    embed=self.error_embed("Quantity must be specified for limited items."),
                    ephemeral=True
                )
                return

            # Find category
            category = ItemCategory.query.filter(sa.func.lower(ItemCategory.name) == category_name.lower()).first()

            if not category:
                await interaction.response.send_message(
                    embed=self.error_embed(
                        f"Category '{category_name}' not found. Use `/addcategory` to create it first."
                    ),
                    ephemeral=True
                )
                return

            # Check if item already exists
            existing_item = Item.query.filter(
                sa.func.lower(Item.name) == name.lower(), 
                Item.category_id == category.id
            ).first()

            if existing_item:
                await interaction.response.send_message(
                    embed=self.error_embed(f"Item '{name}' already exists in category '{category.name}'."),
                    ephemeral=True
                )
                return

            # Create new item
            new_item = Item(
                name=name,
                description=description,
                price=price,
                category_id=category.id,
                is_consumable=is_consumable,
                is_tradeable=is_tradeable,
                is_limited=is_limited,
                quantity=quantity if is_limited else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_item)
            db.session.commit()

            # Send success message
            await interaction.response.send_message(
                embed=self.success_embed(
                    f"Item '{name}' has been added to the shop under category '{category.name}'!"
                ),
                ephemeral=False  # Show to everyone
            )

    @commands.command(name="removeitem", help="Remove an item from the shop")
    @commands.has_permissions(administrator=True)
    async def removeitem_prefix(self, ctx, item_id: int):
        """Remove an item from the shop with traditional prefix command."""
        await self.remove_item(ctx, item_id)

    @app_commands.command(name="removeitem", description="Remove an item from the shop")
    @app_commands.describe(item_id="The ID of the item to remove")
    @app_commands.default_permissions(administrator=True)
    async def removeitem_slash(self, interaction: discord.Interaction, item_id: int):
        """Remove an item from the shop with slash command."""
        await self.remove_item_slash(interaction, item_id)

    async def remove_item(self, ctx, item_id: int):
        """Handle removing an item from the shop."""
        from app import app

        with app.app_context():
            # Find the item
            item = Item.query.get(item_id)

            if not item:
                await ctx.send(embed=self.error_embed(f"Item with ID {item_id} not found."))
                return

            # Store item name for confirmation message
            item_name = item.name

            # Delete the item
            db.session.delete(item)
            db.session.commit()

            # Send success message
            await ctx.send(
                embed=self.success_embed(
                    f"Item '{item_name}' has been removed from the shop!"
                )
            )

    async def remove_item_slash(self, interaction: discord.Interaction, item_id: int):
        """Handle removing an item from the shop (slash command version)."""
        from app import app

        with app.app_context():
            # Find the item
            item = Item.query.get(item_id)

            if not item:
                await interaction.response.send_message(
                    embed=self.error_embed(f"Item with ID {item_id} not found."),
                    ephemeral=True
                )
                return

            # Store item name for confirmation message
            item_name = item.name

            # Delete the item
            db.session.delete(item)
            db.session.commit()

            # Send success message
            await interaction.response.send_message(
                embed=self.success_embed(
                    f"Item '{item_name}' has been removed from the shop!"
                ),
                ephemeral=False  # Show to everyone
            )

    # Investment-related commands

    @commands.command(name="investments", help="View your company investments")
    async def investments_prefix(self, ctx):
        """View your company investments."""
        from app import app

        with app.app_context():
            guild_id = ctx.guild.id
            user_id = ctx.author.id

            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()

            if not db_guild or not db_user:
                await ctx.send(embed=self.error_embed("Database error. Please try again later."))
                return

            # Get user's guild member record
            guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()

            if not guild_member:
                await ctx.send(embed=self.error_embed("Could not find your economy profile."))
                return

            # Get user's investments
            investments = CompanyInvestment.query.filter_by(investor_id=guild_member.id).all()

            if not investments:
                await ctx.send(embed=self.error_embed("You don't have any company investments."))
                return

            # Create embed message
            embed = self.create_embed(
                f"{ctx.author.display_name}'s Investments",
                "Your company investments and returns"
            )

            from models import Company
            total_invested = 0
            total_return = 0

            for investment in investments:
                company = Company.query.get(investment.company_id)

                if not company:
                    continue

                # Calculate investment details
                invested_amount = investment.amount_invested
                total_invested += invested_amount

                ownership_percent = investment.percent_ownership * 100

                # Calculate time remaining
                current_time = datetime.utcnow()
                if investment.expires_at <= current_time:
                    time_remaining = "Expired"
                else:
                    days_remaining = (investment.expires_at - current_time).days
                    hours_remaining = ((investment.expires_at - current_time).seconds // 3600)
                    time_remaining = f"{days_remaining}d {hours_remaining}h remaining"

                # Calculate expected return
                daily_return = round(company.value * investment.percent_ownership)
                total_days = (investment.expires_at - investment.created_at).days
                expected_total = daily_return * total_days
                total_return += expected_total

                # Add field for this investment
                embed.add_field(
                    name=f"{company.name} - {ownership_percent:.2f}% ownership",
                    value=(
                        f"💰 Invested: {invested_amount} coins\n"
                        f"📈 Daily return: {daily_return} coins\n"
                        f"⏳ {time_remaining}\n"
                        f"💵 Expected total: {expected_total} coins"
                    ),
                    inline=False
                )

            # Add summary field
            embed.add_field(
                name="Investment Summary",
                value=(
                    f"💰 Total invested: {total_invested} coins\n"
                    f"💵 Expected total return: {total_return} coins\n"
                    f"📊 ROI: {((total_return / total_invested) - 1) * 100:.2f}%"
                ),
                inline=False
            )

            # Send the embed
            await ctx.send(embed=embed)

    @app_commands.command(name="investments", description="View your company investments")
    async def investments_slash(self, interaction: discord.Interaction):
        """View your company investments with slash command."""
        from app import app

        with app.app_context():
            guild_id = interaction.guild_id
            user_id = interaction.user.id

            # Find database records
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()

            if not db_guild or not db_user:
                await interaction.response.send_message(
                    embed=self.error_embed("Database error. Please try again later."),
                    ephemeral=True
                )
                return

            # Get user's guild member record
            guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()

            if not guild_member:
                await interaction.response.send_message(
                    embed=self.error_embed("Could not find your economy profile."),
                    ephemeral=True
                )
                return

            # Get user's investments
            investments = CompanyInvestment.query.filter_by(investor_id=guild_member.id).all()

            if not investments:
                await interaction.response.send_message(
                    embed=self.error_embed("You don't have any company investments."),
                    ephemeral=True
                )
                return

            # Create embed message
            embed = self.create_embed(
                f"{interaction.user.display_name}'s Investments",
                "Your company investments and returns"
            )

            from models import Company
            total_invested = 0
            total_return = 0

            for investment in investments:
                company = Company.query.get(investment.company_id)

                if not company:
                    continue

                # Calculate investment details
                invested_amount = investment.amount_invested
                total_invested += invested_amount

                ownership_percent = investment.percent_ownership * 100

                # Calculate time remaining
                current_time = datetime.utcnow()
                if investment.expires_at <= current_time:
                    time_remaining = "Expired"
                else:
                    days_remaining = (investment.expires_at - current_time).days
                    hours_remaining = ((investment.expires_at - current_time).seconds // 3600)
                    time_remaining = f"{days_remaining}d {hours_remaining}h remaining"

                # Calculate expected return
                daily_return = round(company.value * investment.percent_ownership)
                total_days = (investment.expires_at - investment.created_at).days
                expected_total = daily_return * total_days
                total_return += expected_total

                # Add field for this investment
                embed.add_field(
                    name=f"{company.name} - {ownership_percent:.2f}% ownership",
                    value=(
                        f"💰 Invested: {invested_amount} coins\n"
                        f"📈 Daily return: {daily_return} coins\n"
                        f"⏳ {time_remaining}\n"
                        f"💵 Expected total: {expected_total} coins"
                    ),
                    inline=False
                )

            # Add summary field
            embed.add_field(
                name="Investment Summary",
                value=(
                    f"💰 Total invested: {total_invested} coins\n"
                    f"💵 Expected total return: {total_return} coins\n"
                    f"📊 ROI: {((total_return / total_invested) - 1) * 100:.2f}%"
                ),
                inline=False
            )

            # Send the embed
            await interaction.response.send_message(embed=embed)

    # Shop and category display commands

    @commands.command(name="shoplist", help="List all shop items with prices")
    async def shoplist_prefix(self, ctx):
        """List all shop categories and items with prices in a formatted output."""
        await self.list_shop_items(ctx)

    @app_commands.command(name="shoplist", description="List all shop items with prices")
    async def shoplist_slash(self, interaction: discord.Interaction):
        """List all shop categories and items with prices in a formatted output (slash command version)."""
        from app import app

        with app.app_context():
            # Get all categories
            categories = ItemCategory.query.all()

            if not categories:
                await interaction.response.send_message(
                    embed=self.error_embed("No item categories found in the shop."),
                    ephemeral=True
                )
                return

            # Create embed message
            embed = self.create_embed(
                "Shop Item List",
                "Complete list of all items available for purchase"
            )

            for category in categories:
                # Get items in this category
                items = Item.query.filter_by(category_id=category.id).all()

                if not items:
                    continue

                # Create item list for this category
                item_list = ""
                for item in items:
                    status = ""
                    if item.is_limited and item.quantity is not None:
                        status = f" | {item.quantity} left" if item.quantity > 0 else " | SOLD OUT"

                    item_list += f"• ID: {item.id} - {item.name} - {item.price} coins{status}\n"

                # Add field for this category
                embed.add_field(
                    name=f"{category.name}",
                    value=item_list or "No items",
                    inline=False
                )

            # Send the embed
            await interaction.response.send_message(embed=embed)

    @commands.command(name="category", help="List shop categories")
    async def category_prefix(self, ctx):
        """Display all available shop categories in a formatted embed."""
        await self.display_categories(ctx)

    @app_commands.command(name="category", description="List shop categories")
    async def category_slash(self, interaction: discord.Interaction):
        """Display all available shop categories in a formatted embed (slash command version)."""
        from app import app

        with app.app_context():
            # Get all categories
            categories = ItemCategory.query.all()

            if not categories:
                await interaction.response.send_message(
                    embed=self.error_embed("No item categories found in the shop."),
                    ephemeral=True
                )
                return

            # Create embed message
            embed = self.create_embed(
                "Shop Categories",
                "Browse through different item categories"
            )

            for category in categories:
                # Get item count for this category
                item_count = Item.query.filter_by(category_id=category.id).count()

                # Get a sample item from this category
                sample_item = Item.query.filter_by(category_id=category.id).first()
                sample_text = f"Example: {sample_item.name} ({sample_item.price} coins)" if sample_item else "No items"

                # Add field for this category
                embed.add_field(
                    name=f"{category.name} ({item_count} items)",
                    value=f"{category.description}\n{sample_text}",
                    inline=False
                )

            # Add instructions
            embed.set_footer(text="Use /shop <category> to browse items in a specific category")

            # Send the embed
            await interaction.response.send_message(embed=embed)

    async def display_categories(self, ctx):
        """Display all available shop categories with descriptions and example items."""
        from app import app

        with app.app_context():
            # Get all categories
            categories = ItemCategory.query.all()

            if not categories:
                await ctx.send(embed=self.error_embed("No item categories found in the shop."))
                return

            # Create embed message
            embed = self.create_embed(
                "Shop Categories",
                "Browse through different item categories"
            )

            for category in categories:
                # Get item count for this category
                item_count = Item.query.filter_by(category_id=category.id).count()

                # Get a sample item from this category
                sample_item = Item.query.filter_by(category_id=category.id).first()
                sample_text = f"Example: {sample_item.name} ({sample_item.price} coins)" if sample_item else "No items"

                # Add field for this category
                embed.add_field(
                    name=f"{category.name} ({item_count} items)",
                    value=f"{category.description}\n{sample_text}",
                    inline=False
                )

            # Add instructions
            embed.set_footer(text="Use !shop <category> to browse items in a specific category")

            # Send the embed
            await ctx.send(embed=embed)

    async def list_shop_items(self, ctx):
        """Show a comprehensive list of all shop categories and their items with prices."""
        from app import app

        with app.app_context():
            # Get all categories
            categories = ItemCategory.query.all()

            if not categories:
                await ctx.send(embed=self.error_embed("No item categories found in the shop."))
                return

            # Create embed message
            embed = self.create_embed(
                "Shop Item List",
                "Complete list of all items available for purchase"
            )

            # Create multiple pages if needed
            all_embeds = [embed]
            current_embed = embed
            field_count = 0

            for category in categories:
                # Get items in this category
                items = Item.query.filter_by(category_id=category.id).all()

                if not items:
                    continue

                # Check if we need a new embed (Discord limit: 25 fields per embed)
                if field_count >= 24:  # Leave room for a "Navigation" field
                    new_embed = self.create_embed(
                        "Shop Item List (Continued)",
                        "Complete list of all items available for purchase"
                    )
                    all_embeds.append(new_embed)
                    current_embed = new_embed
                    field_count = 0

                # Create item list for this category
                item_list = ""
                for item in items:
                    status = ""
                    if item.is_limited and item.quantity is not None:
                        status = f" | {item.quantity} left" if item.quantity > 0 else " | SOLD OUT"

                    item_list += f"• ID: {item.id} - {item.name} - {item.price} coins{status}\n"

                # Add field for this category
                current_embed.add_field(
                    name=f"{category.name}",
                    value=item_list or "No items",
                    inline=False
                )
                field_count += 1

            # If we have multiple embeds, send them with pagination
            if len(all_embeds) > 1:
                current_page = 0

                # Send the first page
                message = await ctx.send(embed=all_embeds[current_page])

                # Add navigation reactions
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")

                # Define a check function for reactions
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

                # Wait for reactions
                while True:
                    try:
                        reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)

                        # Remove user's reaction
                        await message.remove_reaction(reaction, user)

                        # Update current page based on reaction
                        if str(reaction.emoji) == "➡️" and current_page < len(all_embeds) - 1:
                            current_page += 1
                            await message.edit(embed=all_embeds[current_page])
                        elif str(reaction.emoji) == "⬅️" and current_page > 0:
                            current_page -= 1
                            await message.edit(embed=all_embeds[current_page])

                    except asyncio.TimeoutError:
                        break

            else:
                # Just send the single embed
                await ctx.send(embed=embed)

    # Background task to process investment income
    async def process_investment_income_loop(self):
        """Background task that processes company investment income."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                from app import app

                with app.app_context():
                    # Get current time
                    current_time = datetime.utcnow()

                    # Get all active investments
                    investments = CompanyInvestment.query.filter(
                        CompanyInvestment.expires_at > current_time,
                        CompanyInvestment.last_payment_at < current_time - timedelta(hours=24)
                    ).all()

                    for investment in investments:
                        try:
                            # Get the company
                            from models import Company, GuildMember, Transaction
                            company = Company.query.get(investment.company_id)

                            if company:
                                # Calculate daily return
                                daily_return = round(company.value * investment.percent_ownership)

                                # Get the investor
                                investor = GuildMember.query.get(investment.investor_id)

                                if investor:
                                    # Add return to investor's wallet
                                    investor.wallet += daily_return

                                    # Add transaction record
                                    transaction = Transaction(
                                        user_id=investor.user_id,
                                        guild_id=investor.guild_id,
                                        transaction_type="investment_income",
                                        amount=daily_return,
                                        description=f"Investment income from {company.name}"
                                    )
                                    db.session.add(transaction)

                                    # Update last payment time
                                    investment.last_payment_at = current_time

                                    logging.info(f"Processed investment income: {investor.id} received {daily_return} from {company.name}")

                                    # Try to notify investor
                                    try:
                                        user = await self.bot.fetch_user(int(User.query.get(investor.user_id).discord_id))
                                        if user:
                                            await user.send(
                                                embed=self.info_embed(
                                                    "Investment Income",
                                                    f"You received {daily_return} coins from your investment in {company.name}!"
                                                )
                                            )
                                    except:
                                        pass  # Don't worry if DM fails

                        except Exception as e:
                            logging.error(f"Error processing investment {investment.id}: {e}")

                    # Commit all changes
                    db.session.commit()

            except Exception as e:
                logging.error(f"Error in investment processing loop: {e}")

            # Run once a day
            await asyncio.sleep(3600)  # Check hourly

    async def cog_load(self):
        """Called when the cog is loaded."""
        # Start background task
        self.bot.loop.create_task(self.process_investment_income_loop())

async def setup(bot):
    """Add the Items cog to the bot."""
    await bot.add_cog(Items(bot))
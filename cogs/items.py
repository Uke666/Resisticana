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
        if category:
            await self.show_category_items(ctx, category)
        else:
            # Get categories from database
            from app import app
            with app.app_context():
                categories = ItemCategory.query.all()
            
            if not categories:
                await ctx.send(embed=self.info_embed("Shop", "There are no categories in the shop yet."))
                return
            
            # Create category selection menu
            embed = self.create_embed("Item Shop Categories", "Select a category by typing its number:")
            
            category_list = ""
            for i, category in enumerate(categories, 1):
                # Count items in this category
                with app.app_context():
                    item_count = Item.query.filter_by(category_id=category.id).count()
                category_list += f"`{i}.` **{category.name}** ({item_count} items)\n"
                category_list += f"   {category.description}\n\n"
            
            embed.description = category_list
            embed.set_footer(text="Type a number to view items, or 'cancel' to exit")
            
            # Send the selection message
            message = await ctx.send(embed=embed)
            
            # Wait for user selection
            def check(m):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
                
            try:
                response = await self.bot.wait_for('message', check=check, timeout=30.0)
                
                # Process the selection
                if response.content.lower() == 'cancel':
                    await ctx.send(embed=self.info_embed("Shop", "Shop browsing cancelled."))
                    return
                
                try:
                    selection = int(response.content.strip())
                    if 1 <= selection <= len(categories):
                        selected_category = categories[selection-1]
                        await self.show_category_items(ctx, selected_category.name)
                    else:
                        await ctx.send(embed=self.error_embed(f"Invalid selection. Please choose a number between 1 and {len(categories)}."))
                except ValueError:
                    await ctx.send(embed=self.error_embed("Invalid selection. Please enter a number."))
            
            except asyncio.TimeoutError:
                # Handle timeout
                await ctx.send(embed=self.info_embed("Shop", "Shop browsing timed out."))
                return
    
    @app_commands.command(name="shop", description="Browse items in the shop")
    @app_commands.describe(category="Optional category to filter items by")
    async def shop_slash(self, interaction: discord.Interaction, category: str = None):
        """Browse the item shop with slash command."""
        if category:
            await self.show_category_items_slash(interaction, category)
        else:
            # Get categories from database
            from app import app
            with app.app_context():
                categories = ItemCategory.query.all()
            
            if not categories:
                await interaction.response.send_message(
                    embed=self.info_embed("Shop", "There are no categories in the shop yet."),
                    ephemeral=True
                )
                return
            
            # Create category selection view
            class CategorySelect(discord.ui.Select):
                def __init__(self, cog):
                    self.cog = cog
                    options = []
                    
                    for category in categories:
                        with app.app_context():
                            item_count = Item.query.filter_by(category_id=category.id).count()
                        
                        options.append(discord.SelectOption(
                            label=category.name,
                            description=f"{item_count} items available",
                            value=str(category.id)
                        ))
                    
                    super().__init__(
                        placeholder="Select a category...",
                        min_values=1,
                        max_values=1,
                        options=options
                    )
                
                async def callback(self, interaction: discord.Interaction):
                    category_id = int(self.values[0])
                    with app.app_context():
                        selected_category = ItemCategory.query.get(category_id)
                    
                    if selected_category:
                        await self.cog.show_category_items_slash(interaction, selected_category.name)
            
            class CategoryView(discord.ui.View):
                def __init__(self, cog, timeout=60):
                    super().__init__(timeout=timeout)
                    self.add_item(CategorySelect(cog))
            
            # Create embed with instructions
            embed = self.create_embed("Item Shop", "Select a category to browse items:")
            
            # Add a brief description of each category
            category_descriptions = ""
            for category in categories:
                with app.app_context():
                    item_count = Item.query.filter_by(category_id=category.id).count()
                category_descriptions += f"**{category.name}** ({item_count} items) - {category.description}\n\n"
            
            embed.description = category_descriptions
            
            # Send the message with the select menu
            await interaction.response.send_message(embed=embed, view=CategoryView(self))
    
    async def show_shop_categories(self, ctx):
        """Show all item categories in the shop."""
        # Get categories from database
        categories = ItemCategory.query.all()
        
        if not categories:
            await ctx.send(embed=self.info_embed("Shop", "There are no categories in the shop yet."))
            return
        
        embed = self.create_embed("Item Shop", "Browse categories and items available for purchase.")
        
        for category in categories:
            # Count items in this category
            item_count = Item.query.filter_by(category_id=category.id).count()
            embed.add_field(
                name=f"{category.name} ({item_count} items)",
                value=f"{category.description}\nUse `!shop {category.name}` to view items.",
                inline=False
            )
        
        embed.set_footer(text="Use !shop <category> to browse items in a specific category.")
        await ctx.send(embed=embed)
    
    async def show_shop_categories_slash(self, interaction: discord.Interaction):
        """Show all item categories in the shop (slash command version)."""
        # Get categories from database
        categories = ItemCategory.query.all()
        
        if not categories:
            await interaction.response.send_message(
                embed=self.info_embed("Shop", "There are no categories in the shop yet."), 
                ephemeral=True
            )
            return
        
        embed = self.create_embed("Item Shop", "Browse categories and items available for purchase.")
        
        for category in categories:
            # Count items in this category
            item_count = Item.query.filter_by(category_id=category.id).count()
            embed.add_field(
                name=f"{category.name} ({item_count} items)",
                value=f"{category.description}\nUse `/shop {category.name}` to view items.",
                inline=False
            )
        
        embed.set_footer(text="Use /shop with the category parameter to browse items in a specific category.")
        await interaction.response.send_message(embed=embed)
    
    async def show_category_items(self, ctx, category_name):
        """Show items in a specific category."""
        # Find the category
        from app import app
        with app.app_context():
            category = ItemCategory.query.filter(
                ItemCategory.name.ilike(f"%{category_name}%")
            ).first()
        
        if not category:
            await ctx.send(embed=self.error_embed(f"Category '{category_name}' not found."))
            return
        
        # Get items in this category
        with app.app_context():
            items = Item.query.filter_by(category_id=category.id).all()
        
        if not items:
            await ctx.send(embed=self.info_embed(
                f"{category.name} Items", 
                "There are no items in this category yet."
            ))
            return
        
        embed = self.create_embed(
            f"Shop: {category.name} Items", 
            f"Items available in the {category.name} category."
        )
        
        for item in items:
            # Check if limited and sold out
            sold_out = ""
            if item.is_limited and item.quantity_available is not None:
                if item.quantity_available <= 0:
                    sold_out = " [SOLD OUT]"
                else:
                    sold_out = f" [{item.quantity_available} remaining]"
            
            # Create item description with properties
            props = []
            if item.is_consumable:
                props.append("Consumable")
            if not item.is_tradeable:
                props.append("Not Tradeable")
            if item.is_role_reward:
                props.append("Grants Role")
            
            prop_text = f" ({', '.join(props)})" if props else ""
            
            embed.add_field(
                name=f"#{item.id}: {item.name}{sold_out} - {item.price} coins{prop_text}",
                value=f"{item.description}\nBuy with `!buy {item.id}`",
                inline=False
            )
        
        embed.set_footer(text="Use !buy <item_id> to purchase an item.")
        await ctx.send(embed=embed)
    
    async def show_category_items_slash(self, interaction: discord.Interaction, category_name):
        """Show items in a specific category (slash command version)."""
        # Find the category
        from app import app
        with app.app_context():
            category = ItemCategory.query.filter(
                ItemCategory.name.ilike(f"%{category_name}%")
            ).first()
        
        if not category:
            await interaction.response.send_message(
                embed=self.error_embed(f"Category '{category_name}' not found."),
                ephemeral=True
            )
            return
        
        # Get items in this category
        with app.app_context():
            items = Item.query.filter_by(category_id=category.id).all()
        
        if not items:
            await interaction.response.send_message(
                embed=self.info_embed(
                    f"{category.name} Items", 
                    "There are no items in this category yet."
                ),
                ephemeral=True
            )
            return
        
        embed = self.create_embed(
            f"Shop: {category.name} Items", 
            f"Items available in the {category.name} category."
        )
        
        for item in items:
            # Check if limited and sold out
            sold_out = ""
            if item.is_limited and item.quantity_available is not None:
                if item.quantity_available <= 0:
                    sold_out = " [SOLD OUT]"
                else:
                    sold_out = f" [{item.quantity_available} remaining]"
            
            # Create item description with properties
            props = []
            if item.is_consumable:
                props.append("Consumable")
            if not item.is_tradeable:
                props.append("Not Tradeable")
            if item.is_role_reward:
                props.append("Grants Role")
            
            prop_text = f" ({', '.join(props)})" if props else ""
            
            embed.add_field(
                name=f"#{item.id}: {item.name}{sold_out} - {item.price} coins{prop_text}",
                value=f"{item.description}\nBuy with `/buy {item.id}`",
                inline=False
            )
        
        embed.set_footer(text="Use /buy command to purchase an item.")
        await interaction.response.send_message(embed=embed)
    
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
        # Get the item from database
        from app import app
        from datetime import datetime
        
        with app.app_context():
            item = Item.query.get(item_id)
        
        if not item:
            await ctx.send(embed=self.error_embed(f"Item with ID {item_id} not found."))
            return
        
        # Check if item is sold out (if limited)
        if item.is_limited and item.quantity_available is not None and item.quantity_available <= 0:
            await ctx.send(embed=self.error_embed(f"Sorry, {item.name} is sold out!"))
            return
        
        # Get guild and user
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        
        # Find database records
        with app.app_context():
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()
        
        if not db_guild or not db_user:
            await ctx.send(embed=self.error_embed("Database error. Please try again later."))
            return
        
        # Find guild member record to access wallet
        from models import GuildMember
        with app.app_context():
            guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()
        
        if not guild_member:
            await ctx.send(embed=self.error_embed("Could not find your economy profile."))
            return
        
        # Check if user has enough money
        if guild_member.wallet < item.price:
            await ctx.send(embed=self.error_embed(
                f"You don't have enough money to buy {item.name}. "
                f"Price: {item.price}, Your wallet: {guild_member.wallet}."
            ))
            return
        
        # Create transaction and add item to inventory
        try:
            with app.app_context():
                # Deduct money from wallet
                guild_member.wallet -= item.price
                
                # Add transaction record
                from models import Transaction
                from app import db
                transaction = Transaction(
                    user_id=db_user.id,
                    guild_id=db_guild.id,
                    transaction_type="purchase",
                    amount=-item.price,
                    description=f"Purchased {item.name}"
                )
                db.session.add(transaction)
                
                # Check if user already has this item in inventory
                inventory_item = InventoryItem.query.filter_by(
                    user_id=db_user.id,
                    item_id=item.id,
                    guild_id=db_guild.id
                ).first()
                
                if inventory_item and not item.is_consumable:
                    # Update quantity for non-consumable items
                    inventory_item.quantity += 1
                    inventory_item.acquired_at = datetime.utcnow()  # Update acquisition time
                else:
                    # Create new inventory entry
                    inventory_item = InventoryItem(
                        user_id=db_user.id,
                        item_id=item.id,
                        guild_id=db_guild.id,
                        quantity=1
                    )
                    db.session.add(inventory_item)
                
                # Update item quantity if limited
                if item.is_limited and item.quantity_available is not None:
                    item.quantity_available -= 1
                
                # Commit changes
                db.session.commit()
            
            # Special handling for role rewards
            if item.is_role_reward and item.role_id:
                try:
                    role = ctx.guild.get_role(int(item.role_id))
                    if role:
                        await ctx.author.add_roles(role)
                except Exception as e:
                    logging.error(f"Error adding role for purchased item: {e}")
            
            # Notify user of successful purchase
            await ctx.send(embed=self.success_embed(
                f"You purchased {item.name} for {item.price} coins!"
            ))
            
        except Exception as e:
            with app.app_context():
                db.session.rollback()
            logging.error(f"Error during item purchase: {e}")
            await ctx.send(embed=self.error_embed("An error occurred during purchase. Please try again."))
    
    async def purchase_item_slash(self, interaction: discord.Interaction, item_id: int):
        """Handle the purchase of an item (slash command version)."""
        # Get the item from database
        from app import app
        from datetime import datetime
        
        with app.app_context():
            item = Item.query.get(item_id)
        
        if not item:
            await interaction.response.send_message(
                embed=self.error_embed(f"Item with ID {item_id} not found."),
                ephemeral=True
            )
            return
        
        # Check if item is sold out (if limited)
        if item.is_limited and item.quantity_available is not None and item.quantity_available <= 0:
            await interaction.response.send_message(
                embed=self.error_embed(f"Sorry, {item.name} is sold out!"),
                ephemeral=True
            )
            return
        
        # Get guild and user
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        
        # Find database records
        with app.app_context():
            db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
            db_user = User.query.filter_by(discord_id=str(user_id)).first()
        
        if not db_guild or not db_user:
            await interaction.response.send_message(
                embed=self.error_embed("Database error. Please try again later."),
                ephemeral=True
            )
            return
        
        # Find guild member record to access wallet
        from models import GuildMember
        with app.app_context():
            guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()
        
        if not guild_member:
            await interaction.response.send_message(
                embed=self.error_embed("Could not find your economy profile."),
                ephemeral=True
            )
            return
        
        # Check if user has enough money
        if guild_member.wallet < item.price:
            await interaction.response.send_message(
                embed=self.error_embed(
                    f"You don't have enough money to buy {item.name}. "
                    f"Price: {item.price}, Your wallet: {guild_member.wallet}."
                ),
                ephemeral=True
            )
            return
        
        # Create transaction and add item to inventory
        try:
            with app.app_context():
                # Deduct money from wallet
                guild_member.wallet -= item.price
                
                # Add transaction record
                from models import Transaction
                from app import db
                transaction = Transaction(
                    user_id=db_user.id,
                    guild_id=db_guild.id,
                    transaction_type="purchase",
                    amount=-item.price,
                    description=f"Purchased {item.name}"
                )
                db.session.add(transaction)
                
                # Check if user already has this item in inventory
                inventory_item = InventoryItem.query.filter_by(
                    user_id=db_user.id,
                    item_id=item.id,
                    guild_id=db_guild.id
                ).first()
                
                if inventory_item and not item.is_consumable:
                    # Update quantity for non-consumable items
                    inventory_item.quantity += 1
                    inventory_item.acquired_at = datetime.utcnow()  # Update acquisition time
                else:
                    # Create new inventory entry
                    inventory_item = InventoryItem(
                        user_id=db_user.id,
                        item_id=item.id,
                        guild_id=db_guild.id,
                        quantity=1
                    )
                    db.session.add(inventory_item)
                
                # Update item quantity if limited
                if item.is_limited and item.quantity_available is not None:
                    item.quantity_available -= 1
                
                # Commit changes
                db.session.commit()
            
            # Special handling for role rewards
            if item.is_role_reward and item.role_id:
                try:
                    role = interaction.guild.get_role(int(item.role_id))
                    if role:
                        await interaction.user.add_roles(role)
                except Exception as e:
                    logging.error(f"Error adding role for purchased item: {e}")
            
            # Notify user of successful purchase
            await interaction.response.send_message(
                embed=self.success_embed(f"You purchased {item.name} for {item.price} coins!")
            )
            
        except Exception as e:
            with app.app_context():
                db.session.rollback()
            logging.error(f"Error during item purchase: {e}")
            await interaction.response.send_message(
                embed=self.error_embed("An error occurred during purchase. Please try again."),
                ephemeral=True
            )
    
    @commands.command(name="inventory", help="View your inventory")
    async def inventory_prefix(self, ctx):
        """View your inventory with traditional prefix command."""
        from app import app
        with app.app_context():
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
            
            # Get inventory items
            inventory_items = InventoryItem.query.filter_by(
                user_id=db_user.id,
                guild_id=db_guild.id
            ).all()
            
            if not inventory_items:
                await ctx.send(embed=self.info_embed(
                    "Inventory", 
                    "Your inventory is empty. Use `!shop` to browse items you can buy."
                ))
                return
            
            # Construct the inventory details
            embed = self.create_embed(
                f"{ctx.author.display_name}'s Inventory",
                "Items you currently own."
            )
            
            # Group items by category for better organization
            categories = {}
            
            for inv_item in inventory_items:
                item = inv_item.item_type
                
                if item.category.name not in categories:
                    categories[item.category.name] = []
                
                categories[item.category.name].append((inv_item, item))
            
            # Add fields for each category
            for category_name, items in categories.items():
                items_text = ""
                
                for inv_item, item in items:
                    # Add item details
                    quantity_text = f" (x{inv_item.quantity})" if inv_item.quantity > 1 else ""
                    use_text = " - Use with `!use " + str(item.id) + "`" if item.is_consumable else ""
                    items_text += f"• **{item.name}**{quantity_text}{use_text}\n"
                    items_text += f"  {item.description}\n"
                
                embed.add_field(
                    name=category_name,
                    value=items_text,
                    inline=False
                )
            
            embed.set_footer(text="Use !use <item_id> to use a consumable item.")
            
        # Send the embed outside of app context
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
            
            # Get inventory items
            inventory_items = InventoryItem.query.filter_by(
                user_id=db_user.id,
                guild_id=db_guild.id
            ).all()
            
            if not inventory_items:
                await interaction.response.send_message(
                    embed=self.info_embed(
                        "Inventory", 
                        "Your inventory is empty. Use `/shop` to browse items you can buy."
                    )
                )
                return
            
            # Construct the embed
            embed = self.create_embed(
                f"{interaction.user.display_name}'s Inventory",
                "Items you currently own."
            )
            
            # Group items by category for better organization
            categories = {}
            
            for inv_item in inventory_items:
                item = inv_item.item_type
                
                if item.category.name not in categories:
                    categories[item.category.name] = []
                
                categories[item.category.name].append((inv_item, item))
            
            # Add fields for each category
            for category_name, items in categories.items():
                items_text = ""
                
                for inv_item, item in items:
                    # Add item details
                    quantity_text = f" (x{inv_item.quantity})" if inv_item.quantity > 1 else ""
                    use_text = " - Use with `/use " + str(item.id) + "`" if item.is_consumable else ""
                    items_text += f"• **{item.name}**{quantity_text}{use_text}\n"
                    items_text += f"  {item.description}\n"
                
                embed.add_field(
                    name=category_name,
                    value=items_text,
                    inline=False
                )
            
            embed.set_footer(text="Use /use command to use a consumable item.")
        
        # Send the embed outside of app context
        await interaction.response.send_message(embed=embed)
    
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

            # Get item properties
            properties = item.get_properties()
            effect_message = "You used " + item.name
            
            with app.app_context():
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
                
                # Create a selection message with companies
                company_list = "\n".join([f"{i+1}. {company.name}" for i, company in enumerate(companies)])
                
                select_embed = self.create_embed(
                    "Select a Company",
                    f"Please select a company to invest in by replying with the number:\n\n{company_list}\n\nType 'cancel' to abort."
                )
                await ctx.send(embed=select_embed)
                
                # Wait for user response
                try:
                    def check(m):
                        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
                        
                    response = await self.bot.wait_for('message', check=check, timeout=60.0)
                    
                    # Check for cancel
                    if response.content.lower() == 'cancel':
                        await ctx.send(embed=self.info_embed("Investment Cancelled", "Investment cancelled."))
                        return
                    
                    # Try to parse the selection
                    try:
                        selection = int(response.content.strip())
                        if selection < 1 or selection > len(companies):
                            await ctx.send(embed=self.error_embed(f"Invalid selection. Please choose a number between 1 and {len(companies)}."))
                            return
                        
                        selected_company = companies[selection-1]
                        
                        # Get investment parameters
                        passive_income_rate = properties.get('passive_income_rate', 0.05)
                        duration_days = properties.get('duration_days', 30)
                        
                        # Create investment record in database
                        from datetime import datetime, timedelta
                        
                        # Check if user already has shares in this company
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
                                VALUES (:investor_id, :company_id, :amount_invested, :percent, :created_at, :expires_at)
                                """
                            ), {
                                "investor_id": guild_member.id,
                                "company_id": selected_company.id,
                                "amount_invested": item.price,
                                "percent": passive_income_rate,
                                "created_at": datetime.utcnow(),
                                "expires_at": expires_at
                            })
                            conn.commit()
                        
                        effect_message += f" and invested in {selected_company.name}. You will earn {passive_income_rate*100}% of profits for {duration_days} days!"
                        
                    except ValueError:
                        await ctx.send(embed=self.error_embed("Invalid selection. Please enter a number."))
                        return
                        
                except asyncio.TimeoutError:
                    await ctx.send(embed=self.error_embed("Investment timed out. Please try again."))
                    return
                
            # Handle Loot Boxes
            elif hasattr(item, 'category') and item.category and item.category.name == 'Loot Boxes':
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
            elif item.name == 'Double Daily':
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
            elif item.name == 'Robbery Shield':
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
            elif item.name == 'Quest Skip Token':
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
            elif item.name == 'Bet Insurance':
                # Store effect in user's instance properties
                instance_props = inventory_item.get_instance_properties()
                refund_percent = properties.get('refund_percent', 75)
                
                # Set bet insurance
                instance_props['bet_insurance'] = True
                instance_props['refund_percent'] = refund_percent
                inventory_item.set_instance_properties(instance_props)
                
                effect_message += f" and will receive {refund_percent}% back if you lose your next bet!"
            
            # Legacy items support
            elif "effect_type" in properties:
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
                                        VALUES (:investor_id, :company_id, :amount_invested, :percent, :created_at, :expires_at)
                                        """
                                    ), {
                                        "investor_id": guild_member.id,
                                        "company_id": self.selected_company.id,
                                        "amount_invested": item.price,
                                        "percent": passive_income_rate,
                                        "created_at": datetime.utcnow(),
                                        "expires_at": expires_at
                                    })
                                    conn.commit()
                                
                                success_message = f"You invested in {self.selected_company.name}. You will earn {passive_income_rate*100}% of profits for {duration_days} days!"
                                await select_interaction.response.send_message(
                                    embed=self.cog.success_embed(success_message)
                                )
                                self.stop()
                                
                            except Exception as e:
                                logging.error(f"Error processing company investment: {e}")
                                await select_interaction.response.send_message(
                                    embed=self.cog.error_embed("An error occurred during investment. Please try again."),
                                    ephemeral=True
                                )
                                self.stop()
                                
                # Send the dropdown
                view = CompanySelectView(self)
                message = await interaction.followup.send(embed=select_embed, view=view)
                
                # Wait for selection
                timed_out = await view.wait()
                if timed_out:
                    await interaction.followup.send(
                        embed=self.error_embed("Investment selection timed out. Please try again.")
                    )
                    try:
                        await message.edit(view=None)  # Disable the view
                    except:
                        pass
                    return
                
                # If we get here without returning, the item has been used successfully
                return
                
            # Handle Loot Boxes
            elif hasattr(item, 'category') and item.category and item.category.name == 'Loot Boxes':
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
            elif item.name == 'Double Daily':
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
            elif item.name == 'Robbery Shield':
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
            elif item.name == 'Quest Skip Token':
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
            elif item.name == 'Bet Insurance':
                # Store effect in user's instance properties
                instance_props = inventory_item.get_instance_properties()
                refund_percent = properties.get('refund_percent', 75)
                
                # Set bet insurance
                instance_props['bet_insurance'] = True
                instance_props['refund_percent'] = refund_percent
                inventory_item.set_instance_properties(instance_props)
                
                effect_message += f" and will receive {refund_percent}% back if you lose your next bet!"
            
            # Legacy items support
            elif "effect_type" in properties:
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
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                await interaction.user.add_roles(role)
                                effect_message += f" and received the {role.name} role for {duration} minutes!"
                                
                                # Schedule role removal
                                async def remove_role_later():
                                    await asyncio.sleep(duration * 60)
                                    try:
                                        await interaction.user.remove_roles(role)
                                        await interaction.user.send(f"Your temporary {role.name} role has expired.")
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
            await interaction.response.send_message(
                embed=self.success_embed(effect_message)
            )
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during item usage: {e}")
            await interaction.response.send_message(
                embed=self.error_embed("An error occurred while using the item. Please try again."),
                ephemeral=True
            )
    
    async def gift_prefix(self, ctx, item_id: int, quantity: int, *, target: discord.Member):
        """Gift an item to another user with traditional prefix command."""
        await self.gift_item(ctx, item_id, quantity, target)
    
    @app_commands.command(name="gift", description="Gift an item to another user")
    @app_commands.describe(
        item_id="The ID of the item to gift",
        quantity="The quantity to gift (default: 1)",
        target="The user to gift the item to"
    )
    async def gift_slash(self, interaction: discord.Interaction, item_id: int, target: discord.Member, quantity: int = 1):
        """Gift an item to another user with slash command."""
        await self.gift_item_slash(interaction, item_id, quantity, target)
    
    async def gift_item(self, ctx, item_id: int, quantity: int, target: discord.Member):
        """Handle gifting an item to another user."""
        if quantity <= 0:
            await ctx.send(embed=self.error_embed("Quantity must be greater than 0."))
            return
        
        if target.id == ctx.author.id:
            await ctx.send(embed=self.error_embed("You can't gift items to yourself."))
            return
        
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        target_id = target.id
        
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
            await ctx.send(embed=self.error_embed(f"{item.name} cannot be traded or gifted."))
            return
        
        # Check if user has enough of the item
        inventory_item = InventoryItem.query.filter_by(
            user_id=db_user.id,
            item_id=item.id,
            guild_id=db_guild.id
        ).first()
        
        if not inventory_item or inventory_item.quantity < quantity:
            await ctx.send(embed=self.error_embed(
                f"You don't have enough {item.name} to gift. You have: {inventory_item.quantity if inventory_item else 0}, trying to gift: {quantity}."
            ))
            return
        
        # Process the gift
        try:
            # Update sender's inventory
            inventory_item.quantity -= quantity
            
            # If quantity is zero, remove the item from inventory
            if inventory_item.quantity <= 0:
                db.session.delete(inventory_item)
            
            # Check if recipient already has this item in inventory
            target_inventory_item = InventoryItem.query.filter_by(
                user_id=db_target.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()
            
            if target_inventory_item:
                # Update quantity for existing item
                target_inventory_item.quantity += quantity
            else:
                # Create new inventory entry
                target_inventory_item = InventoryItem(
                    user_id=db_target.id,
                    item_id=item.id,
                    guild_id=db_guild.id,
                    quantity=quantity
                )
                db.session.add(target_inventory_item)
            
            # Add gift transaction record
            from models import Transaction
            transaction = Transaction(
                user_id=db_user.id,
                guild_id=db_guild.id,
                transaction_type="gift",
                amount=0,  # No monetary value for gifts
                recipient_id=db_target.id,
                description=f"Gifted {quantity}x {item.name} to {target.display_name}"
            )
            db.session.add(transaction)
            
            # Commit changes
            db.session.commit()
            
            # Notify users of successful gift
            await ctx.send(embed=self.success_embed(
                f"You gifted {quantity}x {item.name} to {target.display_name}!"
            ))
            
            # Try to notify recipient via DM
            try:
                embed = self.success_embed(
                    f"You received a gift from {ctx.author.display_name}!"
                )
                embed.add_field(
                    name="Gift Details",
                    value=f"{quantity}x {item.name}",
                    inline=False
                )
                embed.add_field(
                    name="Item Description",
                    value=item.description,
                    inline=False
                )
                
                await target.send(embed=embed)
            except:
                # Failed to send DM, not critical
                pass
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during item gifting: {e}")
            await ctx.send(embed=self.error_embed("An error occurred while gifting the item. Please try again."))
    
    async def gift_item_slash(self, interaction: discord.Interaction, item_id: int, quantity: int, target: discord.Member):
        """Handle gifting an item to another user (slash command version)."""
        if quantity <= 0:
            await interaction.response.send_message(
                embed=self.error_embed("Quantity must be greater than 0."),
                ephemeral=True
            )
            return
        
        if target.id == interaction.user.id:
            await interaction.response.send_message(
                embed=self.error_embed("You can't gift items to yourself."),
                ephemeral=True
            )
            return
        
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        target_id = target.id
        
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
                embed=self.error_embed(f"{item.name} cannot be traded or gifted."),
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
                    f"You don't have enough {item.name} to gift. You have: {inventory_item.quantity if inventory_item else 0}, trying to gift: {quantity}."
                ),
                ephemeral=True
            )
            return
        
        # Process the gift
        try:
            # Update sender's inventory
            inventory_item.quantity -= quantity
            
            # If quantity is zero, remove the item from inventory
            if inventory_item.quantity <= 0:
                db.session.delete(inventory_item)
            
            # Check if recipient already has this item in inventory
            target_inventory_item = InventoryItem.query.filter_by(
                user_id=db_target.id,
                item_id=item.id,
                guild_id=db_guild.id
            ).first()
            
            if target_inventory_item:
                # Update quantity for existing item
                target_inventory_item.quantity += quantity
            else:
                # Create new inventory entry
                target_inventory_item = InventoryItem(
                    user_id=db_target.id,
                    item_id=item.id,
                    guild_id=db_guild.id,
                    quantity=quantity
                )
                db.session.add(target_inventory_item)
            
            # Add gift transaction record
            from models import Transaction
            transaction = Transaction(
                user_id=db_user.id,
                guild_id=db_guild.id,
                transaction_type="gift",
                amount=0,  # No monetary value for gifts
                recipient_id=db_target.id,
                description=f"Gifted {quantity}x {item.name} to {target.display_name}"
            )
            db.session.add(transaction)
            
            # Commit changes
            db.session.commit()
            
            # Notify users of successful gift
            await interaction.response.send_message(
                embed=self.success_embed(f"You gifted {quantity}x {item.name} to {target.display_name}!")
            )
            
            # Try to notify recipient via DM
            try:
                embed = self.success_embed(
                    f"You received a gift from {interaction.user.display_name}!"
                )
                embed.add_field(
                    name="Gift Details",
                    value=f"{quantity}x {item.name}",
                    inline=False
                )
                embed.add_field(
                    name="Item Description",
                    value=item.description,
                    inline=False
                )
                
                await target.send(embed=embed)
            except:
                # Failed to send DM, not critical
                pass
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during item gifting: {e}")
            await interaction.response.send_message(
                embed=self.error_embed("An error occurred while gifting the item. Please try again."),
                ephemeral=True
            )
    
    @commands.has_permissions(administrator=True)
    async def addcategory_prefix(self, ctx, name: str, *, description: str):
        """Add a new item category with traditional prefix command."""
        await self.add_category(ctx, name, description)
    
    @app_commands.command(name="addcategory", description="Add a new item category (admin only)")
    @app_commands.describe(
        name="The name of the new category",
        description="The description of the category"
    )
    @app_commands.default_permissions(administrator=True)
    async def addcategory_slash(self, interaction: discord.Interaction, name: str, description: str):
        """Add a new item category with slash command."""
        await self.add_category_slash(interaction, name, description)
    
    async def add_category(self, ctx, name: str, description: str):
        """Handle adding a new item category."""
        # Check if category already exists
        existing = ItemCategory.query.filter(ItemCategory.name.ilike(name)).first()
        
        if existing:
            await ctx.send(embed=self.error_embed(f"A category named '{existing.name}' already exists."))
            return
        
        # Create new category
        try:
            new_category = ItemCategory(
                name=name,
                description=description
            )
            
            db.session.add(new_category)
            db.session.commit()
            
            await ctx.send(embed=self.success_embed(
                f"Created new item category: {name}"
            ))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating item category: {e}")
            await ctx.send(embed=self.error_embed("An error occurred while creating the category. Please try again."))
    
    async def add_category_slash(self, interaction: discord.Interaction, name: str, description: str):
        """Handle adding a new item category (slash command version)."""
        # Check for administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=self.error_embed("You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Check if category already exists
        existing = ItemCategory.query.filter(ItemCategory.name.ilike(name)).first()
        
        if existing:
            await interaction.response.send_message(
                embed=self.error_embed(f"A category named '{existing.name}' already exists."),
                ephemeral=True
            )
            return
        
        # Create new category
        try:
            new_category = ItemCategory(
                name=name,
                description=description
            )
            
            db.session.add(new_category)
            db.session.commit()
            
            await interaction.response.send_message(
                embed=self.success_embed(f"Created new item category: {name}")
            )
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating item category: {e}")
            await interaction.response.send_message(
                embed=self.error_embed("An error occurred while creating the category. Please try again."),
                ephemeral=True
            )
    
    @commands.has_permissions(administrator=True)
    async def additem_prefix(self, ctx, name: str, price: int, category: str, *, description: str):
        """Add a new item to the shop with traditional prefix command."""
        await self.add_item(ctx, name, price, category, description)
    
    @app_commands.command(name="additem", description="Add a new item to the shop (admin only)")
    @app_commands.describe(
        name="The name of the new item",
        price="The price in coins",
        category="The category name",
        description="The item description",
        is_consumable="Whether the item can be consumed (default: False)",
        is_tradeable="Whether the item can be traded (default: True)",
        is_limited="Whether the item has limited quantity (default: False)",
        quantity="The available quantity if limited"
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
        if price < 0:
            await ctx.send(embed=self.error_embed("Price must be a positive number."))
            return
        
        # Find the category
        category = ItemCategory.query.filter(
            ItemCategory.name.ilike(f"%{category_name}%")
        ).first()
        
        if not category:
            await ctx.send(embed=self.error_embed(
                f"Category '{category_name}' not found. Use !addcategory to create it first."
            ))
            return
        
        # Check if item with this name already exists
        existing = Item.query.filter(Item.name.ilike(name)).first()
        
        if existing:
            await ctx.send(embed=self.error_embed(f"An item named '{existing.name}' already exists."))
            return
        
        # Create new item
        try:
            new_item = Item(
                name=name,
                description=description,
                price=price,
                category_id=category.id,
                # Default values for other fields
                is_consumable=False,
                is_tradeable=True,
                is_limited=False
            )
            
            db.session.add(new_item)
            db.session.commit()
            
            await ctx.send(embed=self.success_embed(
                f"Created new item: {name} (Price: {price} coins, Category: {category.name})"
            ))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating item: {e}")
            await ctx.send(embed=self.error_embed("An error occurred while creating the item. Please try again."))
    
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
        # Check for administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=self.error_embed("You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        if price < 0:
            await interaction.response.send_message(
                embed=self.error_embed("Price must be a positive number."),
                ephemeral=True
            )
            return
        
        # Find the category
        category = ItemCategory.query.filter(
            ItemCategory.name.ilike(f"%{category_name}%")
        ).first()
        
        if not category:
            await interaction.response.send_message(
                embed=self.error_embed(f"Category '{category_name}' not found. Use /addcategory to create it first."),
                ephemeral=True
            )
            return
        
        # Check if item with this name already exists
        existing = Item.query.filter(Item.name.ilike(name)).first()
        
        if existing:
            await interaction.response.send_message(
                embed=self.error_embed(f"An item named '{existing.name}' already exists."),
                ephemeral=True
            )
            return
        
        # Create new item
        try:
            new_item = Item(
                name=name,
                description=description,
                price=price,
                category_id=category.id,
                is_consumable=is_consumable,
                is_tradeable=is_tradeable,
                is_limited=is_limited,
                quantity_available=quantity if is_limited else None
            )
            
            db.session.add(new_item)
            db.session.commit()
            
            await interaction.response.send_message(
                embed=self.success_embed(
                    f"Created new item: {name} (Price: {price} coins, Category: {category.name})"
                )
            )
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating item: {e}")
            await interaction.response.send_message(
                embed=self.error_embed("An error occurred while creating the item. Please try again."),
                ephemeral=True
            )
    
    @commands.has_permissions(administrator=True)
    async def removeitem_prefix(self, ctx, item_id: int):
        """Remove an item from the shop with traditional prefix command."""
        await self.remove_item(ctx, item_id)
    
    @app_commands.command(name="removeitem", description="Remove an item from the shop (admin only)")
    @app_commands.describe(item_id="The ID of the item to remove")
    @app_commands.default_permissions(administrator=True)
    async def removeitem_slash(self, interaction: discord.Interaction, item_id: int):
        """Remove an item from the shop with slash command."""
        await self.remove_item_slash(interaction, item_id)
    
    async def remove_item(self, ctx, item_id: int):
        """Handle removing an item from the shop."""
        # Find the item
        item = Item.query.get(item_id)
        
        if not item:
            await ctx.send(embed=self.error_embed(f"Item with ID {item_id} not found."))
            return
        
        # Check if any users own this item
        inventory_count = InventoryItem.query.filter_by(item_id=item.id).count()
        
        if inventory_count > 0:
            await ctx.send(embed=self.error_embed(
                f"Cannot remove '{item.name}'. {inventory_count} users currently own this item."
            ))
            return
        
        # Remove the item
        try:
            item_name = item.name
            db.session.delete(item)
            db.session.commit()
            
            await ctx.send(embed=self.success_embed(
                f"Removed item: {item_name} (ID: {item_id})"
            ))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error removing item: {e}")
            await ctx.send(embed=self.error_embed("An error occurred while removing the item. Please try again."))
    
    async def remove_item_slash(self, interaction: discord.Interaction, item_id: int):
        """Handle removing an item from the shop (slash command version)."""
        # Check for administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=self.error_embed("You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Find the item
        item = Item.query.get(item_id)
        
        if not item:
            await interaction.response.send_message(
                embed=self.error_embed(f"Item with ID {item_id} not found."),
                ephemeral=True
            )
            return
        
        # Check if any users own this item
        inventory_count = InventoryItem.query.filter_by(item_id=item.id).count()
        
        if inventory_count > 0:
            await interaction.response.send_message(
                embed=self.error_embed(
                    f"Cannot remove '{item.name}'. {inventory_count} users currently own this item."
                ),
                ephemeral=True
            )
            return
        
        # Remove the item
        try:
            item_name = item.name
            db.session.delete(item)
            db.session.commit()
            
            await interaction.response.send_message(
                embed=self.success_embed(f"Removed item: {item_name} (ID: {item_id})")
            )
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error removing item: {e}")
            await interaction.response.send_message(
                embed=self.error_embed("An error occurred while removing the item. Please try again."),
                ephemeral=True
            )

    @commands.command(name="investments", help="View your company investments")
    async def investments_prefix(self, ctx):
        """View your company investments."""
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        
        # Find database records
        db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
        db_user = User.query.filter_by(discord_id=str(user_id)).first()
        
        if not db_guild or not db_user:
            await ctx.send(embed=self.error_embed("Database error. Please try again later."))
            return
        
        # Find guild member record
        from models import GuildMember
        guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()
        
        if not guild_member:
            await ctx.send(embed=self.error_embed("Could not find your economy profile."))
            return
        
        # Get user's investments
        try:
            from models import Company
            with sa.create_engine(db.engine.url).connect() as conn:
                investments = conn.execute(sa.text("""
                    SELECT ci.*, c.name AS company_name
                    FROM company_investment ci
                    JOIN company c ON ci.company_id = c.id
                    WHERE ci.investor_id = :investor_id
                """), {"investor_id": guild_member.id}).fetchall()
            
            if not investments:
                await ctx.send(embed=self.info_embed(
                    "Your Investments", 
                    "You don't have any active company investments."
                ))
                return
            
            embed = self.create_embed(
                "Your Company Investments", 
                f"Here are your investments in companies:"
            )
            
            total_income = 0
            
            for inv in investments:
                # Calculate time remaining
                now = datetime.utcnow()
                expires = inv.expires_at.replace(tzinfo=None) if inv.expires_at.tzinfo else inv.expires_at
                time_left = expires - now
                days_left = max(0, time_left.days)
                
                # Format percentage as whole number with % sign
                percent = float(inv.percent_ownership) * 100
                
                # Add field for this investment
                embed.add_field(
                    name=f"Investment in {inv.company_name}",
                    value=(
                        f"Amount Invested: {inv.amount_invested} coins\n"
                        f"Ownership: {percent:.1f}%\n"
                        f"Time Remaining: {days_left} days\n"
                        f"Last Payment: {inv.last_payment_at.strftime('%Y-%m-%d') if inv.last_payment_at else 'No payments yet'}"
                    ),
                    inline=False
                )
                
                # Theoretically show estimated daily income
                estimated_daily = 50 * float(inv.percent_ownership)  # Assume company makes 1000 coins per day
                total_income += estimated_daily
            
            if total_income > 0:
                embed.set_footer(text=f"Estimated daily income: ~{total_income:.1f} coins (varies based on company performance)")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logging.error(f"Error retrieving investments: {e}")
            await ctx.send(embed=self.error_embed("An error occurred while retrieving your investments."))

    @app_commands.command(name="investments", description="View your company investments")
    async def investments_slash(self, interaction: discord.Interaction):
        """View your company investments with slash command."""
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
        
        # Find guild member record
        from models import GuildMember
        guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()
        
        if not guild_member:
            await interaction.response.send_message(
                embed=self.error_embed("Could not find your economy profile."),
                ephemeral=True
            )
            return
        
        # Get user's investments
        try:
            from models import Company
            with sa.create_engine(db.engine.url).connect() as conn:
                investments = conn.execute(sa.text("""
                    SELECT ci.*, c.name AS company_name
                    FROM company_investment ci
                    JOIN company c ON ci.company_id = c.id
                    WHERE ci.investor_id = :investor_id
                """), {"investor_id": guild_member.id}).fetchall()
            
            if not investments:
                await interaction.response.send_message(
                    embed=self.info_embed(
                        "Your Investments", 
                        "You don't have any active company investments."
                    ),
                    ephemeral=True
                )
                return
            
            embed = self.create_embed(
                "Your Company Investments", 
                f"Here are your investments in companies:"
            )
            
            total_income = 0
            
            for inv in investments:
                # Calculate time remaining
                now = datetime.utcnow()
                expires = inv.expires_at.replace(tzinfo=None) if inv.expires_at.tzinfo else inv.expires_at
                time_left = expires - now
                days_left = max(0, time_left.days)
                
                # Format percentage as whole number with % sign
                percent = float(inv.percent_ownership) * 100
                
                # Add field for this investment
                embed.add_field(
                    name=f"Investment in {inv.company_name}",
                    value=(
                        f"Amount Invested: {inv.amount_invested} coins\n"
                        f"Ownership: {percent:.1f}%\n"
                        f"Time Remaining: {days_left} days\n"
                        f"Last Payment: {inv.last_payment_at.strftime('%Y-%m-%d') if inv.last_payment_at else 'No payments yet'}"
                    ),
                    inline=False
                )
                
                # Theoretically show estimated daily income
                estimated_daily = 50 * float(inv.percent_ownership)  # Assume company makes 1000 coins per day
                total_income += estimated_daily
            
            if total_income > 0:
                embed.set_footer(text=f"Estimated daily income: ~{total_income:.1f} coins (varies based on company performance)")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logging.error(f"Error retrieving investments: {e}")
            await interaction.response.send_message(
                embed=self.error_embed("An error occurred while retrieving your investments."),
                ephemeral=True
            )
    
    async def process_investment_income_loop(self):
        """Background task that processes company investment income."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                now = datetime.utcnow()
                logging.info("Processing company investment income...")
                
                # Process company investment income
                with db.engine.begin() as conn:
                    # Find active investments
                    investments_result = conn.execute(sa.text("""
                        SELECT 
                            ci.id, 
                            ci.investor_id, 
                            ci.company_id, 
                            ci.amount_invested,
                            ci.percent_ownership,
                            u.discord_id as user_discord_id,
                            c.name as company_name,
                            gm.guild_id,
                            gm.user_id
                        FROM 
                            company_investment ci
                        JOIN 
                            guild_member gm ON ci.investor_id = gm.id
                        JOIN 
                            user u ON gm.user_id = u.id
                        JOIN 
                            company c ON ci.company_id = c.id
                        WHERE 
                            ci.expires_at > :now
                        AND 
                            (ci.last_payment_at IS NULL OR DATE(ci.last_payment_at) < DATE(:now))
                    """), {"now": now})
                    
                    investments = investments_result.fetchall()
                    logging.info(f"Found {len(investments)} investments due for payment")
                    
                    for inv in investments:
                        try:
                            # Generate some random income for the company (simulated)
                            company_daily_profit = random.randint(800, 1200)  # Random profit between 800-1200
                            
                            # Calculate investor's share based on ownership percentage
                            investor_share = int(company_daily_profit * float(inv.percent_ownership) / 100)
                            
                            if investor_share > 0:
                                # Add payment to investor's wallet
                                conn.execute(sa.text("""
                                    UPDATE guild_member
                                    SET wallet = wallet + :amount
                                    WHERE id = :investor_id
                                """), {"amount": investor_share, "investor_id": inv.investor_id})
                                
                                # Record transaction
                                conn.execute(sa.text("""
                                    INSERT INTO transaction (
                                        user_id, 
                                        guild_id, 
                                        transaction_type, 
                                        amount, 
                                        description, 
                                        timestamp
                                    )
                                    VALUES (
                                        :user_id,
                                        :guild_id,
                                        'investment_income',
                                        :amount,
                                        :description,
                                        :timestamp
                                    )
                                """), {
                                    "user_id": inv.user_id,
                                    "guild_id": inv.guild_id,
                                    "amount": investor_share,
                                    "description": f"Investment income from {inv.company_name}",
                                    "timestamp": now
                                })
                                
                                # Update last payment timestamp
                                conn.execute(sa.text("""
                                    UPDATE company_investment
                                    SET last_payment_at = :payment_time
                                    WHERE id = :investment_id
                                """), {"payment_time": now, "investment_id": inv.id})
                                
                                # Try to notify the user via DM
                                try:
                                    discord_user = self.bot.get_user(int(inv.user_discord_id)) if inv.user_discord_id else None
                                        
                                    if discord_user:
                                        embed = self.success_embed(
                                            f"You received {investor_share} coins from your investment in {inv.company_name}!"
                                        )
                                        await discord_user.send(embed=embed)
                                except Exception as notify_err:
                                    logging.error(f"Error sending investment notification: {notify_err}")
                        
                        except Exception as inv_err:
                            logging.error(f"Error processing individual investment {inv.id}: {inv_err}")
                    
                    # Commit all changes
                    conn.commit()
                    
                    # Clean up expired investments
                    conn.execute(sa.text("""
                        DELETE FROM company_investment
                        WHERE expires_at < :now
                    """), {"now": now})
                    conn.commit()
                
            except Exception as e:
                logging.error(f"Error in investment income processing: {e}")
                db.session.rollback()
            
            # Run once a day
            await asyncio.sleep(86400)  # 24 hours
    
    async def cog_load(self):
        """Called when the cog is loaded."""
        # Start background task for investment income
        self.bot.loop.create_task(self.process_investment_income_loop())

async def setup(bot):
    """Add the Items cog to the bot."""
    await bot.add_cog(Items(bot))
    logging.info("Items cog loaded successfully")
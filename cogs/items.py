import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
import logging
from datetime import datetime

from cogs.base_cog import BaseCog
from models import ItemCategory, Item, InventoryItem, Guild, User
from app import db

class Items(BaseCog):
    """Item shop and inventory management commands."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        
        # Register commands
        self.shop_prefix = commands.Command(self.shop_prefix, name="shop", 
                                         help="Browse the item shop")
        self.buy_prefix = commands.Command(self.buy_prefix, name="buy", 
                                        help="Buy an item from the shop")
        self.inventory_prefix = commands.Command(self.inventory_prefix, name="inventory", 
                                              help="View your inventory")
        self.use_prefix = commands.Command(self.use_prefix, name="use", 
                                        help="Use an item from your inventory")
        self.gift_prefix = commands.Command(self.gift_prefix, name="gift", 
                                         help="Gift an item to another user")
        self.additem_prefix = commands.Command(self.additem_prefix, name="additem", 
                                           help="Add a new item to the shop (admin only)")
        self.addcategory_prefix = commands.Command(self.addcategory_prefix, name="addcategory", 
                                               help="Add a new item category (admin only)")
        self.removeitem_prefix = commands.Command(self.removeitem_prefix, name="removeitem", 
                                              help="Remove an item from the shop (admin only)")
                                              
        # Register commands to bot
        self.bot.add_command(self.shop_prefix)
        self.bot.add_command(self.buy_prefix)
        self.bot.add_command(self.inventory_prefix)
        self.bot.add_command(self.use_prefix)
        self.bot.add_command(self.gift_prefix)
        self.bot.add_command(self.additem_prefix)
        self.bot.add_command(self.addcategory_prefix)
        self.bot.add_command(self.removeitem_prefix)
        
    async def shop_prefix(self, ctx, category=None):
        """Browse the item shop with traditional prefix command."""
        if category:
            await self.show_category_items(ctx, category)
        else:
            await self.show_shop_categories(ctx)
    
    @app_commands.command(name="shop", description="Browse items in the shop")
    @app_commands.describe(category="Optional category to filter items by")
    async def shop_slash(self, interaction: discord.Interaction, category: str = None):
        """Browse the item shop with slash command."""
        if category:
            await self.show_category_items_slash(interaction, category)
        else:
            await self.show_shop_categories_slash(interaction)
    
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
        category = ItemCategory.query.filter(
            ItemCategory.name.ilike(f"%{category_name}%")
        ).first()
        
        if not category:
            await ctx.send(embed=self.error_embed(f"Category '{category_name}' not found."))
            return
        
        # Get items in this category
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
        db_guild = Guild.query.filter_by(discord_id=str(guild_id)).first()
        db_user = User.query.filter_by(discord_id=str(user_id)).first()
        
        if not db_guild or not db_user:
            await ctx.send(embed=self.error_embed("Database error. Please try again later."))
            return
        
        # Find guild member record to access wallet
        from models import GuildMember
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
            # Deduct money from wallet
            guild_member.wallet -= item.price
            
            # Add transaction record
            from models import Transaction
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
            
            # Special handling for role rewards
            if item.is_role_reward and item.role_id:
                try:
                    role = ctx.guild.get_role(int(item.role_id))
                    if role:
                        await ctx.author.add_roles(role)
                except Exception as e:
                    logging.error(f"Error adding role for purchased item: {e}")
            
            # Commit changes
            db.session.commit()
            
            # Notify user of successful purchase
            await ctx.send(embed=self.success_embed(
                f"You purchased {item.name} for {item.price} coins!"
            ))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during item purchase: {e}")
            await ctx.send(embed=self.error_embed("An error occurred during purchase. Please try again."))
    
    async def purchase_item_slash(self, interaction: discord.Interaction, item_id: int):
        """Handle the purchase of an item (slash command version)."""
        # Get the item from database
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
            # Deduct money from wallet
            guild_member.wallet -= item.price
            
            # Add transaction record
            from models import Transaction
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
            
            # Special handling for role rewards
            if item.is_role_reward and item.role_id:
                try:
                    role = interaction.guild.get_role(int(item.role_id))
                    if role:
                        await interaction.user.add_roles(role)
                except Exception as e:
                    logging.error(f"Error adding role for purchased item: {e}")
            
            # Commit changes
            db.session.commit()
            
            # Notify user of successful purchase
            await interaction.response.send_message(
                embed=self.success_embed(f"You purchased {item.name} for {item.price} coins!")
            )
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during item purchase: {e}")
            await interaction.response.send_message(
                embed=self.error_embed("An error occurred during purchase. Please try again."),
                ephemeral=True
            )
    
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
        await ctx.send(embed=embed)
    
    async def show_inventory_slash(self, interaction: discord.Interaction):
        """Show a user's inventory (slash command version)."""
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
        await interaction.response.send_message(embed=embed)
    
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
            if "effect_type" in properties:
                effect_type = properties["effect_type"]
                
                # Economy boost items
                if effect_type == "money":
                    if "amount" in properties:
                        amount = int(properties["amount"])
                        
                        # Find guild member record to access wallet
                        from models import GuildMember
                        guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()
                        
                        if guild_member:
                            guild_member.wallet += amount
                            effect_message += f" and received {amount} coins!"
                            
                            # Add transaction record
                            from models import Transaction
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
                
                # Add more effect types as needed
            
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
            db.session.rollback()
            logging.error(f"Error during item usage: {e}")
            await ctx.send(embed=self.error_embed("An error occurred while using the item. Please try again."))
    
    async def use_item_slash(self, interaction: discord.Interaction, item_id: int):
        """Handle using an item from inventory (slash command version)."""
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
            if "effect_type" in properties:
                effect_type = properties["effect_type"]
                
                # Economy boost items
                if effect_type == "money":
                    if "amount" in properties:
                        amount = int(properties["amount"])
                        
                        # Find guild member record to access wallet
                        from models import GuildMember
                        guild_member = GuildMember.query.filter_by(user_id=db_user.id, guild_id=db_guild.id).first()
                        
                        if guild_member:
                            guild_member.wallet += amount
                            effect_message += f" and received {amount} coins!"
                            
                            # Add transaction record
                            from models import Transaction
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
                
                # Add more effect types as needed
            
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

async def setup(bot):
    """Add the Items cog to the bot."""
    await bot.add_cog(Items(bot))
    logging.info("Items cog loaded successfully")
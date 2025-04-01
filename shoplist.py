import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json

from models import ItemCategory, Item
from app import db

# These functions will be added to the Items cog class
# Copy and paste them into the correct location in cogs/items.py

@commands.command(name="shoplist", help="List all shop categories and items with prices")
async def shoplist_prefix(self, ctx):
    """List all shop categories and items with prices in a formatted output."""
    await self.list_shop_items(ctx)
    
@app_commands.command(name="shoplist", description="List all shop categories and items with prices")
async def shoplist_slash(self, interaction: discord.Interaction):
    """List all shop categories and items with prices in a formatted output (slash command version)."""
    await self.list_shop_items(interaction)

async def list_shop_items(self, ctx):
    """Show a comprehensive list of all shop categories and their items with prices."""
    from app import app
    with app.app_context():
        categories = ItemCategory.query.all()
        
        if not categories:
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(embed=self.info_embed("Shop", "There are no categories in the shop yet."))
            else:
                await ctx.send(embed=self.info_embed("Shop", "There are no categories in the shop yet."))
            return
        
        # Create paginated embeds for all categories and items
        all_embeds = []
        
        for category in categories:
            items = Item.query.filter_by(category_id=category.id).all()
            if not items:
                continue
                
            embed = self.create_embed(
                f"Shop Items - {category.name}",
                f"**{category.description}**\n\nItems available in this category:"
            )
            
            items_text = ""
            for item in items:
                # Get additional properties
                properties = {}
                if hasattr(item, 'properties_json') and item.properties_json:
                    try:
                        properties = json.loads(item.properties_json)
                    except:
                        properties = {}
                
                # Item status info
                status_info = ""
                if hasattr(item, 'is_limited') and item.is_limited:
                    remaining = properties.get('quantity', 0)
                    status_info = f" | Limited: {remaining} left"
                
                # Consumable/tradeable flags
                flags = []
                if hasattr(item, 'is_consumable') and item.is_consumable:
                    flags.append("Consumable")
                if hasattr(item, 'is_tradeable') and not item.is_tradeable:
                    flags.append("Not Tradeable")
                
                flags_text = f" | {', '.join(flags)}" if flags else ""
                
                # Add the item to the list
                items_text += f"**ID {item.id}:** {item.name} - 💰 **{item.price}** coins{status_info}{flags_text}\n"
                items_text += f"*{item.description}*\n\n"
            
            # Add field with items
            embed.add_field(name="Items", value=items_text or "No items available", inline=False)
            embed.set_footer(text=f"Use the !buy <id> or /buy command to purchase an item")
            
            all_embeds.append(embed)
        
        if not all_embeds:
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(embed=self.info_embed("Shop", "There are no items in the shop yet."))
            else:
                await ctx.send(embed=self.info_embed("Shop", "There are no items in the shop yet."))
            return
            
        # If only one embed, send it directly
        if len(all_embeds) == 1:
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(embed=all_embeds[0])
            else:
                await ctx.send(embed=all_embeds[0])
            return
            
        # Set up pagination
        current_page = 0
        
        # Create the message with the first page
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(embed=all_embeds[current_page])
            msg = await ctx.original_response()
        else:
            msg = await ctx.send(embed=all_embeds[current_page])
            
        # Add navigation reactions
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")
        
        def check(reaction, user):
            return (
                user == (ctx.user if isinstance(ctx, discord.Interaction) else ctx.author) and
                str(reaction.emoji) in ["⬅️", "➡️"] and
                reaction.message.id == msg.id
            )
        
        # Wait for reactions
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                
                # Handle pagination
                if str(reaction.emoji) == "➡️" and current_page < len(all_embeds) - 1:
                    current_page += 1
                    await msg.edit(embed=all_embeds[current_page])
                elif str(reaction.emoji) == "⬅️" and current_page > 0:
                    current_page -= 1
                    await msg.edit(embed=all_embeds[current_page])
                
                # Remove the user's reaction
                await msg.remove_reaction(reaction.emoji, user)
                
            except asyncio.TimeoutError:
                # Remove navigation reactions after timeout
                try:
                    await msg.clear_reactions()
                except:
                    pass
                break
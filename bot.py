import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import json
import datetime
from utils.database import Database
from utils.config import PREFIX

# Initialize bot with all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Create initial data directories if they don't exist
os.makedirs('data', exist_ok=True)

# Initialize database
db = Database()

@bot.event
async def on_ready():
    """Event triggered when the bot is ready and connected to Discord."""
    # Set up more detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')

    # Load cogs (extensions)
    await load_extensions()

    # Start daily reward loop
    bot.loop.create_task(daily_reward_loop())

    # Sync slash commands with Discord
    try:
        logging.info("Syncing slash commands...")

        # First, sync commands for each cog individually
        for cog_name in bot.cogs:
            cog = bot.get_cog(cog_name)
            if hasattr(cog, 'sync_slash_commands'):
                try:
                    await cog.sync_slash_commands()
                    logging.info(f"Successfully synced {cog_name} commands")
                except Exception as e:
                    logging.error(f"Error syncing {cog_name} commands: {e}")

        # Then, sync the global command tree
        commands = await bot.tree.sync()
        logging.info(f"Successfully synced {len(commands)} slash commands!")
    except discord.HTTPException as e:
        if e.code == 429:  # Rate limit error
            logging.warning("Rate limited while syncing commands. Use the /admin_sync command after a few minutes.")
        else:
            logging.error(f"Failed to sync slash commands: {e}")

    # Set bot status
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help or /help"))

    logging.info("Bot is ready!")

async def load_extensions():
    """Load all cog extensions."""
    for extension in ['cogs.economy', 'cogs.company', 'cogs.moderation', 'cogs.betting', 'cogs.items_new']:
        try:
            await bot.load_extension(extension)
            logging.info(f'Loaded extension: {extension}')
        except Exception as e:
            logging.error(f'Failed to load extension {extension}: {e}')

async def daily_reward_loop():
    """Loop that gives daily rewards to all users."""
    while True:
        # Wait until midnight
        now = datetime.datetime.now()
        tomorrow = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_midnight = (tomorrow - now).total_seconds()

        logging.info(f"Daily reward loop will run in {seconds_until_midnight} seconds")
        await asyncio.sleep(seconds_until_midnight)

        # Give daily rewards
        logging.info("Giving daily rewards to all users")
        db.give_daily_rewards_to_all()

        # Sleep for a minute to avoid multiple triggers
        await asyncio.sleep(60)

@bot.event
async def on_message(message):
    """Event triggered when a message is sent in a channel the bot can see."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process commands
    await bot.process_commands(message)

    # Check if user exists in database, if not create them
    db.get_or_create_user(message.author.id)

    # If user is in a company, give them activity bonus
    db.update_activity(message.author.id)

@bot.command(name="help")
async def help_command(ctx, category=None):
    """Display a helpful guide to bot commands."""
    prefix = ctx.prefix

    # Create base embed
    embed = discord.Embed(
        title="Discord Economy Bot - Help Menu",
        description=f"Use `{prefix}help <category>` to view specific commands.\nAll commands are also available as slash commands!",
        color=discord.Color.blue()
    )

    # Add footer with version info
    embed.set_footer(text=f"Discord Economy Bot | Use {prefix}help or /help")

    # General help menu (categories)
    if not category:
        embed.title = "Discord Economy Bot - Help Menu"
        embed.description = f"Use `{prefix}help <category>` to view specific commands.\nAll commands are also available as slash commands!"
        embed.color = discord.Color.blue()

        categories = [
            ("🏦", "Economy", f"`{prefix}help economy`", "Money, bank, and daily rewards"),
            ("🏢", "Company", f"`{prefix}help company`", "Company creation and management"),
            ("🛡️", "Moderation", f"`{prefix}help moderation`", "Role-based timeout commands"),
            ("👥", "General", f"`{prefix}help general`", "General utility commands"),
            ("🎲", "Bets", f"`{prefix}help bets`", "AI-powered betting system"),
            ("🎁", "Items", f"`{prefix}help items`", "Shop and inventory system"),
            ("📈", "Events", f"`{prefix}help events`", "Economic events affecting the economy")
        ]

        for emoji, name, command, desc in categories:
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"{command} - {desc}",
                inline=False
            )

        embed.set_footer(text=f"Discord Economy Bot | Use {prefix}help or /help")

    # Economy commands
    elif category.lower() == "economy":
        embed.title = "💰 Economy Commands"
        embed.description = "```ini\n[Commands for managing your money and earning rewards]```"
        embed.color = discord.Color.gold()

        embed.add_field(name=f"💳 {prefix}balance", value="```ini\n[Check your current balance]```", inline=False)
        embed.add_field(name=f"🎁 {prefix}daily", value="```ini\n[Claim your daily reward of $100]```", inline=False)
        embed.add_field(name=f"💳 {prefix}deposit <amount>", value="```ini\n[Deposit money to your bank]```", inline=False)
        embed.add_field(name=f"💸 {prefix}withdraw <amount>", value="```ini\n[Withdraw money from your bank]```", inline=False)
        embed.add_field(name=f"📤 {prefix}transfer <@user> <amount>", value="```ini\n[Send money to another user]```", inline=False)
        embed.add_field(name=f"📥 {prefix}request <@user> <amount> [reason]", value="```ini\n[Request money from another user]```", inline=False)
        embed.add_field(name=f"📋 {prefix}requests", value="```ini\n[View your pending money requests]```", inline=False)
        embed.add_field(name=f"❌ {prefix}reject <request_id>", value="```ini\n[Reject a money request]```", inline=False)
        embed.add_field(name=f"⚔️ {prefix}quest", value="```ini\n[Get a random quest to earn money]```", inline=False)
        embed.add_field(name=f"🦹 {prefix}rob <@user>", value="```ini\n[Attempt to rob another user (requires 5+ people)]```", inline=False)
        embed.add_field(name=f"🏆 {prefix}leaderboard", value="```ini\n[Display the richest users on the server]```", inline=False)

    # Company commands
    elif category.lower() == "company":
        embed.title = "🏢 Company Commands"
        embed.description = "```ini\n[Commands for managing companies and employees]```"
        embed.color = discord.Color.gold()

        embed.add_field(name=f"🎯 {prefix}createcompany <name>", value="```ini\n[Create a new company (requires higher role)]```", inline=False)
        embed.add_field(name=f"ℹ️ {prefix}company [name]", value="```ini\n[Display info about your company or another company]```", inline=False)
        embed.add_field(name=f"📨 {prefix}invite <@user>", value="```ini\n[Invite a user to your company]```", inline=False)
        embed.add_field(name=f"🚪 {prefix}leave", value="```ini\n[Leave your current company]```", inline=False)
        embed.add_field(name=f"👢 {prefix}kick <@user>", value="```ini\n[Kick a member from your company (owner only)]```", inline=False)
        embed.add_field(name=f"💥 {prefix}disband", value="```ini\n[Disband your company as the owner]```", inline=False)
        embed.add_field(name=f"📑 {prefix}companies", value="```ini\n[List all companies on the server]```", inline=False)

    # Moderation commands
    elif category.lower() == "moderation":
        embed.title = "🛡️ Moderation Commands"
        embed.description = "```ini\n[Commands for moderating users with timeouts]```"
        embed.color = discord.Color.gold()

        embed.add_field(name=f"⏰ {prefix}timeout <@user>", value="```ini\n[Timeout a user based on your role permissions]```", inline=False)
        embed.add_field(name=f"💰 {prefix}timeout_cost", value="```ini\n[Check the cost of using the timeout command]```", inline=False)
        embed.add_field(name=f"⚖️ {prefix}timeout_limit", value="```ini\n[Check your timeout duration limit based on your roles]```", inline=False)
        embed.add_field(name=f"📜 {prefix}timeout_history [@user]", value="```ini\n[View timeout history for yourself or another user]```", inline=False)

    # Betting commands
    elif category.lower() == "bets":
        embed.title = "Betting Commands"
        embed.description = "```ini\n[Commands for AI-powered betting system]```"
        embed.color = discord.Color.gold()

        embed.add_field(name=f"{prefix}createbet <event_description>", value="```ini\n[Create a new betting event with AI-generated options]```", inline=False)
        embed.add_field(name=f"{prefix}sportsbet <description> <end_hours> <option1> <option2> [option3] [option4]", 
                       value="```ini\n[Create a sports bet that will be automatically resolved]```", inline=False)
        embed.add_field(name=f"{prefix}placebet <bet_id> <option> <amount>", value="```ini\n[Place a bet on an event]```", inline=False)
        embed.add_field(name=f"{prefix}activebets", value="```ini\n[View all active betting events]```", inline=False)
        embed.add_field(name=f"{prefix}pastbets [limit]", value="```ini\n[View past resolved betting events]```", inline=False)
        embed.add_field(name=f"{prefix}mybet <bet_id>", value="```ini\n[View your bet on an event]```", inline=False)
        embed.add_field(name=f"{prefix}cancelbet <bet_id>", value="```ini\n[Cancel your bet and get a refund]```", inline=False)
        embed.add_field(name=f"{prefix}resolvebet <bet_id> <winning_option>", value="```ini\n[Admin only: Manually resolve a bet]```", inline=False)

    # General commands
    elif category.lower() == "general":
        embed.title = "📊 General Commands"
        embed.description = "```ini\n[General utility commands]```"
        embed.color = discord.Color.gold()

        embed.add_field(name=f"❓ {prefix}help [category]", value="```ini\n[Display this help menu]```", inline=False)
        embed.add_field(name=f"🏓 {prefix}ping", value="```ini\n[Check the bot's response time]```", inline=False)
        embed.add_field(name=f"ℹ️ {prefix}info", value="```ini\n[Display information about the bot]```", inline=False)

    # Items commands
    elif category.lower() == "items":
        embed.title = "🎁 Items and Shop Commands"
        embed.description = "```ini\n[Commands for browsing the shop and managing your inventory]```"
        embed.color = discord.Color.gold()

        embed.add_field(name=f"🛍️ {prefix}shop [category]", value="```ini\n[Browse the item shop or specific category]```", inline=False)
        embed.add_field(name=f"💰 {prefix}buy <item_id>", value="```ini\n[Buy an item from the shop]```", inline=False)
        embed.add_field(name=f"🎒 {prefix}inventory", value="```ini\n[View your inventory]```", inline=False)
        embed.add_field(name=f"📦 {prefix}use <item_id>", value="```ini\n[Use a consumable item from your inventory]```", inline=False)
        embed.add_field(name=f"🎀 {prefix}gift <item_id> <quantity> <@user>", value="```ini\n[Gift an item to another user]```", inline=False)
        embed.add_field(name=f"➕ {prefix}additem <name> <price> <category> <description>", value="```ini\n[Admin only: Add a new item to the shop]```", inline=False)
        embed.add_field(name=f"📁 {prefix}addcategory <name> <description>", value="```ini\n[Admin only: Add a new item category]```", inline=False)
        embed.add_field(name=f"➖ {prefix}removeitem <item_id>", value="```ini\n[Admin only: Remove an item from the shop]```", inline=False)

    # Events commands
    elif category.lower() == "events":
        embed.title = "Economic Events Commands"
        embed.description = "```ini\n[Commands for interacting with dynamic economic events.]```"
        embed.color = discord.Color.gold()

        embed.add_field(name=f"{prefix}events", value="```ini\n[View current active economic events]```", inline=False)
        embed.add_field(name=f"{prefix}event_info <event_id>", value="```ini\n[Get details about a specific economic event]```", inline=False)
        embed.add_field(name=f"{prefix}generate_event", value="```ini\n[Admin only: Force generate a new economic event]```", inline=False)
        embed.add_field(name=f"{prefix}end_event <event_id>", value="```ini\n[Admin only: End an active economic event]```", inline=False)

    else:
        embed.title = "Unknown Category"
        embed.description = f"Category '{category}' not found. Use `{prefix}help` to see available categories."

    await ctx.send(embed=embed)

# Slash command version of help
@bot.tree.command(name="help", description="Display a helpful guide to bot commands")
@app_commands.describe(category="The category of commands to display")
@app_commands.choices(category=[
    app_commands.Choice(name="Economy", value="economy"),
    app_commands.Choice(name="Company", value="company"),
    app_commands.Choice(name="Moderation", value="moderation"),
    app_commands.Choice(name="General", value="general"),
    app_commands.Choice(name="Bets", value="bets"),
    app_commands.Choice(name="Items", value="items"),
    app_commands.Choice(name="Events", value="events")
])
async def help_slash(interaction: discord.Interaction, category: str = None):
    ctx = await bot.get_context(interaction.message) if interaction.message else None
    prefix = PREFIX if not ctx else ctx.prefix

    # Create base embed
    embed = discord.Embed(
        title="Discord Economy Bot - Help Menu",
        description=f"Use `/help category:category_name` to view specific commands.\nThese commands are also available with the `{prefix}` prefix!",
        color=discord.Color.blue()
    )

    # Add footer with version info
    embed.set_footer(text=f"Discord Economy Bot | Use {prefix}help or /help")

    # General help menu (categories)
    if not category:
        embed.title = "Discord Economy Bot - Help Menu"
        embed.description = "Use `/help category:category_name` to view specific commands.\nThese commands are also available with prefix commands!"
        embed.color = discord.Color.blue()

        categories = [
            ("🏦", "Economy", "/help economy", "Money, bank, and daily rewards"),
            ("🏢", "Company", "/help company", "Company creation and management"),
            ("🛡️", "Moderation", "/help moderation", "Role-based timeout commands"),
            ("👥", "General", "/help general", "General utility commands"),
            ("🎲", "Bets", "/help bets", "AI-powered betting system"),
            ("🎁", "Items", "/help items", "Shop and inventory system"),
            ("📈", "Events", "/help events", "Economic events affecting the economy")
        ]

        for emoji, name, command, desc in categories:
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"`{command}` - {desc}",
                inline=False
            )

        embed.set_footer(text=f"Discord Economy Bot | Use {prefix}help or /help")

    # Economy commands
    elif category.lower() == "economy":
        embed.title = "💰 Economy Commands"
        embed.description = "```ini\n[Commands for managing your money and earning rewards]```"
        embed.color = discord.Color.gold()

        embed.add_field(name="/balance", value="Check your current balance", inline=False)
        embed.add_field(name="/daily", value="Claim your daily reward of $100", inline=False)
        embed.add_field(name="/deposit amount:<amount>", value="Deposit money to your bank", inline=False)
        embed.add_field(name="/withdraw amount:<amount>", value="Withdraw money from your bank", inline=False)
        embed.add_field(name="/transfer user:<@user> amount:<amount>", value="Send money to another user", inline=False)
        embed.add_field(name="/request user:<@user> amount:<amount> [reason]", value="Request money from another user", inline=False)
        embed.add_field(name="/requests", value="View your pending money requests", inline=False)
        embed.add_field(name="/reject request_id:<id>", value="Reject a money request", inline=False)
        embed.add_field(name="/quest", value="Get a random quest to earn money", inline=False)
        embed.add_field(name="/rob user:<@user>", value="Attempt to rob another user (requires 5+ people)", inline=False)
        embed.add_field(name="/leaderboard", value="Display the richest users on the server", inline=False)

    # Company commands
    elif category.lower() == "company":
        embed.title = "🏢 Company Commands"
        embed.description = "```ini\n[Commands for managing companies and employees]```"
        embed.color = discord.Color.gold()

        embed.add_field(name="/createcompany name:<name>", value="Create a new company (requires higher role)", inline=False)
        embed.add_field(name="/company [name]", value="Display info about your company or another company", inline=False)
        embed.add_field(name="/invite user:<@user>", value="Invite a user to your company", inline=False)
        embed.add_field(name="/leave", value="Leave your current company", inline=False)
        embed.add_field(name="/kick user:<@user>", value="Kick a member from your company (owner only)", inline=False)
        embed.add_field(name="/disband", value="Disband your company as the owner", inline=False)
        embed.add_field(name="/companies", value="List all companies on the server", inline=False)

    # Moderation commands
    elif category.lower() == "moderation":
        embed.title = "🛡️ Moderation Commands"
        embed.description = "```ini\n[Commands for moderating users with timeouts]```"
        embed.color = discord.Color.gold()

        embed.add_field(name="/timeout user:<@user>", value="Timeout a user based on your role permissions", inline=False)
        embed.add_field(name="/timeout_cost", value="Check the cost of using the timeout command", inline=False)
        embed.add_field(name="/timeout_limit", value="Check your timeout duration limit based on your roles", inline=False)
        embed.add_field(name="/timeout_history [user:<@user>]", value="View timeout history for yourself or another user", inline=False)

    # Betting commands
    elif category.lower() == "bets":
        embed.title = "🎲 Betting Commands"
        embed.description = "```ini\n[Commands for AI-powered betting system]```"
        embed.color = discord.Color.gold()

        embed.add_field(name="/createbet event_description:<description>", value="Create a new betting event with AI-generated options", inline=False)
        embed.add_field(name="/sportsbet match_description:<desc> end_time:<hours> option1:<option1> option2:<option2>", 
                       value="Create a sports bet that will be automatically resolved", inline=False)
        embed.add_field(name="/placebet bet_id:<id> choice:<option> amount:<amount>", value="Place a bet on an event", inline=False)
        embed.add_field(name="/activebets", value="View all active betting events", inline=False)
        embed.add_field(name="/pastbets limit:<number>", value="View past resolved betting events", inline=False)
        embed.add_field(name="/mybet bet_id:<id>", value="View your bet on an event", inline=False)
        embed.add_field(name="/cancelbet bet_id:<id>", value="Cancel your bet and get a refund", inline=False)
        embed.add_field(name="/resolvebet bet_id:<id> winner:<option>", value="Admin only: Manually resolve a bet", inline=False)

    # General commands
    elif category.lower() == "general":
        embed.title = "📊 General Commands"
        embed.description = "```ini\n[General utility commands]```"
        embed.color = discord.Color.gold()

        embed.add_field(name="/help [category]", value="Display this help menu", inline=False)
        embed.add_field(name="/ping", value="Check the bot's response time", inline=False)
        embed.add_field(name="/info", value="Display information about the bot", inline=False)

    # Items commands
    elif category.lower() == "items":
        embed.title = "🎁 Items and Shop Commands"
        embed.description = "```ini\n[Commands for browsing the shop and managing your inventory]```"
        embed.color = discord.Color.gold()

        embed.add_field(name="/shop [category]", value="Browse the item shop or specific category", inline=False)
        embed.add_field(name="/buy item_id:<id>", value="Buy an item from the shop", inline=False)
        embed.add_field(name="/inventory", value="View your inventory", inline=False)
        embed.add_field(name="/use item_id:<id>", value="Use a consumable item from your inventory", inline=False)
        embed.add_field(name="/gift item_id:<id> quantity:<amount> target:<@user>", value="Gift an item to another user", inline=False)
        embed.add_field(name="/additem name:<name> price:<amount> category:<cat> description:<desc>", value="Admin only: Add a new item to the shop", inline=False)
        embed.add_field(name="/addcategory name:<name> description:<desc>", value="Admin only: Add a new item category", inline=False)
        embed.add_field(name="/removeitem item_id:<id>", value="Admin only: Remove an item from the shop", inline=False)

    # Events commands
    elif category.lower() == "events":
        embed.title = "📈 Economic Events Commands"
        embed.description = "```ini\n[Commands for interacting with dynamic economic events]```"
        embed.color = discord.Color.gold()

        embed.add_field(name="/events", value="View current active economic events", inline=False)
        embed.add_field(name="/event_info event_id:<id>", value="Get details about a specific economic event", inline=False)
        embed.add_field(name="/generate_event", value="Admin only: Force generate a new economic event", inline=False)
        embed.add_field(name="/end_event event_id:<id>", value="Admin only: End an active economic event", inline=False)

    else:
        embed.title = "Unknown Category"
        embed.description = f"Category '{category}' not found. Use `/help` to see available categories."

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Simple ping command - both prefix and slash
@bot.command(name="ping")
async def ping(ctx):
    """Check the bot's latency."""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

@bot.tree.command(name="ping", description="Check the bot's response time")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms", ephemeral=True)

# Bot info command - both prefix and slash
@bot.command(name="info")
async def info(ctx):
    """Display information about the bot."""
    embed = discord.Embed(
        title="Discord Economy Bot",
        description="A Discord economy bot with company creation, money management, bank system, and role-based timeout features",
        color=discord.Color.blue()
    )

    # Add various info fields
    embed.add_field(name="Version", value="1.0.0", inline=True)
    embed.add_field(name="Prefix", value=bot.command_prefix, inline=True)
    embed.add_field(name="Server Count", value=len(bot.guilds), inline=True)

    embed.add_field(name="Features", value="""
• Economy system with wallet and bank
• Daily rewards of $100 for all users
• Company creation and management
• AI-generated quests for earning money
• Role-based timeout system
• Item shop and inventory system
• Dynamic economic events
    """, inline=False)

    embed.set_footer(text=f"Made with ❤️ for Discord")

    await ctx.send(embed=embed)

@bot.tree.command(name="info", description="Display information about the bot")
async def info_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Discord Economy Bot",
        description="A Discord economy bot with company creation, money management, bank system, and role-based timeout features",
        color=discord.Color.blue()
    )

    # Add various info fields
    embed.add_field(name="Version", value="1.0.0", inline=True)
    embed.add_field(name="Prefix", value=bot.command_prefix, inline=True)
    embed.add_field(name="Server Count", value=len(bot.guilds), inline=True)

    embed.add_field(name="Features", value="""
• Economy system with wallet and bank
• Daily rewards of $100 for all users
• Company creation and management
• AI-generated quests for earning money
• Role-based timeout system
• Item shop and inventory system
• Dynamic economic events
    """, inline=False)

    embed.set_footer(text=f"Made with ❤️ for Discord")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Admin commands
@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_commands(ctx):
    """Manually sync slash commands (admin only)."""
    try:
        logging.info(f"Admin {ctx.author.name} manually syncing slash commands")

        # First sync individual cogs (which may add commands to the tree)
        for cog_name in bot.cogs:
            cog = bot.get_cog(cog_name)
            if hasattr(cog, 'sync_slash_commands'):
                try:
                    await cog.sync_slash_commands()
                    logging.info(f"Successfully synced {cog_name} commands")
                    await ctx.send(f"✅ Synced {cog_name} commands!")
                except Exception as e:
                    logging.error(f"Error syncing {cog_name} commands: {e}")
                    await ctx.send(f"❌ Error syncing {cog_name} commands: {e}")

        # Then sync the global command tree
        bot.tree.clear_commands(guild=None)
        synced = await bot.tree.sync()
        logging.info(f"Successfully synced {len(synced)} global commands")
        await ctx.send(f"✅ Slash commands cleared and resynced globally! ({len(synced)} commands)")
    except Exception as e:
        logging.error(f"Manual sync error: {e}")
        await ctx.send(f"❌ Error syncing slash commands: {e}")

@bot.tree.command(name="admin_sync", description="Manually sync slash commands (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def sync_commands_slash(interaction: discord.Interaction):
    """Slash command for manually syncing commands."""
    try:
        logging.info(f"Admin {interaction.user.name} manually syncing slash commands")

        # First sync individual cogs (which may add commands to the tree)
        await interaction.response.send_message("🔄 Syncing commands...", ephemeral=True)

        for cog_name in bot.cogs:
            cog = bot.get_cog(cog_name)
            if hasattr(cog, 'sync_slash_commands'):
                try:
                    await cog.sync_slash_commands()
                    logging.info(f"Successfully synced {cog_name} commands")
                    await interaction.followup.send(f"✅ Synced {cog_name} commands!", ephemeral=True)
                except Exception as e:
                    logging.error(f"Error syncing {cog_name} commands: {e}")
                    await interaction.followup.send(f"❌ Error syncing {cog_name} commands: {e}", ephemeral=True)

        # Then sync the global command tree
        bot.tree.clear_commands(guild=None)
        synced = await bot.tree.sync()
        logging.info(f"Successfully synced {len(synced)} global commands")
        await interaction.followup.send(f"✅ Slash commands cleared and resynced globally! ({len(synced)} commands)", ephemeral=True)
    except Exception as e:
        logging.error(f"Manual sync error: {e}")
        try:
            await interaction.followup.send(f"❌ Error syncing slash commands: {e}", ephemeral=True)
        except:
            await interaction.response.send_message(f"❌ Error syncing slash commands: {e}", ephemeral=True)

# Error handlers for permission checks
@sync_commands.error
async def sync_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permissions to use this command!")
    else:
        logging.error(f"Sync command error: {error}")
        await ctx.send(f"❌ An error occurred: {error}")

@sync_commands_slash.error
async def sync_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need administrator permissions to use this command!", ephemeral=True)
    else:
        logging.error(f"Sync slash command error: {error}")
        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)

def run_bot(token):
    """Run the bot with the given token."""
    import functools
    from app import app

    # Create a decorator to handle Flask application context
    def with_app_context(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with app.app_context():
                return await func(*args, **kwargs)
        return wrapper

    # Apply the decorator to command invoke method
    original_invoke = bot.invoke
    bot.invoke = with_app_context(original_invoke)

    bot.run(token)
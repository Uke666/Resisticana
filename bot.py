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

    # Create base embed with consistent styling
    embed = discord.Embed(
        title="Discord Economy Bot - Help Menu",
        description=f"Use `{prefix}help <category>` to view specific commands.\nAll commands are also available as slash commands!",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Discord Economy Bot")

    # Categories for organization
    categories = {
        "economy": ("🏠 Economy", "Money, bank, and daily rewards"),
        "company": ("🏛️ Company", "Company creation and management"),
        "moderation": ("🛡️ Moderation", "Role-based bomb commands"),
        "general": ("👤 General", "General utility commands"),
        "bets": ("🎲 Bets", "AI-powered betting system"),
        "items": ("🎁 Items", "Shop and inventory system"),
        "events": ("📈 Events", "Economic events affecting the economy")
    }

    # General help menu (categories)
    if not category:
        embed.title = "Discord Economy Bot - Help Menu"
        embed.description = f"Use `{prefix}help <category>` to view specific commands.\nAll commands are also available as slash commands!"
        embed.color = discord.Color.from_rgb(47, 49, 54)
        
        for cat, (emoji_title, desc) in categories.items():
            embed.add_field(
                name=f"{emoji_title}",
                value=f"`{prefix}help {cat}` - {desc}",
                inline=False
            )
        
        embed.set_footer(text=f"Discord Economy Bot | Use {prefix}help or /help")
    else:
        cat = category.lower()
        if cat in categories:
            emoji_title, desc = categories[cat]
            embed.title = emoji_title
            embed.description = f"```ini\n[{desc}]```"

            # Add command lists based on category
            if cat == "economy":
                commands = [
                    ("balance", "Check your current balance"),
                    ("daily", "Claim your daily reward of $100"),
                    ("deposit <amount>", "Deposit money to your bank"),
                    ("withdraw <amount>", "Withdraw money from your bank"),
                    ("transfer <@user> <amount>", "Send money to another user"),
                    ("request <@user> <amount> [reason]", "Request money from another user"),
                    ("requests", "View your pending money requests"),
                    ("reject <request_id>", "Reject a money request"),
                    ("quest", "Get a random quest to earn money"),
                    ("rob <@user>", "Attempt to rob another user (requires 5+ people)"),
                    ("leaderboard", "Display the richest users on the server")
                ]
            elif cat == "company":
                commands = [
                    ("createcompany <name>", "Create a new company (requires higher role)"),
                    ("company [name]", "Display info about your company or another company"),
                    ("invite <@user>", "Invite a user to your company"),
                    ("leave", "Leave your current company"),
                    ("kick <@user>", "Kick a member from your company (owner only)"),
                    ("disband", "Disband your company as the owner"),
                    ("companies", "List all companies on the server")
                ]
            elif cat == "moderation":
                commands = [
                    ("bomb <@user>", "Bomb a user based on your role permissions"),
                    ("bombcost", "Check the cost of using the bomb command"),
                    ("bomblimit", "Check your bomb duration limit based on your roles"),
                    ("bombhistory [@user]", "View bomb history for yourself or another user")
                ]
            elif cat == "general":
                commands = [
                    ("help [category]", "Display this help menu"),
                    ("ping", "Check the bot's response time"),
                    ("info", "Display information about the bot")
                ]
            elif cat == "bets":
                commands = [
                    ("createbet <event_description>", "Create a new betting event"),
                    ("sportsbet <hours> <option1> <option2> <description>", "Create a sports bet"),
                    ("placebet <bet_id> <choice> <amount>", "Place a bet on an event"),
                    ("activebets", "View all active betting events"),
                    ("pastbets [limit]", "View past resolved betting events"),
                    ("mybet <bet_id>", "View your bet on an event"),
                    ("cancelbet <bet_id>", "Cancel your bet and get a refund")
                ]
            elif cat == "items":
                commands = [
                    ("shop [category]", "Browse the item shop or specific category"),
                    ("buy <item_id>", "Buy an item from the shop"),
                    ("inventory", "View your inventory"),
                    ("use <item_id>", "Use a consumable item from your inventory"),
                    ("gift <item_id> <quantity> <@user>", "Gift an item to another user")
                ]
            elif cat == "events":
                commands = [
                    ("events", "View current active economic events"),
                    ("event_info <event_id>", "Get details about a specific economic event")
                ]

            # Add commands to embed
            for cmd, desc in commands:
                embed.add_field(
                    name=f"{prefix}{cmd}",
                    value=desc,
                    inline=False
                )
        else:
            embed.title = "Unknown Category"
            embed.description = f"Category '{category}' not found. Use `{prefix}help` to see available categories."

    await ctx.send(embed=embed)

# Simple ping command
@bot.command(name="ping")
async def ping(ctx):
    """Check the bot's latency."""
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    embed.set_footer(text="Discord Economy Bot")
    await ctx.send(embed=embed)

@bot.tree.command(name="ping", description="Check the bot's response time")
async def ping_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    embed.set_footer(text="Discord Economy Bot")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Bot info command
@bot.command(name="info")
async def info(ctx):
    """Display information about the bot."""
    embed = discord.Embed(
        title="Discord Economy Bot",
        description="A Discord economy bot with company creation, money management, bank system, and role-based timeout features",
        color=discord.Color.blue()
    )

    embed.add_field(name="Version", value="1.0.0", inline=True)
    embed.add_field(name="Prefix", value=bot.command_prefix, inline=True)
    embed.add_field(name="Server Count", value=len(bot.guilds), inline=True)

    features = """
• Economy system with wallet and bank
• Daily rewards of $100 for all users
• Company creation and management
• AI-generated quests for earning money
• Role-based timeout system
• Item shop and inventory system
• Dynamic economic events
    """
    embed.add_field(name="Features", value=features, inline=False)
    embed.set_footer(text="Made with ❤️ for Discord")

    await ctx.send(embed=embed)

@bot.tree.command(name="info", description="Display information about the bot")
async def info_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Discord Economy Bot",
        description="A Discord economy bot with company creation, money management, bank system, and role-based timeout features",
        color=discord.Color.blue()
    )

    embed.add_field(name="Version", value="1.0.0", inline=True)
    embed.add_field(name="Prefix", value=bot.command_prefix, inline=True)
    embed.add_field(name="Server Count", value=len(bot.guilds), inline=True)

    features = """
• Economy system with wallet and bank
• Daily rewards of $100 for all users
• Company creation and management
• AI-generated quests for earning money
• Role-based timeout system
• Item shop and inventory system
• Dynamic economic events
    """
    embed.add_field(name="Features", value=features, inline=False)
    embed.set_footer(text="Made with ❤️ for Discord")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Admin commands
@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_commands(ctx):
    """Manually sync slash commands (admin only)."""
    try:
        logging.info(f"Admin {ctx.author.name} manually syncing slash commands")

        embed = discord.Embed(
            title="Syncing Commands",
            description="🔄 Starting command sync...",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Discord Economy Bot")
        message = await ctx.send(embed=embed)

        # First sync individual cogs
        for cog_name in bot.cogs:
            cog = bot.get_cog(cog_name)
            if hasattr(cog, 'sync_slash_commands'):
                try:
                    await cog.sync_slash_commands()
                    embed.add_field(name=f"✅ {cog_name}", value="Successfully synced", inline=False)
                    await message.edit(embed=embed)
                except Exception as e:
                    embed.add_field(name=f"❌ {cog_name}", value=f"Error: {e}", inline=False)
                    await message.edit(embed=embed)

        # Then sync global command tree
        bot.tree.clear_commands(guild=None)
        synced = await bot.tree.sync()

        embed.description = f"✅ Successfully synced {len(synced)} slash commands!"
        await message.edit(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Sync Error",
            description=f"❌ Error syncing slash commands: {e}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Discord Economy Bot")
        await ctx.send(embed=embed)

@bot.tree.command(name="admin_sync", description="Manually sync slash commands (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def sync_commands_slash(interaction: discord.Interaction):
    try:
        logging.info(f"Admin {interaction.user.name} manually syncing slash commands")

        embed = discord.Embed(
            title="Syncing Commands",
            description="🔄 Starting command sync...",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Discord Economy Bot")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # First sync individual cogs
        for cog_name in bot.cogs:
            cog = bot.get_cog(cog_name)
            if hasattr(cog, 'sync_slash_commands'):
                try:
                    await cog.sync_slash_commands()
                    embed.add_field(name=f"✅ {cog_name}", value="Successfully synced", inline=False)
                    await interaction.edit_original_response(embed=embed)
                except Exception as e:
                    embed.add_field(name=f"❌ {cog_name}", value=f"Error: {e}", inline=False)
                    await interaction.edit_original_response(embed=embed)

        # Then sync global command tree
        bot.tree.clear_commands(guild=None)
        synced = await bot.tree.sync()

        embed.description = f"✅ Successfully synced {len(synced)} slash commands!"
        await interaction.edit_original_response(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Sync Error",
            description=f"❌ Error syncing slash commands: {e}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Discord Economy Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

# Error handlers for permission checks
@sync_commands.error
async def sync_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="Permission Error",
            description="❌ You need administrator permissions to use this command!",
            color=discord.Color.red()
        )
        embed.set_footer(text="Discord Economy Bot")
        await ctx.send(embed=embed)
    else:
        logging.error(f"Sync command error: {error}")
        embed = discord.Embed(
            title="Error",
            description=f"❌ An error occurred: {error}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Discord Economy Bot")
        await ctx.send(embed=embed)

@sync_commands_slash.error
async def sync_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="Permission Error",
            description="❌ You need administrator permissions to use this command!",
            color=discord.Color.red()
        )
        embed.set_footer(text="Discord Economy Bot")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logging.error(f"Sync slash command error: {error}")
        embed = discord.Embed(
            title="Error",
            description=f"❌ An error occurred: {error}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Discord Economy Bot")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
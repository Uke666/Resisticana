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
    logging.info(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # Load cogs (extensions)
    await load_extensions()
    
    # Start daily reward loop
    bot.loop.create_task(daily_reward_loop())
    
    # Sync slash commands with Discord
    try:
        logging.info("Syncing slash commands...")
        await bot.tree.sync()
        logging.info("Slash commands synced successfully!")
    except Exception as e:
        logging.error(f"Failed to sync slash commands: {e}")
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help or /help"))
    
    logging.info("Bot is ready!")

async def load_extensions():
    """Load all cog extensions."""
    for extension in ['cogs.economy', 'cogs.company', 'cogs.moderation']:
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
        embed.add_field(
            name="🏦 Economy",
            value=f"`{prefix}help economy` - Money, bank, and daily rewards",
            inline=False
        )
        embed.add_field(
            name="🏢 Company",
            value=f"`{prefix}help company` - Company creation and management",
            inline=False
        )
        embed.add_field(
            name="🛡️ Moderation",
            value=f"`{prefix}help moderation` - Role-based timeout commands",
            inline=False
        )
        embed.add_field(
            name="📊 General",
            value=f"`{prefix}help general` - General utility commands",
            inline=False
        )
        
    # Economy commands
    elif category.lower() == "economy":
        embed.title = "Economy Commands"
        embed.description = "Commands for managing your money and earning rewards."
        
        embed.add_field(name=f"{prefix}balance", value="Check your current balance", inline=False)
        embed.add_field(name=f"{prefix}daily", value="Claim your daily reward of $100", inline=False)
        embed.add_field(name=f"{prefix}deposit <amount>", value="Deposit money to your bank", inline=False)
        embed.add_field(name=f"{prefix}withdraw <amount>", value="Withdraw money from your bank", inline=False)
        embed.add_field(name=f"{prefix}transfer <@user> <amount>", value="Send money to another user", inline=False)
        embed.add_field(name=f"{prefix}quest", value="Get a random quest to earn money", inline=False)
        embed.add_field(name=f"{prefix}rob <@user>", value="Attempt to rob another user (requires 5+ people)", inline=False)
        embed.add_field(name=f"{prefix}leaderboard", value="Display the richest users on the server", inline=False)
        
    # Company commands
    elif category.lower() == "company":
        embed.title = "Company Commands"
        embed.description = "Commands for managing companies and employees."
        
        embed.add_field(name=f"{prefix}createcompany <name>", value="Create a new company (requires higher role)", inline=False)
        embed.add_field(name=f"{prefix}company [name]", value="Display info about your company or another company", inline=False)
        embed.add_field(name=f"{prefix}invite <@user>", value="Invite a user to your company", inline=False)
        embed.add_field(name=f"{prefix}leave", value="Leave your current company", inline=False)
        embed.add_field(name=f"{prefix}kick <@user>", value="Kick a member from your company (owner only)", inline=False)
        embed.add_field(name=f"{prefix}disband", value="Disband your company as the owner", inline=False)
        embed.add_field(name=f"{prefix}companies", value="List all companies on the server", inline=False)
        
    # Moderation commands
    elif category.lower() == "moderation":
        embed.title = "Moderation Commands"
        embed.description = "Commands for moderating users with timeouts."
        
        embed.add_field(name=f"{prefix}timeout <@user>", value="Timeout a user based on your role permissions", inline=False)
        embed.add_field(name=f"{prefix}timeout_cost", value="Check the cost of using the timeout command", inline=False)
        embed.add_field(name=f"{prefix}timeout_limit", value="Check your timeout duration limit based on your roles", inline=False)
        embed.add_field(name=f"{prefix}timeout_history [@user]", value="View timeout history for yourself or another user", inline=False)
        
    # General commands
    elif category.lower() == "general":
        embed.title = "General Commands"
        embed.description = "General utility commands."
        
        embed.add_field(name=f"{prefix}help [category]", value="Display this help menu", inline=False)
        embed.add_field(name=f"{prefix}ping", value="Check the bot's response time", inline=False)
        embed.add_field(name=f"{prefix}info", value="Display information about the bot", inline=False)
        
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
    app_commands.Choice(name="General", value="general")
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
        embed.add_field(
            name="🏦 Economy",
            value=f"`/help economy` - Money, bank, and daily rewards",
            inline=False
        )
        embed.add_field(
            name="🏢 Company",
            value=f"`/help company` - Company creation and management",
            inline=False
        )
        embed.add_field(
            name="🛡️ Moderation",
            value=f"`/help moderation` - Role-based timeout commands",
            inline=False
        )
        embed.add_field(
            name="📊 General",
            value=f"`/help general` - General utility commands",
            inline=False
        )
        
    # Economy commands
    elif category.lower() == "economy":
        embed.title = "Economy Commands"
        embed.description = "Commands for managing your money and earning rewards."
        
        embed.add_field(name="/balance", value="Check your current balance", inline=False)
        embed.add_field(name="/daily", value="Claim your daily reward of $100", inline=False)
        embed.add_field(name="/deposit amount:<amount>", value="Deposit money to your bank", inline=False)
        embed.add_field(name="/withdraw amount:<amount>", value="Withdraw money from your bank", inline=False)
        embed.add_field(name="/transfer user:<@user> amount:<amount>", value="Send money to another user", inline=False)
        embed.add_field(name="/quest", value="Get a random quest to earn money", inline=False)
        embed.add_field(name="/rob user:<@user>", value="Attempt to rob another user (requires 5+ people)", inline=False)
        embed.add_field(name="/leaderboard", value="Display the richest users on the server", inline=False)
        
    # Company commands
    elif category.lower() == "company":
        embed.title = "Company Commands"
        embed.description = "Commands for managing companies and employees."
        
        embed.add_field(name="/createcompany name:<name>", value="Create a new company (requires higher role)", inline=False)
        embed.add_field(name="/company [name]", value="Display info about your company or another company", inline=False)
        embed.add_field(name="/invite user:<@user>", value="Invite a user to your company", inline=False)
        embed.add_field(name="/leave", value="Leave your current company", inline=False)
        embed.add_field(name="/kick user:<@user>", value="Kick a member from your company (owner only)", inline=False)
        embed.add_field(name="/disband", value="Disband your company as the owner", inline=False)
        embed.add_field(name="/companies", value="List all companies on the server", inline=False)
        
    # Moderation commands
    elif category.lower() == "moderation":
        embed.title = "Moderation Commands"
        embed.description = "Commands for moderating users with timeouts."
        
        embed.add_field(name="/timeout user:<@user>", value="Timeout a user based on your role permissions", inline=False)
        embed.add_field(name="/timeout_cost", value="Check the cost of using the timeout command", inline=False)
        embed.add_field(name="/timeout_limit", value="Check your timeout duration limit based on your roles", inline=False)
        embed.add_field(name="/timeout_history [user:<@user>]", value="View timeout history for yourself or another user", inline=False)
        
    # General commands
    elif category.lower() == "general":
        embed.title = "General Commands"
        embed.description = "General utility commands."
        
        embed.add_field(name="/help [category]", value="Display this help menu", inline=False)
        embed.add_field(name="/ping", value="Check the bot's response time", inline=False)
        embed.add_field(name="/info", value="Display information about the bot", inline=False)
        
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
        await bot.tree.sync()
        await ctx.send("✅ Slash commands synced globally!")
    except Exception as e:
        logging.error(f"Manual sync error: {e}")
        await ctx.send(f"❌ Error syncing slash commands: {e}")

@bot.tree.command(name="admin_sync", description="Manually sync slash commands (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def sync_commands_slash(interaction: discord.Interaction):
    """Slash command for manually syncing commands."""
    try:
        logging.info(f"Admin {interaction.user.name} manually syncing slash commands")
        await bot.tree.sync()
        await interaction.response.send_message("✅ Slash commands synced globally!", ephemeral=True)
    except Exception as e:
        logging.error(f"Manual sync error: {e}")
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
    bot.run(token)

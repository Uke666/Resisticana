import os
import discord
from discord.ext import commands
import asyncio
import logging
import json
import datetime
from utils.database import Database

# Initialize bot with all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

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
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="!help for commands"))
    
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

def run_bot(token):
    """Run the bot with the given token."""
    bot.run(token)

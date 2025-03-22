import discord
from discord.ext import commands
from discord import app_commands
import logging

class BaseCog(commands.Cog):
    """Base cog class with helper methods for both prefix and slash commands."""
    
    def __init__(self, bot):
        self.bot = bot
        
    async def sync_slash_commands(self):
        """Sync slash commands for the current cog."""
        try:
            # Sync for the current guild if available, otherwise globally
            if hasattr(self, 'guild') and self.guild:
                await self.bot.tree.sync(guild=self.guild)
                logging.info(f"Synced slash commands for {self.__class__.__name__} in guild {self.guild.name}")
            else:
                await self.bot.tree.sync()
                logging.info(f"Synced slash commands globally for {self.__class__.__name__}")
        except Exception as e:
            logging.error(f"Failed to sync slash commands for {self.__class__.__name__}: {e}")
    
    def create_embed(self, title, description=None, color=discord.Color.blue()):
        """Create a standard embed with consistent styling."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text="Discord Economy Bot")
        return embed
    
    def success_embed(self, message):
        """Create a success embed."""
        return self.create_embed("Success", message, discord.Color.green())
    
    def error_embed(self, message):
        """Create an error embed."""
        return self.create_embed("Error", message, discord.Color.red())
    
    def info_embed(self, title, message):
        """Create an info embed."""
        return self.create_embed(title, message, discord.Color.blue())
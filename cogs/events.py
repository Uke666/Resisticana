import asyncio
import discord
from discord.ext import commands, tasks
import random
import json
import os
from datetime import datetime, timedelta

from cogs.base_cog import BaseCog
from utils.economic_events import EconomicEventManager

# Initialize the economic event manager
event_manager = EconomicEventManager()

class EventsCog(BaseCog):
    """Cog for handling economic events."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.event_manager = event_manager
        
        # Start the event checking task
        self.event_check_loop.start()
        
    def cog_unload(self):
        """Called when the cog is unloaded."""
        self.event_check_loop.cancel()
    
    @tasks.loop(hours=4)
    async def event_check_loop(self):
        """Check for random events and potentially generate a new one."""
        try:
            # 10% chance to generate a new event every 4 hours, max 3 active events
            new_event = self.event_manager.generate_random_events(chance=0.1, max_events=3)
            
            if new_event:
                # If new event was generated, announce it to all servers
                for guild in self.bot.guilds:
                    # Find a suitable channel for announcements
                    channel = discord.utils.get(guild.text_channels, name='economy') or \
                             discord.utils.get(guild.text_channels, name='announcements') or \
                             discord.utils.get(guild.text_channels, name='general') or \
                             next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
                    
                    if channel:
                        # Create announcement embed
                        embed = self.create_event_embed(new_event)
                        await channel.send("**ECONOMIC EVENT**", embed=embed)
        except Exception as e:
            print(f"Error in event check loop: {e}")
    
    @event_check_loop.before_loop
    async def before_event_check(self):
        """Wait for the bot to be ready before starting the loop."""
        await self.bot.wait_until_ready()
    
    def create_event_embed(self, event):
        """Create a Discord embed for an economic event."""
        # Choose color based on event impact
        if event['impact'] == 'positive':
            color = discord.Color.green()
        elif event['impact'] == 'negative':
            color = discord.Color.red()
        else:
            color = discord.Color.blue()
        
        # Create embed
        embed = discord.Embed(
            title=f"Economic Event: {event['title']}",
            description=event['description'],
            color=color,
            timestamp=datetime.fromisoformat(event['start_time'])
        )
        
        # Add fields
        embed.add_field(name="Impact", value=event['impact'].capitalize(), inline=True)
        embed.add_field(name="Multiplier", value=f"{event['multiplier']}x", inline=True)
        
        # Calculate and add duration field
        start_time = datetime.fromisoformat(event['start_time'])
        end_time = datetime.fromisoformat(event['end_time'])
        duration = end_time - start_time
        
        if duration.days > 0:
            duration_str = f"{duration.days}d {duration.seconds // 3600}h"
        else:
            duration_str = f"{duration.seconds // 3600}h {(duration.seconds // 60) % 60}m"
        
        embed.add_field(name="Duration", value=duration_str, inline=True)
        
        # Add time remaining in footer
        embed.set_footer(text=f"Expires: {end_time.strftime('%Y-%m-%d %H:%M UTC')}")
        
        return embed
    
    @commands.group(name="events", invoke_without_command=True)
    async def events_cmd(self, ctx):
        """Display current economic events."""
        active_events = self.event_manager.get_active_events()
        
        if not active_events:
            await ctx.send("There are no active economic events at the moment.")
            return
        
        for event in active_events:
            embed = self.create_event_embed(event)
            await ctx.send(embed=embed)
    
    @events_cmd.command(name="list")
    async def events_list(self, ctx):
        """List all active economic events."""
        await self.events_cmd(ctx)
    
    @events_cmd.command(name="multiplier")
    async def events_multiplier(self, ctx):
        """Check current economic multiplier."""
        multiplier = self.event_manager.get_current_multiplier()
        
        embed = self.create_embed(
            title="Current Economic Multiplier",
            description=f"The current economy multiplier is **{multiplier:.2f}x**.",
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)
    
    @events_cmd.command(name="generate")
    @commands.has_permissions(administrator=True)
    async def events_generate(self, ctx, event_type=None):
        """Generate a new economic event (Admin only)."""
        # Validate event type
        if event_type and event_type not in ['positive', 'negative', 'neutral']:
            await ctx.send("Invalid event type. Choose from 'positive', 'negative', or 'neutral'.")
            return
        
        # Generate event
        try:
            new_event = self.event_manager.generate_event(event_type)
            embed = self.create_event_embed(new_event)
            await ctx.send("Generated new economic event:", embed=embed)
        except Exception as e:
            await ctx.send(f"Error generating event: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Apply economic event multipliers to message rewards, if applicable."""
        # Don't process messages from the bot itself
        if message.author.bot:
            return
        
        # Check if there's a random reward for the message (1% chance)
        if random.random() < 0.01:
            # Get the current multiplier
            multiplier = self.event_manager.get_current_multiplier()
            
            # Base reward amount
            base_reward = random.randint(1, 10)
            
            # Apply multiplier
            reward = round(base_reward * multiplier)
            
            if reward > 0:
                # Try to get the member and update their wallet
                # This would integrate with your economy system
                try:
                    # Placeholder for your economy logic
                    # For example: economy_cog.add_coins(message.author.id, message.guild.id, reward)
                    
                    # Send a message about the reward
                    await message.channel.send(
                        f"{message.author.mention} received {reward} coins for being active!"
                    )
                except Exception as e:
                    print(f"Error giving message reward: {e}")

def setup(bot):
    """Add the Events cog to the bot."""
    bot.add_cog(EventsCog(bot))
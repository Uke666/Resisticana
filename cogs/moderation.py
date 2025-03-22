import discord
from discord.ext import commands
import asyncio
import datetime
from utils.database import Database

class Moderation(commands.Cog):
    """Cog for handling moderation commands, including the timeout feature."""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        
        # Role IDs that cannot be timed out
        self.protected_role_ids = [
            1352694494843240448,  # Owner
            1352694494813749308,  # Admin
            1352694494813749307,  # Moderator/staff
        ]
        
        # Role timeout permissions (role_id: seconds)
        self.timeout_permissions = {
            1352694494797234234: 10,    # level 5 - 10 seconds
            1352694494797234235: 30,    # level 10 - 30 seconds
            1352694494797234236: 60,    # level 20 - 60 seconds
            1352694494797234237: 120,   # level 35 - 2 minutes
            1352694494813749299: 300,   # level 50 - 5 minutes
        }
        
    @commands.command(name="timeout")
    async def timeout(self, ctx, member: discord.Member):
        """Timeout a user based on your role permissions."""
        user_id = ctx.author.id
        target_id = member.id
        
        # Check if user is trying to timeout themselves
        if user_id == target_id:
            await ctx.send("You can't timeout yourself!")
            return
            
        # Check if target has a protected role
        for role in member.roles:
            if role.id in self.protected_role_ids:
                await ctx.send(f"You cannot timeout users with the {role.name} role!")
                return
                
        # Check if user has permission to timeout
        timeout_duration = 0
        for role in ctx.author.roles:
            if role.id in self.timeout_permissions:
                timeout_duration = max(timeout_duration, self.timeout_permissions[role.id])
                
        if timeout_duration == 0:
            await ctx.send("You don't have permission to timeout users!")
            return
            
        # Check if user has enough money
        user_data = self.db.get_or_create_user(user_id)
        TIMEOUT_COST = 50  # Cost to timeout someone
        
        if user_data["wallet"] < TIMEOUT_COST:
            await ctx.send(f"You need ${TIMEOUT_COST} in your wallet to timeout someone!")
            return
            
        # Deduct money
        self.db.remove_money(user_id, TIMEOUT_COST)
        
        # Apply timeout
        end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=timeout_duration)
        try:
            await member.timeout(end_time, reason=f"Timed out by {ctx.author.display_name}")
            
            # Notify users
            await ctx.send(f"{member.mention} has been timed out for {timeout_duration} seconds by {ctx.author.mention}!")
            
            # Add timeout log
            self.db.add_timeout_log(user_id, target_id, timeout_duration)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to timeout this user!")
            # Refund the money
            self.db.add_money(user_id, TIMEOUT_COST)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            # Refund the money
            self.db.add_money(user_id, TIMEOUT_COST)
            
    @commands.command(name="timeoutcost")
    async def timeout_cost(self, ctx):
        """Check the cost of using the timeout command."""
        await ctx.send("It costs $50 to timeout someone!")
        
    @commands.command(name="timeoutlimit")
    async def timeout_limit(self, ctx):
        """Check your timeout duration limit based on your roles."""
        user_id = ctx.author.id
        
        # Check timeout duration based on roles
        timeout_duration = 0
        highest_role = None
        
        for role in ctx.author.roles:
            if role.id in self.timeout_permissions:
                if self.timeout_permissions[role.id] > timeout_duration:
                    timeout_duration = self.timeout_permissions[role.id]
                    highest_role = role
                    
        if timeout_duration > 0:
            # Format duration for display
            if timeout_duration < 60:
                duration_text = f"{timeout_duration} seconds"
            else:
                minutes = timeout_duration // 60
                duration_text = f"{minutes} minute{'s' if minutes > 1 else ''}"
                
            await ctx.send(f"With your role {highest_role.name}, you can timeout users for {duration_text}!")
        else:
            await ctx.send("You don't have any roles that allow you to timeout users!")
            
    @commands.command(name="timeouthistory")
    async def timeout_history(self, ctx, member: discord.Member = None):
        """View timeout history for yourself or another user."""
        target_id = member.id if member else ctx.author.id
        target_name = member.display_name if member else ctx.author.display_name
        
        # Get timeout history
        timeout_logs = self.db.get_timeout_logs(target_id)
        
        if not timeout_logs:
            await ctx.send(f"{target_name} has no timeout history!")
            return
            
        embed = discord.Embed(
            title=f"Timeout History for {target_name}",
            color=discord.Color.orange()
        )
        
        for log in timeout_logs[:10]:  # Show only the last 10 timeouts
            moderator = ctx.guild.get_member(log["moderator_id"])
            moderator_name = moderator.display_name if moderator else f"User {log['moderator_id']}"
            
            embed.add_field(
                name=f"{log['timestamp'].strftime('%Y-%m-%d %H:%M')}",
                value=f"By: {moderator_name}\nDuration: {log['duration']} seconds",
                inline=False
            )
            
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))

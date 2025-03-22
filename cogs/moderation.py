import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
from utils.database import Database
from cogs.base_cog import BaseCog

class Moderation(BaseCog):
    """Cog for handling moderation commands, including the timeout feature."""
    
    def __init__(self, bot):
        super().__init__(bot)
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
                    
        if timeout_duration > 0 and highest_role is not None:
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
        if member is None:
            member = ctx.author
            
        target_id = member.id
        target_name = member.display_name
        
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

# Slash command versions
    @app_commands.command(name="timeout", description="Timeout a user based on your role permissions")
    @app_commands.describe(user="The user to timeout")
    async def timeout_slash(self, interaction: discord.Interaction, user: discord.Member):
        """Slash command for timing out users."""
        user_id = interaction.user.id
        target_id = user.id
        
        # Check if user is trying to timeout themselves
        if user_id == target_id:
            await interaction.response.send_message("You can't timeout yourself!", ephemeral=True)
            return
            
        # Check if target has a protected role
        for role in user.roles:
            if role.id in self.protected_role_ids:
                await interaction.response.send_message(
                    f"You cannot timeout users with the {role.name} role!",
                    ephemeral=True
                )
                return
                
        # Check if user has permission to timeout
        timeout_duration = 0
        for role in interaction.user.roles:
            if role.id in self.timeout_permissions:
                timeout_duration = max(timeout_duration, self.timeout_permissions[role.id])
                
        if timeout_duration == 0:
            await interaction.response.send_message(
                "You don't have permission to timeout users!", 
                ephemeral=True
            )
            return
            
        # Check if user has enough money
        user_data = self.db.get_or_create_user(user_id)
        TIMEOUT_COST = 50  # Cost to timeout someone
        
        if user_data["wallet"] < TIMEOUT_COST:
            await interaction.response.send_message(
                f"You need ${TIMEOUT_COST} in your wallet to timeout someone!",
                ephemeral=True
            )
            return
            
        # Deduct money
        self.db.remove_money(user_id, TIMEOUT_COST)
        
        # Apply timeout
        end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=timeout_duration)
        try:
            await user.timeout(end_time, reason=f"Timed out by {interaction.user.display_name}")
            
            # Notify users
            await interaction.response.send_message(
                f"{user.mention} has been timed out for {timeout_duration} seconds by {interaction.user.mention}!"
            )
            
            # Add timeout log
            self.db.add_timeout_log(user_id, target_id, timeout_duration)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to timeout this user!",
                ephemeral=True
            )
            # Refund the money
            self.db.add_money(user_id, TIMEOUT_COST)
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            # Refund the money
            self.db.add_money(user_id, TIMEOUT_COST)
    
    @app_commands.command(name="timeout_cost", description="Check the cost of using the timeout command")
    async def timeout_cost_slash(self, interaction: discord.Interaction):
        """Slash command for checking timeout cost."""
        await interaction.response.send_message("It costs $50 to timeout someone!", ephemeral=True)
    
    @app_commands.command(name="timeout_limit", description="Check your timeout duration limit based on your roles")
    async def timeout_limit_slash(self, interaction: discord.Interaction):
        """Slash command for checking timeout limits."""
        # Check timeout duration based on roles
        timeout_duration = 0
        highest_role = None
        
        for role in interaction.user.roles:
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
                
            await interaction.response.send_message(
                f"With your role {highest_role.name}, you can timeout users for {duration_text}!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "You don't have any roles that allow you to timeout users!",
                ephemeral=True
            )
    
    @app_commands.command(name="timeout_history", description="View timeout history for yourself or another user")
    @app_commands.describe(user="The user to check timeout history for (leave empty for yourself)")
    async def timeout_history_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        """Slash command for viewing timeout history."""
        if user is None:
            user = interaction.user
            
        target_id = user.id
        target_name = user.display_name
        
        # Get timeout history
        timeout_logs = self.db.get_timeout_logs(target_id)
        
        if not timeout_logs:
            await interaction.response.send_message(
                f"{target_name} has no timeout history!",
                ephemeral=True
            )
            return
            
        embed = discord.Embed(
            title=f"Timeout History for {target_name}",
            color=discord.Color.orange()
        )
        
        for log in timeout_logs[:10]:  # Show only the last 10 timeouts
            moderator = interaction.guild.get_member(log["moderator_id"])
            moderator_name = moderator.display_name if moderator else f"User {log['moderator_id']}"
            
            embed.add_field(
                name=f"{log['timestamp'].strftime('%Y-%m-%d %H:%M')}",
                value=f"By: {moderator_name}\nDuration: {log['duration']} seconds",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))

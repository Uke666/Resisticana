import discord
from discord.ext import commands
from discord import app_commands, utils
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
        
    @commands.command(name="bomb")
    async def bomb(self, ctx, member: discord.Member = None):
        """Bomb a user (timeout) based on your role permissions."""
        if member is None:
            await ctx.send("You need to specify a user to bomb! Usage: !bomb @username ....fkin dumbass nig...")
            return
        user_id = ctx.author.id
        target_id = member.id
        
        # Check if user is trying to bomb themselves
        if user_id == target_id:
            await ctx.send("yoyoyoyoyo.. this mf trying to bomb himself lmfao")
            return
            
        # Check if target has a protected role
        for role in member.roles:
            if role.id in self.protected_role_ids:
                await ctx.send(f"Nigga wtf You cannot bomb users with the {role.name} role!")
                return
                
        # Check if user has permission to bomb
        timeout_duration = 0
        for role in ctx.author.roles:
            if role.id in self.timeout_permissions:
                timeout_duration = max(timeout_duration, self.timeout_permissions[role.id])
                
        if timeout_duration == 0:
            await ctx.send("You don't have permission to bomb users!")
            return
            
        # Check if user has enough money
        user_data = self.db.get_or_create_user(user_id)
        BOMB_COST = 50  # Cost to bomb someone
        
        if user_data["wallet"] < BOMB_COST:
            await ctx.send(f"You need ${BOMB_COST} in your wallet to bomb someone you fkin moronenic poor lil bitch!")
            return
            
        # Deduct money
        self.db.remove_money(user_id, BOMB_COST)
        
        # Apply timeout with timezone-aware datetime
        end_time = utils.utcnow() + datetime.timedelta(seconds=timeout_duration)
        try:
            await member.timeout(end_time, reason=f"Bombed by {ctx.author.display_name}")
            
            # Create embed with bomb GIF
            embed = discord.Embed(
                title="💣 BOMB DEPLOYED! 💣",
                description=f"{member.mention} has been bombed for {timeout_duration} seconds by {ctx.author.mention}!",
                color=discord.Color.red()
            )
            embed.set_image(url="https://media1.tenor.com/m/tGw9QVHWzToAAAAd/pvz-gta.gif")
            embed.set_footer(text="The user has been temporarily muted")
            
            # Notify users with the bomb GIF
            await ctx.send(embed=embed)
            
            # Add timeout log
            self.db.add_timeout_log(user_id, target_id, timeout_duration)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to bomb this user!")
            # Refund the money
            self.db.add_money(user_id, BOMB_COST)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            # Refund the money
            self.db.add_money(user_id, BOMB_COST)
            
    @commands.command(name="bombcost")
    async def bomb_cost(self, ctx):
        """Check the cost of using the bomb command."""
        await ctx.send("It costs $50 to bomb someone!")
        
    @commands.command(name="bomblimit")
    async def bomb_limit(self, ctx):
        """Check your bomb duration limit based on your roles."""
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
                
            await ctx.send(f"With your role {highest_role.name}, you can bomb users for {duration_text}!")
        else:
            await ctx.send("You don't have any roles that allow you to bomb users!")
            
    @commands.command(name="bombhistory")
    async def bomb_history(self, ctx, member: discord.Member = None):
        """View bomb history for yourself or another user."""
        if member is None:
            member = ctx.author
            
        target_id = member.id
        target_name = member.display_name
        
        # Get timeout history
        timeout_logs = self.db.get_timeout_logs(target_id)
        
        if not timeout_logs:
            await ctx.send(f"{target_name} has no bomb history!")
            return
            
        embed = discord.Embed(
            title=f"💣 Bomb History for {target_name}",
            color=discord.Color.orange()
        )
        
        for log in timeout_logs[:10]:  # Show only the last 10 bombs
            moderator = ctx.guild.get_member(log["moderator_id"])
            moderator_name = moderator.display_name if moderator else f"User {log['moderator_id']}"
            
            embed.add_field(
                name=f"{log['timestamp'].strftime('%Y-%m-%d %H:%M')}",
                value=f"By: {moderator_name}\nDuration: {log['duration']} seconds",
                inline=False
            )
            
        await ctx.send(embed=embed)

# Slash command versions
    @app_commands.command(name="bomb", description="Bomb a user (timeout) based on your role permissions")
    @app_commands.describe(user="The user to bomb")
    async def bomb_slash(self, interaction: discord.Interaction, user: discord.Member):
        """Slash command for bombing users."""
        user_id = interaction.user.id
        target_id = user.id
        
        # Check if user is trying to bomb themselves
        if user_id == target_id:
            await interaction.response.send_message("You can't bomb yourself!", ephemeral=True)
            return
            
        # Check if target has a protected role
        for role in user.roles:
            if role.id in self.protected_role_ids:
                await interaction.response.send_message(
                    f"You cannot bomb users with the {role.name} role!",
                    ephemeral=True
                )
                return
                
        # Check if user has permission to bomb
        timeout_duration = 0
        for role in interaction.user.roles:
            if role.id in self.timeout_permissions:
                timeout_duration = max(timeout_duration, self.timeout_permissions[role.id])
                
        if timeout_duration == 0:
            await interaction.response.send_message(
                "You don't have permission to bomb users!", 
                ephemeral=True
            )
            return
            
        # Check if user has enough money
        user_data = self.db.get_or_create_user(user_id)
        BOMB_COST = 50  # Cost to bomb someone
        
        if user_data["wallet"] < BOMB_COST:
            await interaction.response.send_message(
                f"You need ${BOMB_COST} in your wallet to bomb someone!",
                ephemeral=True
            )
            return
            
        # Deduct money
        self.db.remove_money(user_id, BOMB_COST)
        
        # Apply timeout with timezone-aware datetime
        end_time = utils.utcnow() + datetime.timedelta(seconds=timeout_duration)
        try:
            await user.timeout(end_time, reason=f"Bombed by {interaction.user.display_name}")
            
            # Create embed with bomb GIF
            embed = discord.Embed(
                title="💣 BOMB DEPLOYED! 💣",
                description=f"{user.mention} has been bombed for {timeout_duration} seconds by {interaction.user.mention}!",
                color=discord.Color.red()
            )
            embed.set_image(url="https://media1.tenor.com/m/tGw9QVHWzToAAAAd/pvz-gta.gif")
            embed.set_footer(text="The user has been temporarily muted")
            
            # Send the bomb notification with GIF
            await interaction.response.send_message(embed=embed)
            
            # Add timeout log
            self.db.add_timeout_log(user_id, target_id, timeout_duration)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to bomb this user!",
                ephemeral=True
            )
            # Refund the money
            self.db.add_money(user_id, BOMB_COST)
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            # Refund the money
            self.db.add_money(user_id, BOMB_COST)
    
    @app_commands.command(name="bomb_cost", description="Check the cost of using the bomb command")
    async def bomb_cost_slash(self, interaction: discord.Interaction):
        """Slash command for checking bomb cost."""
        await interaction.response.send_message("It costs $50 to bomb someone!", ephemeral=True)
    
    @app_commands.command(name="bomb_limit", description="Check your bomb duration limit based on your roles")
    async def bomb_limit_slash(self, interaction: discord.Interaction):
        """Slash command for checking bomb limits."""
        # Check timeout duration based on roles
        timeout_duration = 0
        highest_role = None
        
        for role in interaction.user.roles:
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
                
            await interaction.response.send_message(
                f"With your role {highest_role.name}, you can bomb users for {duration_text}!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "You don't have any roles that allow you to bomb users!",
                ephemeral=True
            )
    
    @app_commands.command(name="bomb_history", description="View bomb history for yourself or another user")
    @app_commands.describe(user="The user to check bomb history for (leave empty for yourself)")
    async def bomb_history_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        """Slash command for viewing bomb history."""
        if user is None:
            user = interaction.user
            
        target_id = user.id
        target_name = user.display_name
        
        # Get timeout history
        timeout_logs = self.db.get_timeout_logs(target_id)
        
        if not timeout_logs:
            await interaction.response.send_message(
                f"{target_name} has no bomb history!",
                ephemeral=True
            )
            return
            
        embed = discord.Embed(
            title=f"💣 Bomb History for {target_name}",
            color=discord.Color.orange()
        )
        
        for log in timeout_logs[:10]:  # Show only the last 10 bombs
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

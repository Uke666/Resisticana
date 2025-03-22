import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
import logging
from utils.database import Database
from utils.quests import QuestGenerator
from cogs.base_cog import BaseCog

class Economy(BaseCog):
    """Cog for handling all economy-related commands and functions."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.db = Database()
        self.quest_generator = QuestGenerator()
        self.quest_cooldowns = {}
        self.rob_attempts = {}  # Track robbery attempts {target_id: [user_ids]}

    @commands.command(name="balance", aliases=["bal"])
    async def balance(self, ctx):
        """Check your current balance (wallet and bank)."""
        user_id = ctx.author.id
        user_data = self.db.get_or_create_user(user_id)
        
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Balance",
            color=discord.Color.green()
        )
        embed.add_field(name="Wallet", value=f"${user_data['wallet']}", inline=True)
        embed.add_field(name="Bank", value=f"${user_data['bank']}", inline=True)
        embed.add_field(name="Total", value=f"${user_data['wallet'] + user_data['bank']}", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="daily")
    async def daily(self, ctx):
        """Claim your daily reward of $100."""
        user_id = ctx.author.id
        
        # Check if daily reward is available
        result = self.db.claim_daily_reward(user_id)
        
        if result["success"]:
            embed = discord.Embed(
                title="Daily Reward",
                description=f"You've claimed your daily reward of $100!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Balance", value=f"${result['new_balance']}")
            await ctx.send(embed=embed)
        else:
            # Calculate time until next reward
            time_left = result["next_available"] - datetime.now()
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            embed = discord.Embed(
                title="Daily Reward",
                description=f"You've already claimed your daily reward!",
                color=discord.Color.red()
            )
            embed.add_field(name="Next Reward In", value=f"{hours}h {minutes}m {seconds}s")
            await ctx.send(embed=embed)

    @commands.command(name="deposit", aliases=["dep"])
    async def deposit(self, ctx, amount: str):
        """Deposit money from your wallet to your bank."""
        user_id = ctx.author.id
        
        # Handle "all" amount
        if amount.lower() == "all":
            user_data = self.db.get_or_create_user(user_id)
            amount_int = user_data["wallet"]
        else:
            try:
                amount_int = int(amount)
                if amount_int <= 0:
                    await ctx.send("Amount must be positive!")
                    return
            except ValueError:
                await ctx.send("Please enter a valid amount or 'all'!")
                return
        
        result = self.db.deposit(user_id, amount_int)
        
        if result["success"]:
            embed = discord.Embed(
                title="Deposit Successful",
                description=f"You've deposited ${amount_int} into your bank!",
                color=discord.Color.green()
            )
            embed.add_field(name="Wallet", value=f"${result['wallet']}", inline=True)
            embed.add_field(name="Bank", value=f"${result['bank']}", inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Error: {result['message']}")

    @commands.command(name="withdraw", aliases=["with"])
    async def withdraw(self, ctx, amount: str):
        """Withdraw money from your bank to your wallet."""
        user_id = ctx.author.id
        
        # Handle "all" amount
        if amount.lower() == "all":
            user_data = self.db.get_or_create_user(user_id)
            amount = user_data["bank"]
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    await ctx.send("Amount must be positive!")
                    return
            except ValueError:
                await ctx.send("Please enter a valid amount or 'all'!")
                return
        
        result = self.db.withdraw(user_id, amount)
        
        if result["success"]:
            embed = discord.Embed(
                title="Withdrawal Successful",
                description=f"You've withdrawn ${amount} from your bank!",
                color=discord.Color.green()
            )
            embed.add_field(name="Wallet", value=f"${result['wallet']}", inline=True)
            embed.add_field(name="Bank", value=f"${result['bank']}", inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Error: {result['message']}")

    @commands.command(name="transfer", aliases=["pay", "send"])
    async def transfer(self, ctx, recipient: discord.Member, amount: int):
        """Transfer money from your wallet to another user."""
        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return
            
        sender_id = ctx.author.id
        recipient_id = recipient.id
        
        if sender_id == recipient_id:
            await ctx.send("You can't transfer money to yourself!")
            return
        
        result = self.db.transfer(sender_id, recipient_id, amount)
        
        if result["success"]:
            embed = discord.Embed(
                title="Transfer Successful",
                description=f"You've transferred ${amount} to {recipient.display_name}!",
                color=discord.Color.green()
            )
            embed.add_field(name="Your Balance", value=f"${result['sender_wallet']}", inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Error: {result['message']}")

    @commands.command(name="quest")
    async def quest(self, ctx):
        """Get a random quest to earn money."""
        user_id = ctx.author.id
        
        # Check cooldown
        now = datetime.now()
        if user_id in self.quest_cooldowns and now < self.quest_cooldowns[user_id]:
            time_left = self.quest_cooldowns[user_id] - now
            minutes, seconds = divmod(time_left.seconds, 60)
            await ctx.send(f"You need to wait {minutes}m {seconds}s before getting another quest!")
            return
        
        # Generate a quest
        quest_data = await self.quest_generator.generate_quest(ctx.author.display_name)
        
        # Set cooldown (30 minutes)
        self.quest_cooldowns[user_id] = now + timedelta(minutes=30)
        
        # Create embed for quest
        embed = discord.Embed(
            title=f"Quest for {ctx.author.display_name}",
            description=quest_data["quest_description"],
            color=discord.Color.blue()
        )
        embed.add_field(name="Reward", value=f"${quest_data['reward']}", inline=False)
        embed.add_field(name="Time Limit", value=f"{quest_data['time_limit']} minutes", inline=False)
        
        # Send quest and wait for confirmation
        message = await ctx.send(embed=embed)
        
        # Add reactions for accepting or declining
        await message.add_reaction("✅")  # Accept
        await message.add_reaction("❌")  # Decline
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Quest accepted
                await ctx.send(f"Quest accepted! You have {quest_data['time_limit']} minutes to complete it.")
                
                # Wait for the time limit
                await asyncio.sleep(quest_data['time_limit'] * 60)
                
                # Roll for success (70% chance)
                if random.random() < 0.7:
                    # Success
                    self.db.add_money(user_id, quest_data['reward'])
                    await ctx.send(f"{ctx.author.mention}, you completed the quest and earned ${quest_data['reward']}!")
                else:
                    # Failure
                    await ctx.send(f"{ctx.author.mention}, you failed to complete the quest. Better luck next time!")
            else:
                # Quest declined
                await ctx.send("Quest declined. You can get another quest in 30 minutes.")
                
        except asyncio.TimeoutError:
            await ctx.send(f"{ctx.author.mention}, quest offer expired.")

    @commands.command(name="rob")
    async def rob(self, ctx, target: discord.Member):
        """Attempt to rob another user (requires 5+ people)."""
        user_id = ctx.author.id
        target_id = target.id
        
        # Can't rob yourself
        if user_id == target_id:
            await ctx.send("You can't rob yourself!")
            return
        
        # Check if target has already been robbed recently
        if target_id in self.rob_attempts and "last_robbed" in self.rob_attempts[target_id]:
            last_robbed = self.rob_attempts[target_id]["last_robbed"]
            if datetime.now() < last_robbed + timedelta(hours=1):
                await ctx.send(f"{target.display_name} has already been robbed recently. Try again later!")
                return
        
        # Initialize rob attempt for this target if it doesn't exist
        if target_id not in self.rob_attempts:
            self.rob_attempts[target_id] = {"users": []}
        
        # Check if this user already joined the rob attempt
        if user_id in self.rob_attempts[target_id]["users"]:
            await ctx.send("You're already part of this robbery attempt!")
            return
        
        # Add user to rob attempt
        self.rob_attempts[target_id]["users"].append(user_id)
        robbers_count = len(self.rob_attempts[target_id]["users"])
        
        if robbers_count < 5:
            # Not enough robbers yet
            await ctx.send(f"{ctx.author.display_name} wants to rob {target.display_name}! {5 - robbers_count} more people needed! Use !rob {target.display_name} to join.")
        else:
            # Enough robbers to attempt the robbery
            target_data = self.db.get_or_create_user(target_id)
            
            # Check if target has money in wallet
            if target_data["wallet"] <= 0:
                await ctx.send(f"{target.display_name} has no money in their wallet to rob!")
                self.rob_attempts.pop(target_id)
                return
            
            # Calculate amount to rob (10-25% of wallet)
            rob_percent = random.uniform(0.1, 0.25)
            rob_amount = int(target_data["wallet"] * rob_percent)
            
            # Ensure minimum rob amount
            rob_amount = max(rob_amount, 10)
            
            # Ensure rob amount doesn't exceed wallet
            rob_amount = min(rob_amount, target_data["wallet"])
            
            # Complete the robbery
            self.db.remove_money(target_id, rob_amount)
            
            # Split the money between robbers
            split_amount = rob_amount // len(self.rob_attempts[target_id]["users"])
            
            # Give each robber their cut
            robbers_mentions = []
            for robber_id in self.rob_attempts[target_id]["users"]:
                self.db.add_money(robber_id, split_amount)
                robber = ctx.guild.get_member(robber_id)
                if robber:
                    robbers_mentions.append(robber.mention)
            
            # Set the cooldown for robbing this target again
            self.rob_attempts[target_id] = {"last_robbed": datetime.now()}
            
            # Send success message
            robbers_list = " ".join(robbers_mentions)
            await ctx.send(f"Robbery successful! {robbers_list} robbed {target.mention} of ${rob_amount} and each got ${split_amount}!")

    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx):
        """Display the richest users on the server."""
        leaderboard_data = self.db.get_leaderboard()
        
        if not leaderboard_data:
            await ctx.send("No data available for the leaderboard yet!")
            return
        
        embed = discord.Embed(
            title="Economy Leaderboard",
            description="The richest users in the server",
            color=discord.Color.gold()
        )
        
        for i, entry in enumerate(leaderboard_data[:10], 1):
            user = ctx.guild.get_member(entry["user_id"])
            username = user.display_name if user else f"User {entry['user_id']}"
            
            # Calculate total wealth
            total = entry["wallet"] + entry["bank"]
            
            embed.add_field(
                name=f"{i}. {username}",
                value=f"Wallet: ${entry['wallet']} | Bank: ${entry['bank']} | Total: ${total}",
                inline=False
            )
        
        await ctx.send(embed=embed)

# Slash command equivalents
    @app_commands.command(name="balance", description="Check your current balance (wallet and bank)")
    async def balance_slash(self, interaction: discord.Interaction):
        """Slash command equivalent for checking balance."""
        user_id = interaction.user.id
        user_data = self.db.get_or_create_user(user_id)
        
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Balance",
            color=discord.Color.green()
        )
        embed.add_field(name="Wallet", value=f"${user_data['wallet']}", inline=True)
        embed.add_field(name="Bank", value=f"${user_data['bank']}", inline=True)
        embed.add_field(name="Total", value=f"${user_data['wallet'] + user_data['bank']}", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="daily", description="Claim your daily reward of $100")
    async def daily_slash(self, interaction: discord.Interaction):
        """Slash command equivalent for claiming daily reward."""
        user_id = interaction.user.id
        
        # Check if daily reward is available
        result = self.db.claim_daily_reward(user_id)
        
        if result["success"]:
            embed = discord.Embed(
                title="Daily Reward",
                description=f"You've claimed your daily reward of $100!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Balance", value=f"${result['new_balance']}")
            await interaction.response.send_message(embed=embed)
        else:
            # Calculate time until next reward
            time_left = result["next_available"] - datetime.now()
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            embed = discord.Embed(
                title="Daily Reward",
                description=f"You've already claimed your daily reward!",
                color=discord.Color.red()
            )
            embed.add_field(name="Next Reward In", value=f"{hours}h {minutes}m {seconds}s")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="leaderboard", description="Display the richest users on the server")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        """Slash command equivalent for viewing leaderboard."""
        leaderboard_data = self.db.get_leaderboard()
        
        if not leaderboard_data:
            await interaction.response.send_message("No data available for the leaderboard yet!")
            return
        
        embed = discord.Embed(
            title="Economy Leaderboard",
            description="The richest users in the server",
            color=discord.Color.gold()
        )
        
        for i, entry in enumerate(leaderboard_data[:10], 1):
            user = interaction.guild.get_member(entry["user_id"])
            username = user.display_name if user else f"User {entry['user_id']}"
            
            # Calculate total wealth
            total = entry["wallet"] + entry["bank"]
            
            embed.add_field(
                name=f"{i}. {username}",
                value=f"Wallet: ${entry['wallet']} | Bank: ${entry['bank']} | Total: ${total}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))

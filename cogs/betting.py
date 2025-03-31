
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
import aiohttp
from datetime import datetime, timedelta
from utils.database import Database
from cogs.base_cog import BaseCog
import openai
import logging

class Betting(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.db = Database()
        self.active_bets = {}
        self.bet_results = {}
        self.openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    @app_commands.command(name="createbet", description="Create a new betting event")
    @app_commands.describe(event_description="Description of the betting event")
    async def create_bet(self, interaction: discord.Interaction, event_description: str):
        """Create a new betting event."""
        creator_id = interaction.user.id

        # Analyze event using AI
        event_info = await self.analyze_event(event_description)
        if not event_info:
            await interaction.response.send_message("Could not analyze the event. Please be more specific!", ephemeral=True)
            return

        bet_id = len(self.active_bets)
        self.active_bets[bet_id] = {
            'creator_id': creator_id,
            'description': event_description,
            'options': event_info['options'],
            'participants': {},
            'status': 'open',
            'created_at': datetime.now(),
            'end_time': event_info['estimated_end_time'],
            'result': None
        }

        embed = discord.Embed(
            title="New Betting Event!",
            description=event_description,
            color=discord.Color.blue()
        )
        embed.add_field(name="Options", value="\n".join(event_info['options']), inline=False)
        embed.add_field(name="Bet ID", value=f"#{bet_id}", inline=True)
        embed.add_field(name="Created by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Estimated End", value=event_info['estimated_end_time'].strftime("%Y-%m-%d %H:%M UTC"), inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="placebet", description="Place a bet on an event")
    @app_commands.describe(
        bet_id="The ID of the bet",
        choice="Your betting choice",
        amount="Amount to bet"
    )
    async def place_bet(self, interaction: discord.Interaction, bet_id: int, choice: str, amount: int):
        if bet_id not in self.active_bets:
            await interaction.response.send_message("Bet not found!", ephemeral=True)
            return

        bet = self.active_bets[bet_id]
        if bet['status'] != 'open':
            await interaction.response.send_message("This bet is no longer accepting entries!", ephemeral=True)
            return

        if choice not in bet['options']:
            await interaction.response.send_message(f"Invalid choice! Options are: {', '.join(bet['options'])}", ephemeral=True)
            return

        user_id = interaction.user.id
        user_data = self.db.get_or_create_user(user_id)
        if user_data['wallet'] < amount:
            await interaction.response.send_message("You don't have enough money in your wallet!", ephemeral=True)
            return

        self.db.remove_money(user_id, amount)
        bet['participants'][user_id] = {
            'option': choice,
            'amount': amount,
            'placed_at': datetime.now()
        }

        await interaction.response.send_message(f"Bet placed! You bet ${amount} on {choice}")

    @app_commands.command(name="activebets", description="View all active betting events")
    async def view_active_bets(self, interaction: discord.Interaction):
        active_bets = {bid: bet for bid, bet in self.active_bets.items() if bet['status'] == 'open'}

        if not active_bets:
            await interaction.response.send_message("No active bets!", ephemeral=True)
            return

        embed = discord.Embed(
            title="Active Betting Events",
            color=discord.Color.blue()
        )

        for bid, bet in active_bets.items():
            embed.add_field(
                name=f"Bet #{bid}",
                value=f"Description: {bet['description']}\n"
                      f"Options: {', '.join(bet['options'])}\n"
                      f"Total Pot: ${sum(p['amount'] for p in bet['participants'].values())}\n"
                      f"Ends: {bet['end_time'].strftime('%Y-%m-%d %H:%M UTC')}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resolvebet", description="Resolve a bet and distribute winnings")
    @app_commands.describe(
        bet_id="The ID of the bet to resolve",
        winner="The winning option"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def resolve_bet(self, interaction: discord.Interaction, bet_id: int, winner: str):
        if bet_id not in self.active_bets:
            await interaction.response.send_message("Bet not found!", ephemeral=True)
            return

        bet = self.active_bets[bet_id]
        if bet['status'] != 'open':
            await interaction.response.send_message("This bet has already been resolved!", ephemeral=True)
            return

        if winner not in bet['options']:
            await interaction.response.send_message(f"Invalid winner! Options were: {', '.join(bet['options'])}", ephemeral=True)
            return

        total_pot = sum(p['amount'] for p in bet['participants'].values())
        winning_bets = {uid: data for uid, data in bet['participants'].items() if data['option'] == winner}
        winning_total = sum(data['amount'] for data in winning_bets.values())

        if winning_total > 0:
            for user_id, data in winning_bets.items():
                win_share = (data['amount'] / winning_total) * total_pot
                self.db.add_money(user_id, int(win_share))

        bet['status'] = 'closed'
        bet['result'] = winner
        bet['resolved_at'] = datetime.now()

        embed = discord.Embed(
            title="Bet Resolved!",
            description=bet['description'],
            color=discord.Color.green()
        )
        embed.add_field(name="Winner", value=winner, inline=False)
        embed.add_field(name="Total Pot", value=f"${total_pot}", inline=True)
        embed.add_field(name="Number of Winners", value=str(len(winning_bets)), inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mybet", description="View your active bet on an event")
    @app_commands.describe(bet_id="The ID of the bet")
    async def view_my_bet(self, interaction: discord.Interaction, bet_id: int):
        if bet_id not in self.active_bets:
            await interaction.response.send_message("Bet not found!", ephemeral=True)
            return

        bet = self.active_bets[bet_id]
        user_id = interaction.user.id

        if user_id not in bet['participants']:
            await interaction.response.send_message("You haven't placed a bet on this event!", ephemeral=True)
            return

        user_bet = bet['participants'][user_id]
        embed = discord.Embed(
            title="Your Bet Details",
            description=bet['description'],
            color=discord.Color.blue()
        )
        embed.add_field(name="Your Choice", value=user_bet['option'], inline=True)
        embed.add_field(name="Amount Bet", value=f"${user_bet['amount']}", inline=True)
        embed.add_field(name="Placed At", value=user_bet['placed_at'].strftime("%Y-%m-%d %H:%M UTC"), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cancelbet", description="Cancel your bet and get a refund (if bet is still open)")
    @app_commands.describe(bet_id="The ID of the bet to cancel")
    async def cancel_bet(self, interaction: discord.Interaction, bet_id: int):
        if bet_id not in self.active_bets:
            await interaction.response.send_message("Bet not found!", ephemeral=True)
            return

        bet = self.active_bets[bet_id]
        user_id = interaction.user.id

        if bet['status'] != 'open':
            await interaction.response.send_message("This bet is no longer open for cancellation!", ephemeral=True)
            return

        if user_id not in bet['participants']:
            await interaction.response.send_message("You haven't placed a bet on this event!", ephemeral=True)
            return

        # Refund the bet amount
        refund_amount = bet['participants'][user_id]['amount']
        self.db.add_money(user_id, refund_amount)
        del bet['participants'][user_id]

        await interaction.response.send_message(f"Your bet has been cancelled and ${refund_amount} has been refunded to your wallet.")

    async def analyze_event(self, description):
        """Analyze event description to generate smart betting options."""
        try:
            sports_keywords = {
                'cricket': ['win by runs', 'win by wickets', 'match tied'],
                'football': ['win by goals', 'draw', 'clean sheet'],
                'ipl': ['win by runs', 'win by wickets', 'super over'],
                'match': ['home win', 'away win', 'draw']
            }

            desc_lower = description.lower()
            options = []

            if 'ipl' in desc_lower:
                teams = []
                for team in ['mumbai', 'chennai', 'bangalore', 'kolkata', 'delhi', 'punjab', 'rajasthan', 'hyderabad']:
                    if team in desc_lower:
                        teams.append(team.title())

                if len(teams) >= 2:
                    options.extend([
                        f"{teams[0]} wins by 20+ runs",
                        f"{teams[0]} wins by <20 runs",
                        f"{teams[1]} wins by 20+ runs",
                        f"{teams[1]} wins by <20 runs",
                        "Match goes to Super Over"
                    ])

            if not options:
                for sport, outcomes in sports_keywords.items():
                    if sport in desc_lower:
                        options.extend(outcomes)
                        break

            if not options:
                if 'election' in desc_lower:
                    options = ['Candidate A wins', 'Candidate B wins', 'Too close to call']
                elif 'weather' in desc_lower:
                    options = ['Sunny', 'Rainy', 'Cloudy', 'Mixed conditions']
                elif 'game' in desc_lower:
                    options = ['Player 1 wins', 'Player 2 wins', 'Draw']

            if not options:
                options = ["Decisive Victory", "Close Win", "Draw/Tie", "No Result"]

            return {
                'options': options,
                'estimated_end_time': datetime.now() + timedelta(hours=24),
                'event_type': 'sports' if any(k in desc_lower for k in sports_keywords) else 'general',
                'description': description
            }

        except Exception as e:
            logging.error(f"Error in event analysis: {str(e)}")
            return None

async def setup(bot):
    await bot.add_cog(Betting(bot))

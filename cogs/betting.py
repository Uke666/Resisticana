
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

class Betting(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.db = Database()
        self.active_bets = {}
        self.bet_results = {}
        self.openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    @commands.command(name="createbet")
    async def create_bet(self, ctx, *, event_description: str):
        """Create a new betting event."""
        creator_id = ctx.author.id
        
        # Analyze event using AI
        event_info = await self.analyze_event(event_description)
        if not event_info:
            await ctx.send("Could not analyze the event. Please be more specific!")
            return
            
        bet_id = len(self.active_bets)
        self.active_bets[bet_id] = {
            'creator_id': creator_id,
            'description': event_description,
            'options': event_info['options'],
            'participants': {},  # {user_id: {'option': choice, 'amount': amount}}
            'status': 'open',
            'created_at': datetime.now(),
            'end_time': event_info['estimated_end_time'],
            'result': None
        }
        
        # Create embed for bet
        embed = discord.Embed(
            title="New Betting Event!",
            description=event_description,
            color=discord.Color.blue()
        )
        embed.add_field(name="Options", value="\n".join(event_info['options']), inline=False)
        embed.add_field(name="Bet ID", value=f"#{bet_id}", inline=True)
        embed.add_field(name="Created by", value=ctx.author.mention, inline=True)
        embed.add_field(name="Estimated End", value=event_info['estimated_end_time'].strftime("%Y-%m-%d %H:%M UTC"), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="placebet")
    async def place_bet(self, ctx, bet_id: int, amount: int, *, choice: str):
        """Place a bet on an event."""
        if bet_id not in self.active_bets:
            await ctx.send("Bet not found!")
            return
            
        bet = self.active_bets[bet_id]
        if bet['status'] != 'open':
            await ctx.send("This bet is no longer accepting entries!")
            return
            
        # Validate choice
        if choice not in bet['options']:
            await ctx.send(f"Invalid choice! Options are: {', '.join(bet['options'])}")
            return
            
        # Check user's balance
        user_id = ctx.author.id
        user_data = self.db.get_or_create_user(user_id)
        if user_data['wallet'] < amount:
            await ctx.send("You don't have enough money in your wallet!")
            return
            
        # Place or update bet
        self.db.remove_money(user_id, amount)
        bet['participants'][user_id] = {
            'option': choice,
            'amount': amount,
            'placed_at': datetime.now()
        }
        
        await ctx.send(f"Bet placed! You bet ${amount} on {choice}")

    @commands.command(name="updatebet")
    async def update_bet(self, ctx, bet_id: int, new_amount: int):
        """Update bet amount before cutoff time."""
        if bet_id not in self.active_bets:
            await ctx.send("Bet not found!")
            return
            
        bet = self.active_bets[bet_id]
        user_id = ctx.author.id
        
        if user_id not in bet['participants']:
            await ctx.send("You haven't placed a bet on this event!")
            return
            
        # Check if within 10 minutes of estimated end time
        if datetime.now() > bet['end_time'] - timedelta(minutes=10):
            await ctx.send("Cannot update bet within 10 minutes of event end!")
            return
            
        old_amount = bet['participants'][user_id]['amount']
        difference = new_amount - old_amount
        
        if difference > 0:
            # Need to pay more
            user_data = self.db.get_or_create_user(user_id)
            if user_data['wallet'] < difference:
                await ctx.send("You don't have enough money to increase your bet!")
                return
            self.db.remove_money(user_id, difference)
        else:
            # Getting refund
            self.db.add_money(user_id, abs(difference))
            
        bet['participants'][user_id]['amount'] = new_amount
        await ctx.send(f"Bet updated! New amount: ${new_amount}")

    @commands.command(name="resolvebet")
    @commands.has_permissions(administrator=True)
    async def resolve_bet(self, ctx, bet_id: int, winner: str):
        """Resolve a bet and distribute winnings."""
        if bet_id not in self.active_bets:
            await ctx.send("Bet not found!")
            return
            
        bet = self.active_bets[bet_id]
        if bet['status'] != 'open':
            await ctx.send("This bet has already been resolved!")
            return
            
        if winner not in bet['options']:
            await ctx.send(f"Invalid winner! Options were: {', '.join(bet['options'])}")
            return
            
        # Calculate total pot and winners
        total_pot = sum(p['amount'] for p in bet['participants'].values())
        winning_bets = {uid: data for uid, data in bet['participants'].items() 
                       if data['option'] == winner}
        winning_total = sum(data['amount'] for data in winning_bets.values())
        
        # Distribute winnings
        for user_id, data in winning_bets.items():
            win_share = (data['amount'] / winning_total) * total_pot
            self.db.add_money(user_id, int(win_share))
            user = ctx.guild.get_member(user_id)
            if user:
                try:
                    await user.send(f"🎉 Congratulations! You won ${int(win_share)} from bet #{bet_id}!")
                except:
                    pass
                    
        # Update bet status
        bet['status'] = 'closed'
        bet['result'] = winner
        bet['resolved_at'] = datetime.now()
        
        # Send resolution message
        embed = discord.Embed(
            title="Bet Resolved!",
            description=bet['description'],
            color=discord.Color.green()
        )
        embed.add_field(name="Winner", value=winner, inline=False)
        embed.add_field(name="Total Pot", value=f"${total_pot}", inline=True)
        embed.add_field(name="Number of Winners", value=str(len(winning_bets)), inline=True)
        
        await ctx.send(embed=embed)

    async def analyze_event(self, description):
        """Analyze event description using AI to extract options and end time."""
        try:
            prompt = f"""Analyze this betting event: "{description}"
            Extract:
            1. Possible outcomes/options
            2. Estimated end time
            3. Event type (sports/politics/entertainment/local)
            
            Return as JSON with fields: options (list), estimated_end_time (ISO date), event_type (string)"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result['estimated_end_time'] = datetime.fromisoformat(result['estimated_end_time'])
            return result
            
        except Exception as e:
            logging.error(f"Error in AI analysis: {str(e)}")
            return None

    @commands.command(name="activebets")
    async def view_active_bets(self, ctx):
        """View all active betting events."""
        active_bets = {bid: bet for bid, bet in self.active_bets.items() 
                      if bet['status'] == 'open'}
                      
        if not active_bets:
            await ctx.send("No active bets!")
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
            
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Betting(bot))

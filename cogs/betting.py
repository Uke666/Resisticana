
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
import aiohttp
import asyncio
from datetime import datetime, timedelta
from utils.database import Database
from cogs.base_cog import BaseCog
import openai
import logging

class Betting(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.db = Database()
        self.bets_file = "data/bets.json"
        self._load_bets()
        self.openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Start auto-resolve bets background task
        self.bot.loop.create_task(self.auto_resolve_bets_loop())
        
    def _load_bets(self):
        """Load bets from the JSON file."""
        try:
            if os.path.exists(self.bets_file):
                with open(self.bets_file, 'r') as f:
                    data = json.load(f)
                    self.active_bets = data.get('active_bets', {})
                    self.bet_results = data.get('resolved_bets', {})
                    
                # Convert string keys to integers
                self.active_bets = {int(k): v for k, v in self.active_bets.items()}
                self.bet_results = {int(k): v for k, v in self.bet_results.items()}
                
                # Convert datetime strings back to datetime objects
                for bet_id, bet in self.active_bets.items():
                    bet['created_at'] = datetime.fromisoformat(bet['created_at']) if isinstance(bet['created_at'], str) else bet['created_at']
                    bet['end_time'] = datetime.fromisoformat(bet['end_time']) if isinstance(bet['end_time'], str) else bet['end_time']
                    for user_id, user_bet in bet['participants'].items():
                        user_bet['placed_at'] = datetime.fromisoformat(user_bet['placed_at']) if isinstance(user_bet['placed_at'], str) else user_bet['placed_at']
            else:
                self.active_bets = {}
                self.bet_results = {}
                self._save_bets()
        except Exception as e:
            logging.error(f"Error loading bets data: {e}")
            self.active_bets = {}
            self.bet_results = {}
            
    def _save_bets(self):
        """Save bets to the JSON file."""
        try:
            # Create a copy to avoid modifying the original data
            active_bets_copy = {}
            for bet_id, bet in self.active_bets.items():
                bet_copy = bet.copy()
                # Convert datetime objects to ISO format for JSON serialization
                bet_copy['created_at'] = bet_copy['created_at'].isoformat() if isinstance(bet_copy['created_at'], datetime) else bet_copy['created_at']
                bet_copy['end_time'] = bet_copy['end_time'].isoformat() if isinstance(bet_copy['end_time'], datetime) else bet_copy['end_time']
                
                # Deep copy participants
                participants_copy = {}
                for user_id, user_bet in bet_copy['participants'].items():
                    user_bet_copy = user_bet.copy()
                    user_bet_copy['placed_at'] = user_bet_copy['placed_at'].isoformat() if isinstance(user_bet_copy['placed_at'], datetime) else user_bet_copy['placed_at']
                    participants_copy[user_id] = user_bet_copy
                    
                bet_copy['participants'] = participants_copy
                active_bets_copy[str(bet_id)] = bet_copy
                
            # Also serialize the bet results
            resolved_bets_copy = {}
            for bet_id, bet in self.bet_results.items():
                resolved_bets_copy[str(bet_id)] = bet
                
            with open(self.bets_file, 'w') as f:
                json.dump({
                    'active_bets': active_bets_copy,
                    'resolved_bets': resolved_bets_copy
                }, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving bets data: {e}")

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

        # Generate a unique bet ID by finding the highest ID and adding 1
        bet_id = max(list(self.active_bets.keys()) + list(self.bet_results.keys()) + [-1]) + 1
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

        # Save the bet
        self._save_bets()
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
        
        # Save the changes
        self._save_bets()
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
        
    @app_commands.command(name="pastbets", description="View past resolved betting events")
    async def view_past_bets(self, interaction: discord.Interaction, limit: int = 5):
        """View past betting events that have been resolved."""
        if not self.bet_results:
            await interaction.response.send_message("No past bets found!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="Past Betting Events",
            description="Recently resolved bets",
            color=discord.Color.gold()
        )
        
        # Sort by resolved_at time, newest first
        sorted_bets = sorted(
            self.bet_results.items(), 
            key=lambda x: x[1].get('resolved_at', datetime.now()), 
            reverse=True
        )
        
        # Take only the requested number
        for bid, bet in sorted_bets[:limit]:
            resolved_time = bet.get('resolved_at', 'Unknown')
            if isinstance(resolved_time, datetime):
                resolved_time = resolved_time.strftime('%Y-%m-%d %H:%M UTC')
                
            embed.add_field(
                name=f"Bet #{bid}",
                value=f"**Description:** {bet['description']}\n"
                      f"**Winner:** {bet['winner']}\n"
                      f"**Total Pot:** ${bet['total_pot']}\n"
                      f"**Participants:** {bet['num_participants']}\n"
                      f"**Resolved:** {resolved_time}",
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
        
        # Move the bet to the resolved bets dict
        self.bet_results[bet_id] = {
            'description': bet['description'],
            'options': bet['options'],
            'winner': winner,
            'total_pot': total_pot,
            'num_participants': len(bet['participants']),
            'num_winners': len(winning_bets),
            'created_at': bet['created_at'],
            'resolved_at': datetime.now()
        }
        
        # Save the changes
        self._save_bets()

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

    @app_commands.command(name="sportsbet", description="Create a sports bet that will be auto-resolved")
    @app_commands.describe(
        match_description="Description of the sports match (e.g., Team A vs Team B on March 30)",
        end_time="When the match ends (hours from now)",
        option1="First betting option",
        option2="Second betting option",
        option3="Third betting option (optional)",
        option4="Fourth betting option (optional)"
    )
    async def create_sports_bet(self, interaction: discord.Interaction, 
                             match_description: str,
                             end_time: int,
                             option1: str,
                             option2: str,
                             option3: str = None,
                             option4: str = None):
        """Create a sports bet that will be automatically resolved."""
        creator_id = interaction.user.id
        
        # Create options list
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)
            
        # Generate a unique bet ID
        bet_id = max(list(self.active_bets.keys()) + list(self.bet_results.keys()) + [-1]) + 1
        
        # Calculate end time
        estimated_end_time = datetime.now() + timedelta(hours=end_time)
        
        # Create the bet
        self.active_bets[bet_id] = {
            'creator_id': creator_id,
            'description': match_description,
            'options': options,
            'participants': {},
            'status': 'open',
            'created_at': datetime.now(),
            'end_time': estimated_end_time,
            'result': None,
            'auto_resolve': True  # Flag for auto-resolution
        }
        
        # Create the embed
        embed = discord.Embed(
            title="New Sports Betting Event!",
            description=match_description,
            color=discord.Color.blue()
        )
        embed.add_field(name="Options", value="\n".join(options), inline=False)
        embed.add_field(name="Bet ID", value=f"#{bet_id}", inline=True)
        embed.add_field(name="Created by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Ends in", value=f"{end_time} hours", inline=True)
        embed.add_field(name="Auto-resolve", value="Yes - Results will be determined automatically", inline=False)
        
        # Save the bet
        self._save_bets()
        await interaction.response.send_message(embed=embed)
            
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
        
        # Save the changes
        self._save_bets()

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

    async def auto_resolve_bets_loop(self):
        """Background task that checks for bets that need to be resolved automatically."""
        await self.bot.wait_until_ready()  # Wait until the bot is ready before starting the loop
        
        while not self.bot.is_closed():
            try:
                # Check for expired bets
                now = datetime.now()
                expired_bets = []
                
                for bet_id, bet in self.active_bets.items():
                    # Only auto-resolve sports bets that have passed their end time
                    if (bet['status'] == 'open' and 
                        bet['end_time'] < now and 
                        any(keyword in bet['description'].lower() for keyword in ['cricket', 'football', 'soccer', 'ipl', 'match', 'game', 'vs', 'versus'])):
                        expired_bets.append((bet_id, bet))
                
                # Process expired bets
                for bet_id, bet in expired_bets:
                    try:
                        # Query OpenAI to get the result
                        result = await self.get_sports_match_result(bet['description'], bet['options'])
                        
                        if result:
                            # Get notification channel
                            notification_channel = None
                            for guild in self.bot.guilds:
                                channel = discord.utils.get(guild.text_channels, name="betting")
                                if channel:
                                    notification_channel = channel
                                    break
                            
                            if not notification_channel:
                                for guild in self.bot.guilds:
                                    if guild.system_channel:
                                        notification_channel = guild.system_channel
                                        break
                            
                            # Resolve the bet
                            total_pot = sum(p['amount'] for p in bet['participants'].values())
                            winning_option = result['winning_option']
                            
                            # Check if winning option is in the bet options
                            if winning_option not in bet['options']:
                                # Find closest matching option
                                similarities = [(option, self._calculate_similarity(option.lower(), winning_option.lower())) 
                                              for option in bet['options']]
                                winning_option = max(similarities, key=lambda x: x[1])[0]
                            
                            winning_bets = {uid: data for uid, data in bet['participants'].items() 
                                           if data['option'] == winning_option}
                            winning_total = sum(data['amount'] for data in winning_bets.values())
                            
                            if winning_total > 0:
                                for user_id, data in winning_bets.items():
                                    win_share = (data['amount'] / winning_total) * total_pot
                                    self.db.add_money(user_id, int(win_share))
                            
                            bet['status'] = 'closed'
                            bet['result'] = winning_option
                            bet['resolved_at'] = now
                            bet['auto_resolved'] = True
                            bet['result_details'] = result['details']
                            
                            # Move to resolved bets
                            self.bet_results[bet_id] = {
                                'description': bet['description'],
                                'options': bet['options'],
                                'winner': winning_option,
                                'total_pot': total_pot,
                                'num_participants': len(bet['participants']),
                                'num_winners': len(winning_bets),
                                'created_at': bet['created_at'],
                                'resolved_at': now,
                                'auto_resolved': True,
                                'result_details': result['details']
                            }
                            
                            # Save changes
                            self._save_bets()
                            
                            # Send notification if channel available
                            if notification_channel:
                                embed = discord.Embed(
                                    title="Bet Auto-Resolved!",
                                    description=bet['description'],
                                    color=discord.Color.green()
                                )
                                embed.add_field(name="Winner", value=winning_option, inline=False)
                                embed.add_field(name="Details", value=result['details'], inline=False)
                                embed.add_field(name="Total Pot", value=f"${total_pot}", inline=True)
                                embed.add_field(name="Number of Winners", value=str(len(winning_bets)), inline=True)
                                
                                await notification_channel.send(embed=embed)
                            
                            logging.info(f"Auto-resolved bet #{bet_id}: {bet['description']} with winner {winning_option}")
                    
                    except Exception as e:
                        logging.error(f"Error auto-resolving bet #{bet_id}: {e}")
                        
            except Exception as e:
                logging.error(f"Error in auto_resolve_bets_loop: {e}")
            
            # Run every 30 minutes
            await asyncio.sleep(1800)
    
    def _calculate_similarity(self, str1, str2):
        """Calculate basic similarity between two strings."""
        if not str1 or not str2:
            return 0
            
        # Convert to sets of words
        set1 = set(str1.split())
        set2 = set(str2.split())
        
        # Calculate Jaccard similarity
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0
    
    async def get_sports_match_result(self, match_description, options):
        """Query OpenAI to get sports match results."""
        try:
            # Build the prompt
            prompt = f"""
            You are a virtual betting assistant that resolves sports bets automatically. 
            
            MATCH DESCRIPTION: {match_description}
            
            BETTING OPTIONS: {', '.join(options)}
            
            Based on the most recent data available, please determine:
            1. The result of this match/event
            2. Which of the betting options listed above is the winner
            3. A brief explanation of how you determined the result
            
            Format your response as a JSON object with these fields:
            - winning_option: The exact text of the winning betting option from the list provided
            - details: A 1-2 sentence explanation of the match result and why this option won
            """
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {"role": "system", "content": "You are a virtual betting assistant that analyzes sports data and resolves bets."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3  # Lower temperature for more factual responses
            )
            
            # Process the response
            result_text = response.choices[0].message.content
            try:
                result = json.loads(result_text)
                
                # Validate the result
                if 'winning_option' not in result or 'details' not in result:
                    logging.error(f"Invalid response format from OpenAI: {result_text}")
                    return None
                    
                return result
                
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON from OpenAI: {result_text}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting sports match result: {e}")
            return None

async def setup(bot):
    cog = Betting(bot)
    await bot.add_cog(cog)
    
    # Don't sync commands here - it's already done in the bot.py on_ready event
    logging.info("Betting cog loaded successfully")

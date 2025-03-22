import os
import logging
import random
import asyncio
import json
from openai import OpenAI

class QuestGenerator:
    """Class for generating random quests using OpenAI API."""
    
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = None
        
        if not self.api_key:
            logging.warning("OPENAI_API_KEY not set! Using fallback quest generation.")
        else:
            self.client = OpenAI(api_key=self.api_key)
            
        # Fallback quests in case API isn't available
        self.fallback_quests = [
            {"title": "Social Media Manager", "description": "Post 5 messages in the general chat channel to boost server activity.", "reward": 50, "time_limit": 30},
            {"title": "Server Guide", "description": "Help a new member understand the server rules and channels.", "reward": 75, "time_limit": 45},
            {"title": "Meme Maker", "description": "Create and share an original meme related to the server theme.", "reward": 60, "time_limit": 20},
            {"title": "Discussion Starter", "description": "Start an interesting discussion that gets at least 5 replies.", "reward": 70, "time_limit": 60},
            {"title": "Voice Chat Hero", "description": "Spend 15 minutes in a voice channel chatting with other members.", "reward": 80, "time_limit": 20},
            {"title": "Art Showcase", "description": "Share some original artwork or creation with the community.", "reward": 90, "time_limit": 30},
            {"title": "Emoji Reactor", "description": "React to 10 different messages with appropriate emojis.", "reward": 40, "time_limit": 15},
            {"title": "Feedback Provider", "description": "Provide constructive feedback on someone's idea or creation.", "reward": 65, "time_limit": 25},
            {"title": "Trivia Master", "description": "Answer 3 trivia questions correctly in the chat.", "reward": 55, "time_limit": 20},
            {"title": "Community Cleaner", "description": "Find and report any old messages that break the server rules.", "reward": 85, "time_limit": 40},
        ]
        
    async def generate_quest(self, username):
        """Generate a random quest for a user."""
        # Try to use OpenAI if available
        if self.client:
            try:
                return await self._generate_quest_with_openai(username)
            except Exception as e:
                logging.error(f"Error generating quest with OpenAI: {e}")
                # Fall back to pre-defined quests
                
        # Use fallback quest generation
        return self._generate_fallback_quest(username)
    
    async def _generate_quest_with_openai(self, username):
        """Generate a quest using OpenAI API."""
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        
        prompt = f"""Generate a fun Discord economy bot quest for user '{username}'. 
        The quest should be something the user can do in a Discord server.
        
        Return the result as a JSON object with these fields:
        - quest_title: A catchy title for the quest
        - quest_description: A detailed description of what the user needs to do
        - reward: A random reward amount between 30 and 100
        - time_limit: A time limit in minutes between 10 and 60
        
        Be creative and make the quest engaging but achievable within the time limit.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            # Parse the response
            quest_data = json.loads(response.choices[0].message.content)
            
            # Format the quest
            return {
                "quest_title": quest_data["quest_title"],
                "quest_description": quest_data["quest_description"],
                "reward": int(quest_data["reward"]),
                "time_limit": int(quest_data["time_limit"])
            }
            
        except Exception as e:
            logging.error(f"Error in OpenAI quest generation: {str(e)}")
            raise
    
    def _generate_fallback_quest(self, username):
        """Generate a quest using pre-defined templates when OpenAI is unavailable."""
        quest = random.choice(self.fallback_quests)
        
        # Customize with username
        quest_description = f"Hey {username}! {quest['description']}"
        
        return {
            "quest_title": quest["title"],
            "quest_description": quest_description,
            "reward": quest["reward"],
            "time_limit": quest["time_limit"]
        }

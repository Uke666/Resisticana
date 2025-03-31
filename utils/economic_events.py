"""
Module for handling economic events for the Discord Economy Bot.
These events will modify the economy temporarily in various ways,
such as multiplying message rewards, investment returns, etc.
"""

import os
import json
import random
from datetime import datetime, timedelta
import logging
import openai
from random import choice, uniform, randint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
EVENT_TYPES = ['positive', 'negative', 'neutral']
EVENT_DURATIONS = {
    'short': (1, 3),     # 1-3 hours
    'medium': (4, 12),   # 4-12 hours
    'long': (13, 48)     # 13-48 hours
}
EVENT_MULTIPLIERS = {
    'positive': (1.1, 1.5),
    'negative': (0.5, 0.9),
    'neutral': (0.95, 1.05)
}

# Path to event data file
EVENT_DATA_FILE = "data/economic_events.json"

class EconomicEventManager:
    """Class to manage economic events."""
    
    def __init__(self):
        """Initialize the event manager."""
        self.active_events = []
        self.load_events()
    
    def load_events(self):
        """Load events from file."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(EVENT_DATA_FILE), exist_ok=True)
            
            # Load events if file exists
            if os.path.exists(EVENT_DATA_FILE):
                with open(EVENT_DATA_FILE, 'r') as f:
                    try:
                        data = json.load(f)
                        # Check if data is a dictionary with 'active_events' key
                        if isinstance(data, dict) and 'active_events' in data:
                            self.active_events = data.get('active_events', [])
                        else:
                            # Handle case where data might be a list or invalid format
                            logger.warning("Invalid data format in events file, resetting events")
                            self.active_events = []
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON in events file, resetting events")
                        self.active_events = []
                    
                    # Clean up expired events
                    self._remove_expired_events()
            else:
                # Create file with empty events
                self.save_events()
        except Exception as e:
            logger.error(f"Error loading economic events: {e}")
            self.active_events = []
    
    def save_events(self):
        """Save events to file."""
        try:
            with open(EVENT_DATA_FILE, 'w') as f:
                json.dump({'active_events': self.active_events}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving economic events: {e}")
    
    def _remove_expired_events(self):
        """Remove expired events."""
        now = datetime.now()
        self.active_events = [
            event for event in self.active_events
            if datetime.fromisoformat(event['end_time']) > now
        ]
        self.save_events()
    
    def get_active_events(self):
        """Get all active events."""
        self._remove_expired_events()
        return self.active_events
    
    def get_current_multiplier(self):
        """Calculate the current economy multiplier based on active events."""
        self._remove_expired_events()
        
        # Start with base multiplier of 1.0
        multiplier = 1.0
        
        # Apply each event's multiplier
        for event in self.active_events:
            multiplier *= event['multiplier']
        
        return multiplier
    
    def generate_event_with_ai(self, event_type=None):
        """Use OpenAI to generate a creative economic event."""
        try:
            # Use provided event type or choose randomly
            if not event_type:
                event_type = random.choice(EVENT_TYPES)
            
            # Make sure it's a valid type
            if event_type not in EVENT_TYPES:
                event_type = random.choice(EVENT_TYPES)
            
            # Set up the API key
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OpenAI API key not found, using fallback event generation")
                return self.generate_fallback_event(event_type)
            
            openai.api_key = api_key
            
            # Choose multiplier based on event type
            min_mult, max_mult = EVENT_MULTIPLIERS[event_type]
            multiplier = round(random.uniform(min_mult, max_mult), 2)
            
            # Choose duration
            duration_type = random.choice(list(EVENT_DURATIONS.keys()))
            min_hours, max_hours = EVENT_DURATIONS[duration_type]
            duration_hours = random.randint(min_hours, max_hours)
            
            # Create prompt for OpenAI
            prompt = f"""
            Generate a brief and creative economic event for a Discord economy bot. The event should be {event_type} in 
            nature (impacting the economy positively, negatively, or neutrally).

            The event should include:
            - A catchy title (5 words or less)
            - A brief description (2-3 sentences max)
            - An economic multiplier of {multiplier}x
            - The event will last for {duration_hours} hours

            Format the response as a JSON object with the following fields only:
            - title: String
            - description: String
            
            Example:
            {{
                "title": "Market Frenzy",
                "description": "Investors are flooding the market with capital. All financial activities yield higher returns for a limited time."
            }}
            
            Keep it engaging and creative, but brief. Focus on how it would impact a virtual economy.
            """
            
            # Call the OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an economy simulation expert that generates creative economic events."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            # Extract the content from the response
            content = response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Find JSON object in the response
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    event_data = json.loads(json_str)
                    
                    # Create event with generated data
                    now = datetime.now()
                    end_time = now + timedelta(hours=duration_hours)
                    
                    event = {
                        'id': len(self.active_events) + 1,
                        'title': event_data.get('title', 'Market Shift'),
                        'description': event_data.get('description', 'A shift in the market is affecting the economy.'),
                        'impact': event_type,
                        'multiplier': multiplier,
                        'start_time': now.isoformat(),
                        'end_time': end_time.isoformat()
                    }
                    
                    return event
            except json.JSONDecodeError:
                logger.warning("Could not parse JSON from OpenAI response")
            except Exception as e:
                logger.error(f"Error processing OpenAI response: {e}")
            
            # Fall back to standard event if we couldn't process the AI response
            return self.generate_fallback_event(event_type)
        
        except Exception as e:
            logger.error(f"Error generating event with AI: {e}")
            return self.generate_fallback_event(event_type)
    
    def generate_fallback_event(self, event_type=None):
        """Generate a fallback event without using AI."""
        # Use provided event type or choose randomly
        if not event_type:
            event_type = random.choice(EVENT_TYPES)
        
        # Make sure it's a valid type
        if event_type not in EVENT_TYPES:
            event_type = random.choice(EVENT_TYPES)
        
        # Configure event based on type
        if event_type == 'positive':
            titles = [
                "Market Boom", "Bull Run", "Gold Rush",
                "Economic Stimulus", "Prosperity Era"
            ]
            descriptions = [
                "A surge in market activity has created new opportunities for profit.",
                "Investor confidence is at an all-time high, boosting all economic activities.",
                "New trade routes have opened, increasing profits for everyone.",
                "A wave of prosperity sweeps through the economy, benefiting all participants.",
                "Technological breakthroughs have stimulated economic growth across all sectors."
            ]
        elif event_type == 'negative':
            titles = [
                "Market Crash", "Recession", "Trade War",
                "Economic Crisis", "Resource Shortage"
            ]
            descriptions = [
                "A sudden market downturn has affected all economic activities.",
                "Consumer confidence has plummeted, reducing profits across all sectors.",
                "International tensions have disrupted trade, lowering economic output.",
                "A financial crisis has spread through the economy, reducing all gains.",
                "Critical resource shortages have driven up costs and reduced profits."
            ]
        else:  # neutral
            titles = [
                "Market Shift", "Economic Reform", "Trade Realignment",
                "Sector Rotation", "Market Correction"
            ]
            descriptions = [
                "The market is undergoing a realignment, with mixed economic impacts.",
                "New economic policies have created a period of adjustment.",
                "Changing consumer preferences have shuffled market dynamics.",
                "Investment capital is rotating between sectors, creating balanced conditions.",
                "The economy is undergoing a natural correction phase."
            ]
        
        # Choose multiplier based on event type
        min_mult, max_mult = EVENT_MULTIPLIERS[event_type]
        multiplier = round(random.uniform(min_mult, max_mult), 2)
        
        # Choose duration
        duration_type = random.choice(list(EVENT_DURATIONS.keys()))
        min_hours, max_hours = EVENT_DURATIONS[duration_type]
        duration_hours = random.randint(min_hours, max_hours)
        
        # Calculate timestamps
        now = datetime.now()
        end_time = now + timedelta(hours=duration_hours)
        
        # Create event
        event = {
            'id': len(self.active_events) + 1,
            'title': random.choice(titles),
            'description': random.choice(descriptions),
            'impact': event_type,
            'multiplier': multiplier,
            'start_time': now.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        return event
    
    def generate_event(self, event_type=None):
        """Generate a new economic event and add it to active events."""
        try:
            # Try to generate with AI first
            event = self.generate_event_with_ai(event_type)
            
            # Add to active events
            self.active_events.append(event)
            self.save_events()
            
            return event
        except Exception as e:
            logger.error(f"Error generating event: {e}")
            raise
    
    def generate_random_events(self, chance=0.1, max_events=3):
        """Randomly generate events based on chance."""
        self._remove_expired_events()
        
        # Don't generate if we already have max events
        if len(self.active_events) >= max_events:
            return None
        
        # Check if we should generate a new event
        if random.random() < chance:
            return self.generate_event()
        
        return None
    
    def get_event_by_id(self, event_id):
        """Get an event by its ID."""
        for event in self.active_events:
            if event['id'] == event_id:
                return event
        return None
    
    def remove_event(self, event_id):
        """Remove an event by its ID."""
        self.active_events = [e for e in self.active_events if e['id'] != event_id]
        self.save_events()
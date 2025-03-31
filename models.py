from app import db
from flask_login import UserMixin
from datetime import datetime
import json


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # ensure password hash field has length of at least 256
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Discord related fields
    discord_id = db.Column(db.String(32), unique=True)
    discord_username = db.Column(db.String(100))
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', foreign_keys='Transaction.user_id')
    inventory_items = db.relationship('InventoryItem', backref='user', lazy='dynamic', foreign_keys='InventoryItem.user_id')


class Guild(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(256))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    members = db.relationship('GuildMember', backref='guild', lazy='dynamic')
    companies = db.relationship('Company', backref='guild', lazy='dynamic')


class GuildMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)
    nickname = db.Column(db.String(100))
    roles = db.Column(db.Text)  # Store as JSON string
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Economy data
    wallet = db.Column(db.Integer, default=0)
    bank = db.Column(db.Integer, default=0)
    last_daily = db.Column(db.DateTime)
    
    # Relationships
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('guild_member.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator_role_id = db.Column(db.String(32))
    
    # Relationships
    employees = db.relationship('GuildMember', backref='company', lazy='dynamic', 
                              foreign_keys=[GuildMember.company_id])
    owner = db.relationship('GuildMember', foreign_keys=[owner_id])


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)
    transaction_type = db.Column(db.String(32), nullable=False)  # "daily", "transfer", "deposit", "withdraw", etc.
    amount = db.Column(db.Integer, nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    description = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    guild = db.relationship('Guild')
    recipient = db.relationship('User', foreign_keys=[recipient_id])


class TransactionRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(256))
    status = db.Column(db.String(16), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])
    guild = db.relationship('Guild')


class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_description = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)  # Store as JSON string
    is_active = db.Column(db.Boolean, default=True)
    winner = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)  # For auto-resolved bets
    auto_resolve = db.Column(db.Boolean, default=False)
    
    # Relationships
    guild = db.relationship('Guild')
    creator = db.relationship('User', foreign_keys=[creator_id])
    placed_bets = db.relationship('PlacedBet', backref='event', lazy='dynamic')


class PlacedBet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bet_id = db.Column(db.Integer, db.ForeignKey('bet.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    choice = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])


class TimeoutLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in seconds
    cost = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    guild = db.relationship('Guild')
    target = db.relationship('User', foreign_keys=[target_id])
    moderator = db.relationship('User', foreign_keys=[moderator_id])


class ActiveQuest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)
    quest_title = db.Column(db.String(100), nullable=False)
    quest_description = db.Column(db.Text, nullable=False)
    reward = db.Column(db.Integer, nullable=False)
    time_limit = db.Column(db.Integer, nullable=False)  # In minutes
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    guild = db.relationship('Guild')


class ItemCategory(db.Model):
    """Categories for items in the shop."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))
    
    # Relationships
    items = db.relationship('Item', backref='category', lazy='dynamic')


class Item(db.Model):
    """Items that can be purchased in the shop."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(256))
    category_id = db.Column(db.Integer, db.ForeignKey('item_category.id'), nullable=False)
    
    # Item properties stored as JSON
    properties = db.Column(db.Text)  # JSON string for custom properties
    is_role_reward = db.Column(db.Boolean, default=False)  # Does item grant a role?
    role_id = db.Column(db.String(32))  # Discord role ID if applicable
    
    is_consumable = db.Column(db.Boolean, default=False)  # Can be used/consumed
    is_tradeable = db.Column(db.Boolean, default=True)  # Can be traded with other users
    is_limited = db.Column(db.Boolean, default=False)  # Limited availability
    quantity_available = db.Column(db.Integer, nullable=True)  # For limited items
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory_items = db.relationship('InventoryItem', backref='item_type', lazy='dynamic')
    
    def get_properties(self):
        """Get item properties as a dictionary."""
        if self.properties:
            return json.loads(self.properties)
        return {}
    
    def set_properties(self, props_dict):
        """Set item properties from a dictionary."""
        self.properties = json.dumps(props_dict)


class InventoryItem(db.Model):
    """Items owned by users."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    
    # Item instance properties stored as JSON (allows for unique properties per instance)
    instance_properties = db.Column(db.Text)  # JSON string for custom properties
    
    acquired_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)  # Guild where item was purchased
    
    def get_instance_properties(self):
        """Get item instance properties as a dictionary."""
        if self.instance_properties:
            return json.loads(self.instance_properties)
        return {}
    
    def set_instance_properties(self, props_dict):
        """Set item instance properties from a dictionary."""
        self.instance_properties = json.dumps(props_dict)
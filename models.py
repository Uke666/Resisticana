from app import db
from flask_login import UserMixin
from datetime import datetime


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
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')


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
    creator = db.relationship('User')
    placed_bets = db.relationship('PlacedBet', backref='event', lazy='dynamic')


class PlacedBet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bet_id = db.Column(db.Integer, db.ForeignKey('bet.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    choice = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User')


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
    user = db.relationship('User')
    guild = db.relationship('Guild')
from app import app
import os
import logging
import threading
import time
from flask import render_template, jsonify, session, redirect, url_for, request, flash
from bot import run_bot
import models
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global status tracking
bot_status = {
    "is_running": False,
    "start_time": None,
    "error": None
}

def start_bot_thread():
    """Start the Discord bot in a separate thread."""
    global bot_status
    
    # Get token from environment variable
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        bot_status["error"] = "DISCORD_TOKEN environment variable not set!"
        logging.error(bot_status["error"])
        return
    
    try:
        bot_status["is_running"] = True
        bot_status["start_time"] = time.time()
        bot_status["error"] = None
        # Run the bot
        run_bot(token)
    except Exception as e:
        bot_status["is_running"] = False
        bot_status["error"] = str(e)
        logging.error(f"Bot error: {e}")

@app.route('/')
def home():
    """Home page of the dashboard."""
    return render_template('index.html')

@app.route('/status')
def status():
    """Return the bot status as JSON."""
    return jsonify(bot_status)

@app.route('/start', methods=['POST'])
def start():
    """Start the bot if it's not already running."""
    global bot_status
    
    if bot_status["is_running"]:
        return jsonify({"success": False, "error": "Bot is already running"})
    
    # Start the bot in a new thread
    bot_thread = threading.Thread(target=start_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    
    return jsonify({"success": True})

@app.route('/restart', methods=['POST'])
def restart():
    """Restart the bot to apply new settings or tokens."""
    global bot_status
    
    # Mark the bot as not running
    bot_status["is_running"] = False
    bot_status["error"] = None
    
    # Start the bot in a new thread
    bot_thread = threading.Thread(target=start_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    
    return jsonify({"success": True})

# Dashboard routes
@app.route('/dashboard')
def dashboard():
    """Dashboard page showing bot statistics."""
    return render_template('dashboard.html')

@app.route('/guilds')
def guilds():
    """List of guilds the bot is in."""
    guilds = models.Guild.query.all()
    return render_template('guilds.html', guilds=guilds)

@app.route('/guild/<int:guild_id>')
def guild_detail(guild_id):
    """Detailed view for a specific guild."""
    guild = models.Guild.query.get_or_404(guild_id)
    return render_template('guild_detail.html', guild=guild)

@app.route('/guild/<int:guild_id>/economy')
def guild_economy(guild_id):
    """Economy statistics for a specific guild."""
    guild = models.Guild.query.get_or_404(guild_id)
    members = models.GuildMember.query.filter_by(guild_id=guild_id).all()
    return render_template('guild_economy.html', guild=guild, members=members)

@app.route('/guild/<int:guild_id>/companies')
def guild_companies(guild_id):
    """Companies in a specific guild."""
    guild = models.Guild.query.get_or_404(guild_id)
    companies = models.Company.query.filter_by(guild_id=guild_id).all()
    return render_template('guild_companies.html', guild=guild, companies=companies)

@app.route('/guild/<int:guild_id>/bets')
def guild_bets(guild_id):
    """Bets in a specific guild."""
    guild = models.Guild.query.get_or_404(guild_id)
    active_bets = models.Bet.query.filter_by(guild_id=guild_id, is_active=True).all()
    past_bets = models.Bet.query.filter_by(guild_id=guild_id, is_active=False).all()
    return render_template('guild_bets.html', guild=guild, active_bets=active_bets, past_bets=past_bets)

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Start bot thread automatically
    if not bot_status["is_running"]:
        bot_thread = threading.Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()
    
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)

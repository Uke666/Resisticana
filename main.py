from app import app
import os
import logging
import threading
from flask import render_template, jsonify, session, redirect, url_for, request, flash
from bot import run_bot
import models
from datetime import datetime
from utils.economic_events import EconomicEventManager

# Initialize economic event manager
event_manager = EconomicEventManager()

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global status tracking (removed, bot status is handled differently now)
bot_status = {
    "is_running": False,
    "start_time": None,
    "error": None
}
bot_thread = None

def start_discord_bot():
    """Start the Discord bot in a separate thread."""
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logging.error("DISCORD_TOKEN not found in environment variables")
        return
    run_bot(token)

def main():
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    # Start Discord bot in a separate thread
    global bot_thread
    bot_thread = threading.Thread(target=start_discord_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

@app.route('/')
def home():
    """Home page of the dashboard."""
    return render_template('index.html')

@app.route('/status')
def status():
    """Return the bot status as JSON."""
    return jsonify({"is_running": bot_thread.is_alive() if bot_thread else False, "start_time": bot_status.get("start_time"), "error": bot_status.get("error")})

@app.route('/start', methods=['POST'])
def start():
    """Start the bot if it's not already running."""
    global bot_status, bot_thread
    
    if bot_thread and bot_thread.is_alive():
        return jsonify({"success": False, "error": "Bot is already running"})
    
    # Start the bot in a new thread
    bot_thread = threading.Thread(target=start_discord_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    return jsonify({"success": True})

@app.route('/restart', methods=['POST'])
def restart():
    """Restart the bot to apply new settings or tokens."""
    global bot_status, bot_thread
    
    # Check if we're rate limited
    if bot_status.get("error") and "429 Too Many Requests" in bot_status["error"]:
        # Get rate limit info if available in the error
        import re
        retry_match = re.search(r'retry_after=(\d+\.\d+)', bot_status["error"])
        retry_time = float(retry_match.group(1)) if retry_match else 60
        
        return jsonify({
            "success": False, 
            "error": f"Discord API rate limit in effect. Please try again in {int(retry_time)} seconds.",
            "retry_after": retry_time
        })
    
    # Mark the bot as not running
    bot_status["is_running"] = False
    bot_status["error"] = None
    
    # Start the bot in a new thread
    bot_thread = threading.Thread(target=start_discord_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    return jsonify({"success": True})

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

@app.route('/inventory')
def inventory():
    """Show a user's inventory."""
    # Get the current user from session
    # In a real implementation, this would use authentication
    user_id = session.get('user_id', 1)  # Default to user 1 for demo

    # Get user from database
    user = models.User.query.get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('dashboard'))

    # Get user's inventory items with their associated item details
    inventory_items = (models.InventoryItem.query
                     .filter_by(user_id=user.id)
                     .all())

    # Group items by category
    items_by_category = {}
    for inv_item in inventory_items:
        item = inv_item.item_type
        category_name = item.category.name

        if category_name not in items_by_category:
            items_by_category[category_name] = []

        # Create item info for template
        item_info = {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'image_url': item.image_url,
            'quantity': inv_item.quantity,
            'is_consumable': item.is_consumable,
            'is_tradeable': item.is_tradeable,
            'is_role_reward': item.is_role_reward,
            'acquired_at': inv_item.acquired_at,
            'properties': item.get_properties() if item.properties else {}
        }

        items_by_category[category_name].append(item_info)

    return render_template('inventory.html', 
                         user=user, 
                         items=inventory_items, 
                         items_by_category=items_by_category)



@app.route('/investments')
def investments():
    """Show a user's company investments."""
    # Get the current user from session
    user_id = session.get('user_id', 1)  # Default to user 1 for demo

    # Get user from database
    user = models.User.query.get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('dashboard'))

    # Get guild memberships for this user
    guild_memberships = models.GuildMember.query.filter_by(user_id=user.id).all()

    # Get investments across all guilds
    investments_data = []
    total_invested = 0
    estimated_daily_income = 0

    for membership in guild_memberships:
        # Find investments for this guild member
        investments = models.CompanyInvestment.query.filter_by(investor_id=membership.id).all()

        for investment in investments:
            # Skip expired investments
            if not investment.is_active():
                continue

            company = models.Company.query.get(investment.company_id)
            guild = models.Guild.query.get(company.guild_id)

            # Calculate investment metrics
            days_remaining = investment.days_remaining()
            created_days_ago = (datetime.utcnow() - investment.created_at).days
            total_days = created_days_ago + days_remaining

            # Calculate estimated daily income (random between 0.8-1.2% of investment)
            daily_income = int(investment.amount_invested * float(investment.percent_ownership) / 100 * 0.01)

            # Add to totals
            total_invested += investment.amount_invested
            estimated_daily_income += daily_income

            # Calculate days consumed and total days
            days_consumed = (datetime.utcnow() - investment.created_at).days
            total_investment_days = days_consumed + days_remaining

            investment_info = {
                'id': investment.id,
                'company_name': company.name,
                'guild_name': guild.name,
                'amount_invested': investment.amount_invested,
                'percent_ownership': float(investment.percent_ownership),
                'created_at': investment.created_at,
                'last_payment_at': investment.last_payment_at,
                'expires_at': investment.expires_at,
                'days_remaining': days_remaining,
                'days_consumed': days_consumed,
                'total_days': total_investment_days,
                'is_active': investment.is_active(),
                'estimated_daily_income': daily_income
            }

            investments_data.append(investment_info)

    # Sort investments by creation date (newest first)
    investments_data.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template('investments.html', 
                         user=user, 
                         investments=investments_data,
                         total_invested=total_invested,
                         estimated_daily_income=estimated_daily_income)

@app.route('/inventory/use/<int:item_id>', methods=['POST'])
def use_item(item_id):
    """Use an item from inventory."""
    # Get the current user from session
    user_id = session.get('user_id', 1)  # Default to user 1 for demo

    # Check if user has the item
    inventory_item = models.InventoryItem.query.filter_by(
        user_id=user_id,
        item_id=item_id
    ).first()

    if not inventory_item or inventory_item.quantity <= 0:
        return jsonify({
            'success': False,
            'message': 'You do not have this item in your inventory.'
        })

    # Get the item details
    item = models.Item.query.get(item_id)
    if not item:
        return jsonify({
            'success': False,
            'message': 'Item not found.'
        })

    # Check if item is consumable
    if not item.is_consumable:
        return jsonify({
            'success': False,
            'message': 'This item cannot be used.'
        })

    # Process item usage (this would include the specific effects based on item type)
    try:
        # Get item properties
        properties = item.get_properties()
        effect_message = f"You used {item.name}"

        # Process different item types based on properties
        if "effect_type" in properties:
            effect_type = properties["effect_type"]

            # Economy boost items
            if effect_type == "money" and "amount" in properties:
                amount = int(properties["amount"])

                # Find guild member record to access wallet
                guild_member = models.GuildMember.query.filter_by(
                    user_id=user_id, 
                    guild_id=inventory_item.guild_id
                ).first()

                if guild_member:
                    guild_member.wallet += amount
                    effect_message += f" and received {amount} coins!"

                    # Add transaction record
                    transaction = models.Transaction(
                        user_id=user_id,
                        guild_id=inventory_item.guild_id,
                        transaction_type="item_use",
                        amount=amount,
                        description=f"Used {item.name}"
                    )
                    models.db.session.add(transaction)

            # Other effect types would be processed here

        # Update inventory
        inventory_item.quantity -= 1
        inventory_item.last_used_at = datetime.utcnow()

        # If quantity is zero, remove the item
        if inventory_item.quantity <= 0:
            models.db.session.delete(inventory_item)

        # Commit changes
        models.db.session.commit()

        return jsonify({
            'success': True,
            'message': effect_message
        })

    except Exception as e:
        models.db.session.rollback()
        logging.error(f"Error during item usage: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while using the item.'
        })

@app.route('/shop')
@app.route('/shop/<category>')
def shop(category=None):
    """Browse the item shop."""
    # Get the current user from session
    user_id = session.get('user_id', 1)  # Default to user 1 for demo
    guild_id = session.get('guild_id', 1)  # Default to guild 1 for demo

    # Get user and guild
    user = models.User.query.get(user_id)
    guild = models.Guild.query.get(guild_id)

    if not user or not guild:
        flash('User or guild not found', 'error')
        return redirect(url_for('dashboard'))

    # Get guild member to access wallet
    guild_member = models.GuildMember.query.filter_by(
        user_id=user.id,
        guild_id=guild.id
    ).first()

    if not guild_member:
        flash('Guild member record not found', 'error')
        return redirect(url_for('dashboard'))

    # Get all item categories
    categories = models.ItemCategory.query.all()

    # Get items
    if category:
        # Find the category by name
        category_obj = models.ItemCategory.query.filter(
            models.ItemCategory.name.ilike(f"%{category}%")
        ).first()

        if category_obj:
            items = models.Item.query.filter_by(category_id=category_obj.id).all()
            selected_category = category_obj.name
        else:
            # Category not found
            flash(f'Category "{category}" not found', 'error')
            return redirect(url_for('shop'))
    else:
        # Get all items
        items = models.Item.query.all()
        selected_category = None

    return render_template('shop.html', 
                         user=user,
                         guild=guild,
                         guild_member=guild_member,
                         categories=categories,
                         items=items,
                         selected_category=selected_category)

@app.route('/events')
def events():
    """Show economic events page."""
    # Get active events
    active_events = event_manager.get_active_events()

    # Add helper data for template
    for event in active_events:
        # Calculate time remaining
        end_time = datetime.fromisoformat(event['end_time'])
        time_diff = end_time - datetime.now()

        if time_diff.days > 0:
            event['time_remaining'] = f"{time_diff.days}d {time_diff.seconds // 3600}h"
        else:
            event['time_remaining'] = f"{time_diff.seconds // 3600}h {(time_diff.seconds // 60) % 60}m"

        # Calculate progress percentage
        start_time = datetime.fromisoformat(event['start_time'])
        total_duration = (end_time - start_time).total_seconds()
        elapsed = (datetime.now() - start_time).total_seconds()
        event['progress_percent'] = min(100, max(0, (elapsed / total_duration) * 100))

    # Determine overall market sentiment based on active events
    if active_events:
        positive_count = len([e for e in active_events if e['impact'] == 'positive'])
        negative_count = len([e for e in active_events if e['impact'] == 'negative'])

        if positive_count > negative_count:
            market_sentiment = "Bullish"
        elif negative_count > positive_count:
            market_sentiment = "Bearish"
        else:
            market_sentiment = "Neutral"
    else:
        market_sentiment = "Neutral"

    # Helper for formatting times
    def from_now(time_str):
        dt = datetime.fromisoformat(time_str)
        diff = datetime.now() - dt

        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds // 3600 > 0:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"

    return render_template('events.html',
                         active_events=active_events,
                         market_sentiment=market_sentiment,
                         from_now=from_now)

@app.route('/api/events/generate', methods=['POST'])
def generate_event():
    """Generate a new economic event."""
    try:
        # Get event type from request (optional)
        data = request.get_json() or {}
        event_type = data.get('event_type')

        # Generate the event
        new_event = event_manager.generate_event(event_type)

        return jsonify({
            'success': True,
            'event': new_event
        })
    except Exception as e:
        logging.error(f"Error generating event: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hints', methods=['GET'])
def get_hints():
    """Retrieve contextual hints for the UI hint system."""
    # Define hints by page and context
    hints = {
        'dashboard': [
            {
                'id': 'dashboard-welcome',
                'title': 'Welcome to Your Dashboard',
                'content': 'This is your central hub for managing your economy bot. Monitor performance, track statistics, and control your bot from here.'
            },
            {
                'id': 'dashboard-refresh',
                'title': 'Refresh Status',
                'content': 'Use the refresh button to get the latest bot status information if you\'ve made changes recently.'
            },
            {
                'id': 'dashboard-charts',
                'title': 'Activity Charts',
                'content': 'These charts show recent activity trends for your bot. They update automatically as more data is collected.'
            }
        ],
        'inventory': [
            {
                'id': 'inventory-usage',
                'title': 'Using Items',
                'content': 'Click the "Use" button on consumable items to activate their special effects. Some items provide economic benefits or special roles.'
            },
            {
                'id': 'inventory-categories',
                'title': 'Item Categories',
                'content': 'Your items are organized by category for easier management. Collectibles are permanent while consumables can be used once.'
            },
            {
                'id': 'inventory-tags',
                'title': 'Item Tags',
                'content': 'Look for colored tags on your items. "Consumable" means the item can be used, while "Not Tradeable" means it\'s bound to your account.'
            }
        ],
        'shop': [
            {
                'id': 'shop-navigation',
                'title': 'Shop Categories',
                'content': 'Browse different categories using the tabs at the top. Each category contains different types of items with unique effects.'
            },
            {
                'id': 'shop-item-types',
                'title': 'Item Types',
                'content': 'Collectibles are permanent, Power-Ups provide temporary effects, and Investments generate passive income over time.'
            },
            {
                'id': 'shop-limited',
                'title': 'Limited Items',
                'content': 'Items marked as "Limited" are available in restricted quantities. Once sold out, they may not be available again!'
            }
        ],
        'investments': [
            {
                'id': 'investments-overview',
                'title': 'Investment Dashboard',
                'content': 'Here you can track all your company investments. Each investment generates passive income over a fixed period.'
            },
            {
                'id': 'investments-income',
                'title': 'Passive Income',
                'content': 'Investments generate daily income based on your ownership percentage and the company\'s performance.'
            },
            {
                'id': 'investments-expiry',
                'title': 'Investment Duration',
                'content': 'Each investment has a limited duration. Monitor the progress bar to see how much time remains before it expires.'
            }
        ],
        'events': [
            {
                'id': 'events-overview',
                'title': 'Economic Events',
                'content': 'Economic events affect the entire economy with multipliers that can increase or decrease rewards, income, and other activities.'
            },
            {
                'id': 'events-impact',
                'title': 'Event Impact',
                'content': 'Events marked as "Positive" increase rewards, while "Negative" events reduce them. "Neutral" events have mixed effects.'
            },
            {
                'id': 'events-duration',
                'title': 'Event Duration',
                'content': 'Events last for a limited time before expiring. Plan your economic activities accordingly to maximize or minimize their effects.'
            }
        ],
        'global': [
            {
                'id': 'global-navigation',
                'title': 'Website Navigation',
                'content': 'Use the navigation menu at the top to quickly access different areas of your economy bot dashboard.'
            },
            {
                'id': 'global-wallet',
                'title': 'Your Wallet',
                'content': 'Your current coin balance is displayed on relevant pages. You\'ll need coins to purchase items and make investments.'
            },
            {
                'id': 'global-discord',
                'title': 'Discord Integration',
                'content': 'Changes made on this website are synchronized with your Discord bot. Use commands in Discord for more real-time interactions.'
            }
        ]
    }

    page = request.args.get('page', 'global')
    if page in hints:
        return jsonify({
            'success': True,
            'hints': hints[page]
        })

    # If page not found, return global hints
    return jsonify({
        'success': True,
        'hints': hints['global']
    })

@app.route('/shop/purchase', methods=['POST'])
def purchase_item():
    """Purchase an item from the shop."""
    # Get the current user from session
    user_id = session.get('user_id', 1)  # Default to user 1 for demo
    guild_id = session.get('guild_id', 1)  # Default to guild 1 for demo

    # Get item ID from request
    data = request.get_json()
    item_id = data.get('item_id')

    if not item_id:
        return jsonify({
            'success': False,
            'message': 'Item ID is required.'
        })

    # Get user, guild, and guild member
    user = models.User.query.get(user_id)
    guild = models.Guild.query.get(guild_id)

    if not user or not guild:
        return jsonify({
            'success': False,
            'message': 'User or guild not found.'
        })

    # Get guild member to access wallet
    guild_member = models.GuildMember.query.filter_by(
        user_id=user.id,
        guild_id=guild.id
    ).first()

    if not guild_member:
        return jsonify({
            'success': False,
            'message': 'Guild member record not found.'
        })

    # Get the item
    item = models.Item.query.get(item_id)

    if not item:
        return jsonify({
            'success': False,
            'message': 'Item not found.'
        })

    # Check if limited and sold out
    if item.is_limited and item.quantity_available is not None and item.quantity_available <= 0:
        return jsonify({
            'success': False,
            'message': 'This item is sold out.'
        })

    # Check if user has enough money
    if guild_member.wallet < item.price:
        return jsonify({
            'success': False,
            'message': 'Insufficient funds.'
        })

    # Process purchase
    try:
        # Deduct money from wallet
        guild_member.wallet -= item.price

        # Add transaction record
        transaction = models.Transaction(
            user_id=user.id,
            guild_id=guild.id,
            transaction_type="purchase",
            amount=-item.price,
            description=f"Purchased {item.name}"
        )
        models.db.session.add(transaction)

        # Check if user already has this item in inventory
        inventory_item = models.InventoryItem.query.filter_by(
            user_id=user.id,
            item_id=item.id,
            guild_id=guild.id
        ).first()

        if inventory_item and not item.is_consumable:
            # Update quantity for non-consumable items
            inventory_item.quantity += 1
            inventory_item.acquired_at = datetime.utcnow()  # Update acquisition time
        else:
            # Create new inventory entry
            inventory_item = models.InventoryItem(
                user_id=user.id,
                item_id=item.id,
                guild_id=guild.id,
                quantity=1
            )
            models.db.session.add(inventory_item)

        # Update item quantity if limited
        if item.is_limited and item.quantity_available is not None:
            item.quantity_available -= 1

        # Commit changes
        models.db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully purchased {item.name} for {item.price} coins!'
        })

    except Exception as e:
        models.db.session.rollback()
        logging.error(f"Error during purchase: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during purchase.'
        })

if __name__ == "__main__":
    main()
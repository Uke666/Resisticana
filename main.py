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

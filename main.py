import os
import logging
import threading
import time
from flask import Flask, render_template, jsonify, session, redirect, url_for
from bot import run_bot

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "discord_economy_bot_secret")

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
    return """
    <!DOCTYPE html>
    <html data-bs-theme="dark">
    <head>
        <title>Discord Economy Bot Dashboard</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <style>
            .status-container {
                margin-top: 50px;
                text-align: center;
            }
            .status-indicator {
                font-size: 1.2rem;
                padding: 10px;
                border-radius: 5px;
                display: inline-block;
                margin-bottom: 20px;
            }
            .running {
                background-color: var(--bs-success);
                color: white;
            }
            .stopped {
                background-color: var(--bs-danger);
                color: white;
            }
            .bot-info {
                margin-top: 30px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="status-container">
                <h1 class="mb-4">Discord Economy Bot</h1>
                <div id="status" class="status-indicator">
                    Checking bot status...
                </div>
                <div class="bot-info">
                    <h2>Bot Features</h2>
                    <ul class="list-group">
                        <li class="list-group-item">Economy system with wallet and bank</li>
                        <li class="list-group-item">Daily rewards of $100 for all users</li>
                        <li class="list-group-item">Company creation and management</li>
                        <li class="list-group-item">AI-generated quests for earning money</li>
                        <li class="list-group-item">Role-based timeout system</li>
                    </ul>
                </div>
                <div class="mt-4">
                    <button id="refreshBtn" class="btn btn-primary">Refresh Status</button>
                    <button id="startBtn" class="btn btn-success">Start Bot</button>
                    <button id="restartBtn" class="btn btn-warning">Restart Bot</button>
                </div>
            </div>
        </div>
        
        <script>
            // Function to fetch bot status
            function checkStatus() {
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        const statusDiv = document.getElementById('status');
                        if (data.is_running) {
                            statusDiv.className = 'status-indicator running';
                            statusDiv.innerHTML = 'Bot is running ✅';
                            
                            // Calculate uptime
                            const uptime = Math.floor((Date.now() / 1000) - data.start_time);
                            let uptimeText = '';
                            
                            if (uptime < 60) {
                                uptimeText = `${uptime} seconds`;
                            } else if (uptime < 3600) {
                                uptimeText = `${Math.floor(uptime / 60)} minutes`;
                            } else {
                                uptimeText = `${Math.floor(uptime / 3600)} hours, ${Math.floor((uptime % 3600) / 60)} minutes`;
                            }
                            
                            statusDiv.innerHTML += `<br>Uptime: ${uptimeText}`;
                        } else {
                            statusDiv.className = 'status-indicator stopped';
                            statusDiv.innerHTML = 'Bot is not running ❌';
                            
                            if (data.error) {
                                statusDiv.innerHTML += `<br>Error: ${data.error}`;
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching status:', error);
                    });
            }
            
            // Check status on page load
            checkStatus();
            
            // Set up refresh button
            document.getElementById('refreshBtn').addEventListener('click', checkStatus);
            
            // Set up start button
            document.getElementById('startBtn').addEventListener('click', function() {
                fetch('/start', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Bot starting...');
                            setTimeout(checkStatus, 2000);
                        } else {
                            alert('Failed to start bot: ' + data.error);
                        }
                    })
                    .catch(error => {
                        console.error('Error starting bot:', error);
                    });
            });
            
            // Set up restart button
            document.getElementById('restartBtn').addEventListener('click', function() {
                fetch('/restart', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Bot restarting with new token...');
                            setTimeout(checkStatus, 2000);
                        } else {
                            alert('Failed to restart bot: ' + data.error);
                        }
                    })
                    .catch(error => {
                        console.error('Error restarting bot:', error);
                    });
            });
        </script>
    </body>
    </html>
    """

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

if __name__ == "__main__":
    # Start bot thread automatically
    if not bot_status["is_running"]:
        bot_thread = threading.Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()
    
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)

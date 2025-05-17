from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import threading
import json
import os
from datetime import datetime
from src.bot.rsi_bb_volume_bot import RsiBbVolumeBot
from src.webgui.config_manager import ConfigManager
from config.donotshare.donotshare import WEBGUI_LOGIN, WEBGUI_PASSWORD

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.secret_key = os.urandom(24)  # Required for session management

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize config manager
config_manager = ConfigManager()

# Global dictionaries to store running bots and their threads
running_bots = {}
bot_threads = {}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == WEBGUI_LOGIN and password == WEBGUI_PASSWORD:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/bots', methods=['GET'])
@login_required
def get_bots():
    bots_status = []
    for bot_id, bot in running_bots.items():
        bots_status.append({
            'id': bot_id,
            'status': 'running' if bot.is_running else 'stopped',
            'pairs': bot.trading_pairs,
            'portfolio_value': bot.portfolio_value,
            'active_positions': len(bot.active_positions)
        })
    return jsonify(bots_status)

@app.route('/api/bots', methods=['POST'])
@login_required
def start_bot():
    config = request.json
    bot_id = config.get('id', f"bot_{len(running_bots) + 1}")
    
    # Save bot configuration
    config_manager.save_bot_config(bot_id, config)
    
    # Create and start the bot
    bot = RsiBbVolumeBot(config)
    bot_thread = threading.Thread(target=bot.run)
    bot_thread.daemon = True
    
    running_bots[bot_id] = bot
    bot_threads[bot_id] = bot_thread
    
    bot_thread.start()
    
    return jsonify({'status': 'success', 'bot_id': bot_id})

@app.route('/api/bots/<bot_id>', methods=['DELETE'])
@login_required
def stop_bot(bot_id):
    if bot_id in running_bots:
        bot = running_bots[bot_id]
        bot.stop()
        del running_bots[bot_id]
        del bot_threads[bot_id]
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Bot not found'}), 404

@app.route('/api/bots/<bot_id>/trades', methods=['GET'])
@login_required
def get_trades(bot_id):
    if bot_id in running_bots:
        bot = running_bots[bot_id]
        return jsonify(bot.trade_history)
    return jsonify([])

@app.route('/api/config/bots', methods=['GET'])
@login_required
def get_available_bots():
    return jsonify(config_manager.get_available_bots())

@app.route('/api/config/bots/<bot_id>', methods=['GET'])
@login_required
def get_bot_config(bot_id):
    config = config_manager.get_bot_config(bot_id)
    if config:
        return jsonify(config)
    return jsonify({'status': 'error', 'message': 'Bot configuration not found'}), 404

@app.route('/api/config/bots/<bot_id>', methods=['POST'])
@login_required
def save_bot_config(bot_id):
    config = request.json
    if config_manager.save_bot_config(bot_id, config):
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Failed to save configuration'}), 500

@app.route('/api/config/bots/<bot_id>/parameters', methods=['GET'])
@login_required
def get_bot_parameters(bot_id):
    return jsonify(config_manager.get_bot_parameters(bot_id))

@app.route('/api/config/bots/<bot_id>/archive', methods=['GET'])
@login_required
def get_archived_configs(bot_id):
    return jsonify(config_manager.get_archived_configs(bot_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
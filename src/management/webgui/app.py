"""
Web GUI Flask Application for Trading Bot Management
---------------------------------------------------

This module implements a Flask web application for managing trading bots via a browser-based interface. It provides user authentication, bot lifecycle management, configuration management, and data visualization features. The app uses the shared bot_manager for bot operations and supports both REST API and HTML endpoints.

Main Features:
- User login/logout and session management
- Start, stop, and monitor trading bots via REST API endpoints
- Manage and archive bot configurations
- Visualize ticker data and technical indicators
- Integrates with the bot_manager for unified bot lifecycle control

Routes:
- /login, /logout: User authentication
- /api/bots: Start, stop, and list bots
- /api/config/bots: Manage bot configurations
- /ticker-analyze: Visualize ticker data
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
import os
from datetime import datetime
from src.management.webgui.config_manager import ConfigManager
from config.donotshare.donotshare import WEBGUI_LOGIN, WEBGUI_PASSWORD
from src.analyzer.ticker_analyzer import TickerAnalyzer
import matplotlib.pyplot as plt
import uuid
from src.management.bot_manager import start_bot, stop_bot, get_status, get_trades, get_running_bots

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
    for bot_id in get_running_bots():
        bots_status.append({
            'id': bot_id,
            'status': 'running',
            'active_positions': len(getattr(get_trades(bot_id), 'active_positions', [])),
            'portfolio_value': getattr(get_trades(bot_id), 'portfolio_value', None)
        })
    return jsonify(bots_status)

@app.route('/api/bots', methods=['POST'])
@login_required
def start_bot_api():
    config = request.json
    bot_id = config.get('id', f"bot_{len(get_running_bots()) + 1}")
    strategy_name = config.get('strategy')
    if not strategy_name:
        return jsonify({'status': 'error', 'message': 'Missing strategy'}), 400
    try:
        started_bot_id = start_bot(strategy_name, config, bot_id)
        config_manager.save_bot_config(started_bot_id, config)
        return jsonify({'status': 'success', 'bot_id': started_bot_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/bots/<bot_id>', methods=['DELETE'])
@login_required
def stop_bot_api(bot_id):
    try:
        stop_bot(bot_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404

@app.route('/api/bots/<bot_id>/trades', methods=['GET'])
@login_required
def get_trades_api(bot_id):
    return jsonify(get_trades(bot_id))

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

@app.route('/ticker-analyze', methods=['GET', 'POST'])
@login_required
def ticker_analyze():
    if request.method == 'POST':
        symbol = request.form.get('symbol', '').upper()
        fundamentals, df = TickerAnalyzer.analyze_ticker(symbol)
        plot_path = None
        error = None
        if fundamentals and df is not None and not df.empty:
            try:
                fig, ax = plt.subplots(figsize=(14, 8))
                df[-1000:].plot(y=['Close', 'SMA_20', 'EMA_20', 'BB_High', 'BB_Low'], ax=ax)
                ax.set_title(f"{symbol} - Last 1000 Candles with Indicators")
                ax.set_ylabel('Price')
                ax.grid(True, linestyle=':')
                # Candlestick overlay (optional, simple version)
                # Save plot
                img_name = f"ticker_{symbol}_{uuid.uuid4().hex[:8]}.png"
                plot_path = f'static/{img_name}'
                plt.savefig(os.path.join(app.static_folder, img_name), bbox_inches='tight')
                plt.close(fig)
            except Exception as e:
                error = f"Plotting error: {e}"
        else:
            error = "No data found for this symbol."
        return render_template('ticker_analyze.html', symbol=symbol, fundamentals=fundamentals, df=df[-1000:] if df is not None else None, plot_path=plot_path, error=error)
    return render_template('ticker_analyze.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
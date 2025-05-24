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
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, Markup, send_file
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
import plotly.graph_objs as go
import plotly.io as pio
from src.optimizer import bb_volume_supertrend_optimizer, rsi_bb_volume_optimizer, ichimoku_rsi_atr_volume_optimizer
import threading

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
    plotly_json = None
    if request.method == 'POST':
        symbol = request.form.get('symbol', '').upper()
        fundamentals, df = TickerAnalyzer.analyze_ticker(symbol)
        error = None
        if fundamentals and df is not None and not df.empty:
            try:
                # Prepare Plotly figure
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=df.index,
                    open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                    name='Candlestick'))
                if 'SMA_20' in df:
                    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='SMA 20'))
                if 'EMA_20' in df:
                    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], mode='lines', name='EMA 20'))
                if 'BB_High' in df:
                    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], mode='lines', name='BB High', line=dict(dash='dot')))
                if 'BB_Low' in df:
                    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], mode='lines', name='BB Low', line=dict(dash='dot')))
                fig.update_layout(title=f"{symbol} - Last 1000 Candles with Indicators", xaxis_title='Date', yaxis_title='Price', xaxis_rangeslider_visible=False)
                plotly_json = pio.to_json(fig)
            except Exception as e:
                error = f"Plotly plotting error: {e}"
        else:
            error = "No data found for this symbol."
        return render_template('ticker_analyze.html', symbol=symbol, fundamentals=fundamentals, df=df[-1000:] if df is not None else None, plotly_json=plotly_json, error=error)
    return render_template('ticker_analyze.html')

# --- Optimizer Management ---
optimizers = {
    'bb_volume_supertrend': bb_volume_supertrend_optimizer.BBSuperTrendVolumeBreakoutOptimizer,
    'rsi_bb_volume': rsi_bb_volume_optimizer.RsiBBVolumeOptimizer,
    'ichimoku_rsi_atr_volume': ichimoku_rsi_atr_volume_optimizer.IchimokuRSIATRVolumeOptimizer,
}

running_optimizers = {}
optimizer_results = {}

@app.route('/optimizers', methods=['GET', 'POST'])
@login_required
def manage_optimizers():
    if request.method == 'POST':
        optimizer_name = request.form.get('optimizer')
        data_file = request.form.get('data_file')
        if optimizer_name not in optimizers:
            flash('Unknown optimizer selected', 'danger')
            return redirect(url_for('manage_optimizers'))
        optimizer_class = optimizers[optimizer_name]
        optimizer = optimizer_class()
        def run_opt():
            result = optimizer.optimize_single_file(data_file)
            optimizer_results[f'{optimizer_name}_{data_file}'] = result
            running_optimizers.pop(f'{optimizer_name}_{data_file}', None)
        thread = threading.Thread(target=run_opt)
        thread.start()
        running_optimizers[f'{optimizer_name}_{data_file}'] = thread
        flash(f'Optimizer {optimizer_name} started for {data_file}', 'success')
        return redirect(url_for('manage_optimizers'))
    # GET: show available optimizers and running jobs
    available_optimizers = list(optimizers.keys())
    data_files = []
    data_dir = 'data/all'
    if os.path.exists(data_dir):
        data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    running = list(running_optimizers.keys())
    finished = list(optimizer_results.keys())
    return render_template('optimizers.html', available_optimizers=available_optimizers, data_files=data_files, running=running, finished=finished)

@app.route('/optimizers/<job_id>/status', methods=['GET'])
@login_required
def optimizer_status(job_id):
    running = job_id in running_optimizers
    finished = job_id in optimizer_results
    return jsonify({'running': running, 'finished': finished})

@app.route('/optimizers/<job_id>/results', methods=['GET'])
@login_required
def optimizer_results_api(job_id):
    result = optimizer_results.get(job_id)
    if result:
        return jsonify(result)
    return jsonify({'status': 'not found'}), 404

@app.route('/optimizers/<job_id>/download', methods=['GET'])
@login_required
def optimizer_results_download(job_id):
    result = optimizer_results.get(job_id)
    if result:
        path = os.path.join('results', f'{job_id}_optimization_results.json')
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
    return jsonify({'status': 'not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
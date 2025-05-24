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
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from itsdangerous import URLSafeTimedSerializer
import pyotp
import qrcode
import io
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import csv
import matplotlib.pyplot as plt
import uuid
import plotly.graph_objs as go
import plotly.io as pio
import threading
import yfinance as yf
import psutil
import shutil
import socket
import time
from werkzeug.utils import secure_filename
from binance.client import Client as BinanceClient
from ib_insync import IB, Stock

# --- App and DB Initialization (MUST BE FIRST) ---
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.urandom(24)

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', 'db', 'webgui_users.db')
db_path = os.path.abspath(db_path)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'akossyrev@gmail.com'
app.config['MAIL_PASSWORD'] = '....'

from src.management.webgui.models import db, User

db.init_app(app)
mail = Mail(app)

# Ensure DB tables exist before any queries
with app.app_context():
    db.create_all()

# --- Login Manager ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Other Imports (after app/db setup) ---
from src.management.webgui.config_manager import ConfigManager
from config.donotshare.donotshare import WEBGUI_LOGIN, WEBGUI_PASSWORD, WEBGUI_PORT
from src.analyzer.ticker_analyzer import TickerAnalyzer
from src.management.bot_manager import start_bot, stop_bot, get_status, get_trades, get_running_bots
from src.optimizer import bb_volume_supertrend_optimizer, rsi_bb_volume_optimizer, ichimoku_rsi_atr_volume_optimizer
from src.notification.logger import _logger
from src.notification.emailer import send_email_alert
from src.notification.telegram_notifier import send_telegram_alert
from src.analyzer.stock_screener import StockScreener
from src.analyzer.tickers_list import (
    get_six_tickers, get_sp500_tickers_wikipedia, get_sp_midcap_wikipedia, get_all_us_tickers
)

# --- Config Manager ---
config_manager = ConfigManager()

# --- Password Reset Token Serializer ---
serializer = URLSafeTimedSerializer(app.secret_key)

# --- User Loader (after db/app setup) ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Routes and Views (all after db/app setup) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.twofa_secret:
                session['pre_2fa_user'] = user.id
                return redirect(url_for('twofa_verify'))
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
    print(">>> /ticker-analyze route hit")
    plotly_json = None
    fundamentals = None
    df = None
    symbol = None
    error = None
    if request.method == 'POST':
        symbol = request.form.get('symbol', '').upper()
        fundamentals, df = TickerAnalyzer.analyze_ticker(symbol)
        if fundamentals and df is not None and not df.empty:
            try:
                # Sort df by index (datetime) descending
                df = df.sort_index(ascending=False)
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
    return render_template(
        'ticker_analyze.html',
        symbol=symbol,
        fundamentals=fundamentals,
        df=df,
        plotly_json=plotly_json,
        error=error
    )

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

@app.route('/data-download', methods=['GET', 'POST'])
@login_required
def data_download():
    message = None
    if request.method == 'POST':
        symbol = request.form.get('symbol')
        timeframe = request.form.get('timeframe')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        source = request.form.get('source')
        filename = secure_filename(f"{symbol}_{timeframe}_{start_date}_{end_date}.csv")
        save_path = os.path.join('data', filename)
        try:
            if source == 'yfinance':
                df = yf.download(symbol, start=start_date, end=end_date, interval=timeframe)
                if df.empty:
                    raise Exception('No data returned from yfinance')
                df.to_csv(save_path)
                message = f"Downloaded {len(df)} rows from yfinance to {save_path}"
            elif source == 'binance' and BinanceClient is not None:
                # You must set your API keys in environment or config for real use
                client = BinanceClient()
                klines = client.get_historical_klines(symbol, timeframe, start_str=start_date, end_str=end_date)
                import pandas as pd
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                df.to_csv(save_path)
                message = f"Downloaded {len(df)} rows from Binance to {save_path}"
            elif source == 'ibkr' and IB is not None:
                ib = IB()
                ib.connect('127.0.0.1', 7497, clientId=1)
                contract = Stock(symbol, 'SMART', 'USD')
                bars = ib.reqHistoricalData(
                    contract,
                    endDateTime=end_date,
                    durationStr=f"{(pd.to_datetime(end_date)-pd.to_datetime(start_date)).days} D",
                    barSizeSetting=timeframe,
                    whatToShow='TRADES',
                    useRTH=True,
                    formatDate=1
                )
                import pandas as pd
                df = pd.DataFrame([b.__dict__ for b in bars])
                if not df.empty:
                    df.set_index('date', inplace=True)
                    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                    df.to_csv(save_path)
                    message = f"Downloaded {len(df)} rows from IBKR to {save_path}"
                else:
                    raise Exception('No data returned from IBKR')
                ib.disconnect()
            else:
                message = 'Invalid source or required package not installed.'
        except Exception as e:
            message = f"Error: {e}"
    return render_template('data_download.html', message=message)

@app.route('/api/health', methods=['GET'])
@login_required
def health_check():
    status = {'flask': 'ok'}
    total, used, free = shutil.disk_usage('.')
    status['disk'] = {'total': total, 'used': used, 'free': free}
    mem = psutil.virtual_memory()
    status['memory'] = {'total': mem.total, 'used': mem.used, 'percent': mem.percent}
    status['cpu'] = {'percent': psutil.cpu_percent(interval=0.5)}
    status['hostname'] = socket.gethostname()
    # Broker connectivity (example: Binance)
    try:
        if BinanceClient is not None:
            client = BinanceClient()
            client.ping()
            status['binance'] = 'ok'
        else:
            status['binance'] = 'not_installed'
    except Exception as e:
        status['binance'] = f'error: {e}'
    # Add similar checks for Coinbase, IBKR if needed
    return jsonify(status)

@app.route('/system-status')
@login_required
def system_status():
    return render_template('system_status.html')

# --- Resource Monitoring and Alerting ---
RESOURCE_ALERT_CPU = 90  # percent
RESOURCE_ALERT_MEM = 90  # percent
RESOURCE_ALERT_INTERVAL = 60  # seconds

alerted = {'cpu': False, 'mem': False}

def monitor_resources():
    while True:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        alert_msgs = []
        if mem.percent > RESOURCE_ALERT_MEM and not alerted['mem']:
            msg = f"High memory usage! Memory: {mem.percent}%"
            alert_msgs.append(msg)
            alerted['mem'] = True
        elif mem.percent <= RESOURCE_ALERT_MEM:
            alerted['mem'] = False
        if cpu > RESOURCE_ALERT_CPU and not alerted['cpu']:
            msg = f"High CPU usage! CPU: {cpu}%"
            alert_msgs.append(msg)
            alerted['cpu'] = True
        elif cpu <= RESOURCE_ALERT_CPU:
            alerted['cpu'] = False
        for msg in alert_msgs:
            _logger.error(msg)
            if send_email_alert:
                send_email_alert(subject="System Alert", message=msg)
            if send_telegram_alert:
                send_telegram_alert(msg)
        time.sleep(RESOURCE_ALERT_INTERVAL)

monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
monitor_thread.start()

# --- Registration Route (admin only or open) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful!')
        return redirect(url_for('login'))
    return render_template('register.html')

# --- 2FA Verification Route ---
@app.route('/2fa-verify', methods=['GET', 'POST'])
def twofa_verify():
    user_id = session.get('pre_2fa_user')
    if not user_id:
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if request.method == 'POST':
        code = request.form['code']
        if pyotp.TOTP(user.twofa_secret).verify(code):
            login_user(user)
            session.pop('pre_2fa_user', None)
            return redirect(url_for('index'))
        flash('Invalid 2FA code')
    return render_template('2fa_verify.html')

# --- 2FA Setup Route ---
@app.route('/2fa-setup', methods=['GET', 'POST'])
@login_required
def twofa_setup():
    user = User.query.get(current_user.id)
    if request.method == 'POST':
        if not user.twofa_secret:
            secret = pyotp.random_base32()
            user.twofa_secret = secret
            db.session.commit()
        flash('2FA enabled!')
        return redirect(url_for('index'))
    if not user.twofa_secret:
        secret = pyotp.random_base32()
        user.twofa_secret = secret
        db.session.commit()
    otp_uri = pyotp.totp.TOTP(user.twofa_secret).provisioning_uri(name=user.email, issuer_name="CryptoTradingWebGUI")
    img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    qr_b64 = 'data:image/png;base64,' + base64.b64encode(buf.read()).decode('utf-8')
    return render_template('2fa_setup.html', qr_b64=qr_b64, secret=user.twofa_secret)

# --- Password Reset Request ---
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = serializer.dumps(user.email, salt='reset-password')
            link = url_for('reset_password', token=token, _external=True)
            msg = Message('Password Reset', recipients=[user.email], body=f'Reset your password: {link}')
            mail.send(msg)
            flash('Password reset email sent!')
        else:
            flash('Email not found')
    return render_template('reset_password_request.html')

# --- Password Reset Form ---
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='reset-password', max_age=3600)
    except Exception:
        flash('Invalid or expired token')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=email).first()
    if request.method == 'POST':
        password = request.form['password']
        user.set_password(password)
        db.session.commit()
        flash('Password reset successful!')
        return redirect(url_for('login'))
    return render_template('reset_password.html')

# --- Admin User Management Page ---
@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash('Admin access required')
        return redirect(url_for('index'))
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted')
    return redirect(url_for('admin_users'))

@app.route('/stock-screener', methods=['GET', 'POST'])
@login_required
def stock_screener():
    universes = {
        'SIX': get_six_tickers,
        'S&P 500': get_sp500_tickers_wikipedia,
        'S&P 400 Midcap': get_sp_midcap_wikipedia,
        'All US': get_all_us_tickers,
    }
    results = None
    error = None
    params = {
        'min_price': 0,
        'max_price': 10000,
        'min_volume': 0,
        'min_market_cap': 0,
        'max_pe': 25,
        'min_roe': 0.15,
        'max_de': 100,
        'fcf_positive': True,
        'price_above_50d_200d': True
    }
    if request.method == 'POST':
        universe = request.form.get('universe', 'SIX')
        min_price = float(request.form.get('min_price', 0))
        max_price = float(request.form.get('max_price', 10000))
        min_volume = float(request.form.get('min_volume', 0))
        min_market_cap = float(request.form.get('min_market_cap', 0))
        max_pe = float(request.form.get('max_pe', 25))
        min_roe = float(request.form.get('min_roe', 0.15))
        max_de = float(request.form.get('max_de', 100))
        fcf_positive = request.form.get('fcf_positive', 'on') == 'on'
        price_above_50d_200d = request.form.get('price_above_50d_200d', 'on') == 'on'
        params = {
            'min_price': min_price,
            'max_price': max_price,
            'min_volume': min_volume,
            'min_market_cap': min_market_cap,
            'max_pe': max_pe,
            'min_roe': min_roe,
            'max_de': max_de,
            'fcf_positive': fcf_positive,
            'price_above_50d_200d': price_above_50d_200d
        }
        try:
            tickers = universes[universe]()
            screener = StockScreener(stock_data=[])
            stocks = []
            import yfinance as yf
            for ticker in tickers:
                try:
                    info = yf.Ticker(ticker).info
                    pe = info.get('trailingPE', None)
                    roe = info.get('returnOnEquity', None)
                    de = info.get('debtToEquity', None)
                    price = info.get('currentPrice', 0)
                    fifty_day = info.get('fiftyDayAverage', 0)
                    two_hundred_day = info.get('twoHundredDayAverage', 0)
                    fcf = None
                    try:
                        fcf_info = screener.get_fcf_growth(ticker)
                        if fcf_info and isinstance(fcf_info, dict) and 'FCF (oldest → newest)' in fcf_info:
                            fcf_list = fcf_info['FCF (oldest → newest)']
                            if fcf_list:
                                fcf = fcf_list[-1]
                    except Exception:
                        pass
                    stocks.append({
                        'ticker': ticker,
                        'price': price,
                        'volume': info.get('volume', 0),
                        'market_cap': info.get('marketCap', 0),
                        'pe': pe,
                        'roe': roe,
                        'de': de,
                        'fifty_day': fifty_day,
                        'two_hundred_day': two_hundred_day,
                        'fcf': fcf
                    })
                except Exception:
                    continue
            screener.stock_data = stocks
            filtered = [s for s in stocks if
                s['price'] is not None and params['min_price'] <= s['price'] <= params['max_price'] and
                s['volume'] is not None and s['volume'] >= params['min_volume'] and
                s['market_cap'] is not None and s['market_cap'] >= params['min_market_cap'] and
                (s['pe'] is None or s['pe'] <= params['max_pe']) and
                (s['roe'] is None or s['roe'] >= params['min_roe']) and
                (s['de'] is None or s['de'] <= params['max_de']) and
                (not params['fcf_positive'] or (s['fcf'] is not None and s['fcf'] > 0)) and
                (not params['price_above_50d_200d'] or (s['price'] > (s['fifty_day'] or 0) > (s['two_hundred_day'] or 0)))
            ]
            results = filtered
            # Handle export
            if 'export' in request.form:
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=['ticker','price','volume','market_cap','pe','roe','de','fifty_day','two_hundred_day','fcf'])
                writer.writeheader()
                for row in results:
                    writer.writerow(row)
                output.seek(0)
                return app.response_class(
                    output.getvalue(),
                    mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=screened_stocks.csv'}
                )
        except Exception as e:
            error = str(e)
    return render_template('stock_screener.html', universes=list(universes.keys()), params=params, results=results, error=error)

@app.route('/api/bot-types', methods=['GET'])
@login_required
def get_bot_types():
    bot_types = list(optimizers.keys())
    return jsonify({'bot_types': bot_types})
 
print(app.url_map)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=WEBGUI_PORT) 
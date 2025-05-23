from flask import Flask, request, jsonify, Response
import os
import logging
from functools import wraps
from config.donotshare.donotshare import API_LOGIN, API_PASSWORD, API_PORT
from src.management.bot_manager import start_bot, stop_bot, get_status, get_trades, get_running_bots

app = Flask(__name__)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_auth(username, password):
    return username == API_LOGIN and password == API_PASSWORD

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/start_bot', methods=['POST'])
@requires_auth
def start_bot_api():
    data = request.json
    strategy_name = data.get('strategy')
    config = data.get('config', {'trading_pair': 'BTCUSDT', 'initial_balance': 1000.0})
    bot_id = data.get('bot_id')
    if not strategy_name:
        return jsonify({'error': 'Missing strategy'}), 400
    try:
        started_bot_id = start_bot(strategy_name, config, bot_id)
        return jsonify({'message': f'Started bot for {strategy_name}.', 'bot_id': started_bot_id})
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        return jsonify({'error': f'Failed to start bot: {e}'}), 500

@app.route('/stop_bot', methods=['POST'])
@requires_auth
def stop_bot_api():
    data = request.json
    bot_id = data.get('bot_id')
    if not bot_id:
        return jsonify({'error': 'Missing bot_id'}), 400
    try:
        stop_bot(bot_id)
        return jsonify({'message': f'Stopped bot {bot_id}.'})
    except Exception as e:
        logger.error(f"Failed to stop bot: {e}")
        return jsonify({'error': f'Failed to stop bot: {e}'}), 500

@app.route('/status', methods=['GET'])
@requires_auth
def status_api():
    return jsonify(get_status())

@app.route('/trades', methods=['GET'])
@requires_auth
def trades_api():
    bot_id = request.args.get('bot_id')
    if not bot_id:
        return jsonify({'error': 'Missing bot_id'}), 400
    return jsonify(get_trades(bot_id))

@app.route('/log', methods=['GET'])
@requires_auth
def log():
    strategy_name = request.args.get('strategy')
    if not strategy_name:
        return jsonify({'error': 'Missing strategy'}), 400
    log_file = f"logs/{strategy_name}.log"
    if not os.path.exists(log_file):
        return jsonify({'error': f'No log file found for {strategy_name}.'}), 404
    with open(log_file, 'r') as f:
        lines = f.readlines()[-20:]
    return jsonify({'log': ''.join(lines) or "No recent logs."})

@app.route('/backtest', methods=['POST'])
@requires_auth
def backtest():
    data = request.json
    strategy = data.get('strategy')
    ticker = data.get('ticker')
    tf = data.get('tf')
    if not all([strategy, ticker, tf]):
        return jsonify({'error': 'Usage: strategy, ticker, tf required'}), 400
    # Stub: Replace with actual backtest logic
    return jsonify({'message': f'Backtesting {strategy} on {ticker} ({tf})... [stub]'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=API_PORT)

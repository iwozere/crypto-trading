import os
import json
import pandas as pd
import numpy as np
from skopt import gp_minimize
from skopt.space import Real, Integer
from skopt.utils import use_named_args
from multiprocessing import Pool, cpu_count
import matplotlib.pyplot as plt
import seaborn as sns
import talib as ta
from src.strats.CryptoTrendingStrategy import CryptoTrendStrategy
import warnings

class TrendOptimizer:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Set up plotting style
        plt.style.use('default')
        sns.set_theme(style="darkgrid")
        plt.rcParams['figure.figsize'] = (15, 10)
        plt.rcParams['font.size'] = 10
        
        # Define parameter space for scikit-optimize
        self.space = [
            Integer(5, 30, name='rsi_period'),
            Real(30, 70, name='rsi_threshold'),
            Integer(3, 20, name='ema_fast'),
            Integer(5, 30, name='ema_mid'),
            Integer(10, 50, name='ema_slow'),
            Integer(3, 20, name='volume_sma'),
            Integer(3, 20, name='atr_period'),
            Integer(3, 20, name='supertrend_period'),
            Real(0.5, 3.0, name='supertrend_multiplier'),
            Real(0.1, 1.0, name='risk_per_trade')
        ]
        
        # Store current metrics and symbol
        self.current_metrics = {}
        self.current_symbol = None
        
        # Initialize data storage
        self.raw_data = {}
        self.load_all_data()
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
        
    def load_all_data(self):
        """Load all data files once during initialization"""
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]
        for data_file in data_files:
            try:
                symbol = data_file.split('_')[0]
                df = pd.read_csv(os.path.join(self.data_dir, data_file))
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Replace zeros with small values to avoid division by zero
                df['close'] = df['close'].replace(0, 0.0001)
                df['high'] = df['high'].replace(0, 0.0001)
                df['low'] = df['low'].replace(0, 0.0001)
                df['volume'] = df['volume'].replace(0, 0.0001)
                
                self.raw_data[symbol] = df
                print(f"Loaded data for {symbol}")
            except Exception as e:
                print(f"Error loading {data_file}: {str(e)}")
        
    def params_to_dict(self, params):
        """Convert parameter list to dictionary with proper types"""
        param_types = {
            'rsi_period': int,
            'rsi_threshold': float,
            'ema_fast': int,
            'ema_mid': int,
            'ema_slow': int,
            'volume_sma': int,
            'atr_period': int,
            'supertrend_period': int,
            'supertrend_multiplier': float,
            'risk_per_trade': float
        }
        return {name: param_types[name](value) for name, value in zip([p.name for p in self.space], params)}
    
    def convert_to_serializable(self, obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self.convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_to_serializable(item) for item in obj]
        return obj
    
    def calculate_supertrend(self, df, period, multiplier):
        """Calculate SuperTrend indicator"""
        # Convert to numpy arrays for faster computation
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Calculate ATR
        atr = ta.ATR(df['high'], df['low'], df['close'], period)
        atr = atr.values
        
        # Calculate basic upper and lower bands
        hl2 = (high + low) / 2
        upper = hl2 + (multiplier * atr)
        lower = hl2 - (multiplier * atr)
        
        # Initialize arrays
        supertrend = np.ones(len(df))
        supertrend_stop = np.copy(lower)
        
        # Calculate SuperTrend
        for i in range(1, len(df)):
            if close[i] > upper[i-1]:
                supertrend[i] = 1
            elif close[i] < lower[i-1]:
                supertrend[i] = -1
            else:
                supertrend[i] = supertrend[i-1]
                
            if supertrend[i] == 1:
                supertrend_stop[i] = lower[i]
            else:
                supertrend_stop[i] = upper[i]
        
        # Convert back to pandas Series
        supertrend = pd.Series(supertrend, index=df.index)
        supertrend_stop = pd.Series(supertrend_stop, index=df.index)
        
        return supertrend, supertrend_stop
    
    def calculate_indicators(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        """Calculate all required indicators"""
        # Create a copy of the DataFrame to avoid modifying the original
        df = df.copy()
        
        # Calculate EMAs
        df['ema_slow'] = ta.EMA(df['close'], params['ema_slow'])
        df['ema_mid'] = ta.EMA(df['close'], params['ema_mid'])
        df['ema_fast'] = ta.EMA(df['close'], params['ema_fast'])
        
        # Calculate RSI
        df['rsi'] = ta.RSI(df['close'], params['rsi_period'])
        
        # Calculate ATR
        df['atr'] = ta.ATR(df['high'], df['low'], df['close'], params['atr_period'])
        
        # Calculate SuperTrend
        df['supertrend'], df['supertrend_stop'] = self.calculate_supertrend(
            df, params['supertrend_period'], params['supertrend_multiplier']
        )
        
        # Calculate Volume SMA
        df['volume_sma'] = df['volume'].rolling(params['volume_sma']).mean()
        
        # Fill NaN values with 0
        df = df.fillna(0)
        
        return df
    
    def plot_results(self, df, trade_log, params, data_file):
        """Plot trading results with buy/sell points"""
        # Set figure size to be 4x wider and 3x higher
        plt.rcParams['figure.figsize'] = (60, 30)  # Original was (15, 10)
        
        fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, gridspec_kw={'height_ratios': [3, 1, 1, 1, 1]}, sharex=True)
        
        # Plot price and EMAs
        ax1.plot(df.index, df['close'], label='Price', color='blue', alpha=0.7)
        ax1.plot(df.index, df['ema_fast'], label=f'EMA Fast ({params["ema_fast"]})', color='green', alpha=0.7)
        ax1.plot(df.index, df['ema_mid'], label=f'EMA Mid ({params["ema_mid"]})', color='orange', alpha=0.7)
        ax1.plot(df.index, df['ema_slow'], label=f'EMA Slow ({params["ema_slow"]})', color='red', alpha=0.7)
        
        # Plot buy/sell points with annotations
        buy_points = []
        sell_points = []
        
        # Create separate lists for buy and sell points to handle legend properly
        buy_timestamps = []
        buy_prices = []
        sell_timestamps = []
        sell_prices = []
        
        for trade in trade_log.to_dict('records'):
            timestamp = pd.to_datetime(trade['timestamp'])
            price = trade['price']
            size = trade['size']
            pnl = trade.get('pnl', 0)
            
            if trade['signal'] == 'buy':
                buy_points.append((timestamp, price, size))
                buy_timestamps.append(timestamp)
                buy_prices.append(price)
            else:
                sell_points.append((timestamp, price, size, pnl, trade.get('reason', '')))
                sell_timestamps.append(timestamp)
                sell_prices.append(price)
        
        # Plot buy and sell points separately to ensure proper legend handling
        if buy_timestamps:
            ax1.scatter(buy_timestamps, buy_prices, marker='^', color='green', s=200, label='Buy')
        if sell_timestamps:
            ax1.scatter(sell_timestamps, sell_prices, marker='v', color='red', s=200, label='Sell')
        
        ax1.set_title(f'{data_file} Trading Results', fontsize=20)
        ax1.set_ylabel('Price', fontsize=16)
        ax1.legend(fontsize=14)
        ax1.grid(True)
        
        # Plot RSI
        ax2.plot(df.index, df['rsi'], label='RSI', color='purple')
        ax2.axhline(y=params['rsi_threshold'], color='red', linestyle='--', label=f'RSI Threshold ({params["rsi_threshold"]})')
        ax2.axhline(y=100-params['rsi_threshold'], color='red', linestyle='--')
        ax2.set_ylabel('RSI', fontsize=16)
        ax2.legend(fontsize=14)
        ax2.grid(True)
        
        # Plot ATR
        ax3.plot(df.index, df['atr'], label=f'ATR ({params["atr_period"]})', color='orange')
        ax3.set_ylabel('ATR', fontsize=16)
        ax3.legend(fontsize=14)
        ax3.grid(True)
        
        # Plot SuperTrend
        ax4.plot(df.index, df['supertrend_stop'], label=f'SuperTrend Stop ({params["supertrend_period"]}, {params["supertrend_multiplier"]})', color='purple')
        ax4.plot(df.index, df['close'], label='Price', color='blue', alpha=0.3)
        ax4.fill_between(df.index, df['close'], df['supertrend_stop'], 
                        where=df['supertrend'] == 1, color='green', alpha=0.1)
        ax4.fill_between(df.index, df['close'], df['supertrend_stop'], 
                        where=df['supertrend'] == -1, color='red', alpha=0.1)
        ax4.set_ylabel('SuperTrend', fontsize=16)
        ax4.legend(fontsize=14)
        ax4.grid(True)
        
        # Plot volume
        ax5.bar(df.index, df['volume'], label='Volume', color='gray', alpha=0.7)
        ax5.plot(df.index, df['volume_sma'], label=f'Volume SMA ({params["volume_sma"]})', color='blue')
        ax5.set_ylabel('Volume', fontsize=16)
        ax5.legend(fontsize=14)
        ax5.grid(True)
        
        # Increase font size for x-axis labels
        plt.xticks(fontsize=14)
        
        plt.tight_layout()
        
        # Save plot with higher DPI for better quality
        plot_path = os.path.join(self.results_dir, f'{data_file}_best_params.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return plot_path
    
    def objective(self, params):
        """Objective function for optimization"""
        try:
            # Convert parameters to dictionary
            param_dict = self.params_to_dict(params)
            
            # Create strategy instance with current parameters
            strategy = CryptoTrendStrategy(param_dict)
            
            # Calculate indicators using strategy
            df = strategy.calculate_indicators(self.current_data.copy())
            
            # Run strategy with current parameters
            trade_log = strategy.run_backtest(df, self.current_symbol)
            
            if not isinstance(trade_log, pd.DataFrame) or trade_log.empty:
                return -1000  # Penalize no trades
            
            # Convert trade log to records and filter out any NaN values
            trades = [trade for trade in trade_log.to_dict('records') if not np.isnan(trade.get('pnl', 0))]
            
            if not trades:
                return -1000  # Penalize if all trades have NaN PnL
            
            # Calculate metrics
            total_profit = sum(trade.get('pnl', 0) for trade in trades)
            num_trades = len(trades)
            win_rate = sum(1 for trade in trades if trade.get('pnl', 0) > 0) / num_trades if num_trades > 0 else 0
            
            # Calculate time between trades
            trade_times = pd.Series([pd.to_datetime(trade['timestamp']) for trade in trades])
            time_diffs = pd.Series([(trade_times[i] - trade_times[i-1]).total_seconds() / 3600 
                                  for i in range(1, len(trade_times))])
            
            min_time_between = float(time_diffs.min()) if not time_diffs.empty else 0
            max_time_between = float(time_diffs.max()) if not time_diffs.empty else 0
            avg_time_between = float(time_diffs.mean()) if not time_diffs.empty else 0
            
            # Calculate Sharpe ratio
            returns = pd.Series([trade.get('pnl', 0) for trade in trades])
            if len(returns) > 1 and returns.std() != 0:
                sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std()
            else:
                sharpe_ratio = 0
            
            # Calculate max drawdown
            cumulative_returns = returns.cumsum()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = cumulative_returns - rolling_max
            max_drawdown = abs(drawdowns.min()) if len(drawdowns) > 0 else 0
            
            # Store metrics and trades
            self.current_metrics = {
                'total_profit': float(total_profit),
                'num_trades': int(num_trades),
                'win_rate': float(win_rate),
                'sharpe_ratio': float(sharpe_ratio),
                'max_drawdown': float(max_drawdown),
                'min_time_between_trades': min_time_between,
                'max_time_between_trades': max_time_between,
                'avg_time_between_trades': avg_time_between,
                'params': param_dict,
                'trades': trades  # Store the trades in metrics
            }
            
            # Return negative combined score (we minimize)
            return -(sharpe_ratio * 0.4 + total_profit * 0.4 + win_rate * 0.2)
            
        except Exception as e:
            return -1000  # Penalize errors
    
    def optimize_single_file(self, data_file):
        """Optimize parameters for a single data file"""
        # Extract symbol from filename
        self.current_symbol = data_file.split('_')[0]
        
        # Get data from pre-loaded storage
        if self.current_symbol not in self.raw_data:
            raise ValueError(f"No data found for symbol {self.current_symbol}")
        
        # Create a copy of the raw data for this optimization run
        self.current_data = self.raw_data[self.current_symbol].copy()
        
        # Store current metrics
        self.current_metrics = {}
        
        # Run optimization
        result = gp_minimize(
            func=self.objective,
            dimensions=self.space,
            n_calls=50,
            n_random_starts=10,
            noise=0.1,
            n_jobs=-1  # Use all available cores for parameter combinations
        )
        
        # Get best parameters and metrics
        best_params = self.params_to_dict(result.x)
        best_metrics = self.current_metrics
        
        # Run final backtest with best parameters
        strategy = CryptoTrendStrategy(best_params)
        df_with_indicators = strategy.calculate_indicators(self.current_data.copy())
        trade_log = strategy.run_backtest(df_with_indicators, self.current_symbol)
        
        # Generate plot
        plot_path = self.plot_results(df_with_indicators, trade_log, best_params, data_file)
        
        # Convert trade log to records and ensure all values are serializable
        trade_records = []
        for trade in trade_log.to_dict('records'):
            serializable_trade = {}
            for key, value in trade.items():
                if isinstance(value, (np.int64, np.int32)):
                    serializable_trade[key] = int(value)
                elif isinstance(value, (np.float64, np.float32)):
                    serializable_trade[key] = float(value)
                elif isinstance(value, pd.Timestamp):
                    serializable_trade[key] = value.isoformat()
                else:
                    serializable_trade[key] = value
            trade_records.append(serializable_trade)
        
        # Convert metrics to serializable format
        serializable_metrics = {}
        for key, value in best_metrics.items():
            if key == 'trades':
                # Convert trades in metrics to serializable format
                serializable_metrics[key] = []
                for trade in value:
                    serializable_trade = {}
                    for k, v in trade.items():
                        if isinstance(v, (np.int64, np.int32)):
                            serializable_trade[k] = int(v)
                        elif isinstance(v, (np.float64, np.float32)):
                            serializable_trade[k] = float(v)
                        elif isinstance(v, pd.Timestamp):
                            serializable_trade[k] = v.isoformat()
                        else:
                            serializable_trade[k] = v
                    serializable_metrics[key].append(serializable_trade)
            else:
                serializable_metrics[key] = value
        
        # Save results
        results = {
            'symbol': self.current_symbol,
            'data_file': data_file,
            'best_params': best_params,
            'metrics': serializable_metrics,
            'trades': trade_records,
            'optimization_history': [
                {
                    'params': self.params_to_dict(x),
                    'score': float(score)
                }
                for x, score in zip(result.x_iters, result.func_vals)
            ],
            'plot_path': plot_path
        }
        
        # Save to JSON with full data file name
        results_path = os.path.join(self.results_dir, f'{data_file}_optimization_results.json')
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        return results
    
    def run_optimization(self):
        """Run optimization for all data files"""
        # Get all CSV files
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]
        
        # Process one file at a time
        all_results = []
        for data_file in data_files:
            try:
                result = self.optimize_single_file(data_file)
                if result is not None:
                    all_results.append(result)
            except Exception as e:
                print(f"Error processing {data_file}: {str(e)}")
        
        # Save combined results
        combined_results = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'results': all_results
        }
        
        combined_path = os.path.join(self.results_dir, 'combined_optimization_results.json')
        with open(combined_path, 'w') as f:
            json.dump(self.convert_to_serializable(combined_results), f, indent=4)
        
        print(f"\nCombined results saved to {combined_path}")

if __name__ == "__main__":
    optimizer = TrendOptimizer()
    optimizer.run_optimization() 
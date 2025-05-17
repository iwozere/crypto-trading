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
import warnings
from src.strats.CryptoTrendingRsiBbStrategy import CryptoTrendingRsiBbStrategy

class RsiBbOptimizer:
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
            Real(30, 70, name='rsi_oversold'),
            Real(30, 70, name='rsi_overbought'),
            Integer(10, 50, name='bb_period'),
            Real(1.5, 3.0, name='bb_std'),
            Integer(10, 50, name='volume_period'),
            Real(1.0, 3.0, name='volume_threshold'),
            Real(0.01, 0.05, name='risk_per_trade'),
            Integer(10, 30, name='atr_period'),
            Real(1.5, 3.0, name='atr_tp_multiplier'),
            Real(0.5, 2.0, name='atr_sl_multiplier')
        ]
        
        # Store current metrics and symbol
        self.current_metrics = {}
        self.current_symbol = None
        
        # Initialize data storage
        self.raw_data = {}
        self.load_all_data()
        
        # Suppress specific warnings
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
        
    def load_all_data(self):
        """Load all data files once during initialization"""
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]
        for data_file in data_files:
            try:
                # Load and process the data
                df = pd.read_csv(os.path.join(self.data_dir, data_file))
                
                # Ensure timestamp is properly formatted and set as index
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Replace zeros with small values to avoid division by zero
                df['close'] = df['close'].replace(0, 0.0001)
                df['high'] = df['high'].replace(0, 0.0001)
                df['low'] = df['low'].replace(0, 0.0001)
                df['volume'] = df['volume'].replace(0, 0.0001)
                
                # Pre-calculate common indicators that don't depend on parameters
                df['returns'] = df['close'].pct_change()
                
                # Store data with full filename as key
                self.raw_data[data_file] = df
                print(f"Loaded data for {data_file}")
            except Exception as e:
                print(f"Error loading {data_file}: {str(e)}")
        
    def params_to_dict(self, params):
        """Convert parameter list to dictionary with proper types"""
        param_types = {
            'rsi_period': int,
            'rsi_oversold': float,
            'rsi_overbought': float,
            'bb_period': int,
            'bb_std': float,
            'volume_period': int,
            'volume_threshold': float,
            'risk_per_trade': float,
            'atr_period': int,
            'atr_tp_multiplier': float,
            'atr_sl_multiplier': float
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
    
    def plot_results(self, df, trade_log, params, data_file):
        """Plot trading results with buy/sell points"""
        # Set figure size to be 4x wider and 3x higher
        plt.rcParams['figure.figsize'] = (60, 30)
        
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, gridspec_kw={'height_ratios': [3, 1, 1, 1]}, sharex=True)
        
        # Plot price and Bollinger Bands
        ax1.plot(df.index, df['close'], label='Price', color='blue', alpha=0.7)
        ax1.plot(df.index, df['bb_high'], label=f'BB High ({params["bb_period"]}, {params["bb_std"]})', color='red', alpha=0.7)
        ax1.plot(df.index, df['bb_mid'], label=f'BB Mid ({params["bb_period"]})', color='orange', alpha=0.7)
        ax1.plot(df.index, df['bb_low'], label=f'BB Low ({params["bb_period"]}, {params["bb_std"]})', color='green', alpha=0.7)
        
        # Debug print trade log info
        print("\nTrade Log Info in plot_results:")
        print(f"Trade log type: {type(trade_log)}")
        print(f"Trade log shape: {trade_log.shape if hasattr(trade_log, 'shape') else 'N/A'}")
        print(f"Trade log columns: {trade_log.columns.tolist() if hasattr(trade_log, 'columns') else 'N/A'}")
        
        # Ensure trade_log is a DataFrame
        if not isinstance(trade_log, pd.DataFrame):
            print("Converting trade_log to DataFrame")
            trade_log = pd.DataFrame(trade_log)
        
        # Reset index if timestamp is the index
        if isinstance(trade_log.index, pd.DatetimeIndex):
            trade_log = trade_log.reset_index()
        
        # Plot buy/sell points
        if not trade_log.empty:
            # Filter buy and sell points
            buy_points = trade_log[trade_log['signal'] == 'buy']
            sell_points = trade_log[trade_log['signal'] == 'sell']
            
            print(f"Number of buy points: {len(buy_points)}")
            print(f"Number of sell points: {len(sell_points)}")
            
            # Plot buy points
            if not buy_points.empty:
                ax1.scatter(buy_points['timestamp'], buy_points['price'], 
                          marker='^', color='green', s=200, label='Buy')
                print("Added buy points to plot")
            
            # Plot sell points
            if not sell_points.empty:
                ax1.scatter(sell_points['timestamp'], sell_points['price'], 
                          marker='v', color='red', s=200, label='Sell')
                print("Added sell points to plot")
        
        ax1.set_title(f'{data_file} Trading Results', fontsize=20)
        ax1.set_ylabel('Price', fontsize=16)
        ax1.legend(fontsize=14)
        ax1.grid(True)
        
        # Plot RSI
        ax2.plot(df.index, df['rsi'], label='RSI', color='purple')
        ax2.axhline(y=params['rsi_oversold'], color='green', linestyle='--', label=f'RSI Oversold ({params["rsi_oversold"]})')
        ax2.axhline(y=params['rsi_overbought'], color='red', linestyle='--', label=f'RSI Overbought ({params["rsi_overbought"]})')
        ax2.set_ylabel('RSI', fontsize=16)
        ax2.legend(fontsize=14)
        ax2.grid(True)
        
        # Plot Volume
        ax3.bar(df.index, df['volume'], label='Volume', color='gray', alpha=0.7)
        ax3.plot(df.index, df['volume_ma'], label=f'Volume MA ({params["volume_period"]})', color='blue')
        ax3.set_ylabel('Volume', fontsize=16)
        ax3.legend(fontsize=14)
        ax3.grid(True)
        
        # Plot OBV
        ax4.plot(df.index, df['obv'], label='OBV', color='purple')
        ax4.set_ylabel('OBV', fontsize=16)
        ax4.legend(fontsize=14)
        ax4.grid(True)
        
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
            strategy = CryptoTrendingRsiBbStrategy(param_dict)
            
            # Calculate indicators using strategy
            df = strategy.calculate_indicators(self.current_data.copy())
            
            # Run strategy with current parameters
            trade_log = strategy.run_backtest(df, self.current_symbol)
            
            if not isinstance(trade_log, pd.DataFrame) or trade_log.empty:
                return 1000  # Penalize no trades with a large positive value
            
            # Convert trade log to records and filter out any NaN values
            trades = [trade for trade in trade_log.to_dict('records') if not np.isnan(trade.get('pnl', 0))]
            
            if not trades:
                return 1000  # Penalize if all trades have NaN PnL
            
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
                'trades': trades
            }
            
            # Print optimization progress
            print(f"\nOptimization Progress:")
            print(f"Parameters: {param_dict}")
            print(f"Total Profit: {total_profit:.2f}%")
            print(f"Number of Trades: {num_trades}")
            print(f"Win Rate: {win_rate:.2%}")
            print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
            print(f"Max Drawdown: {max_drawdown:.2f}%")
            
            # Return negative combined score (we minimize)
            return -(total_profit)
            
        except Exception as e:
            print(f"Error in objective function: {str(e)}")
            return 1000  # Penalize errors with a large positive value
    
    def optimize_single_file(self, data_file):
        """Optimize parameters for a single data file"""
        print(f"\nOptimizing for {data_file}...")
        
        # Extract symbol from filename
        self.current_symbol = data_file.split('_')[0]
        
        # Get data from pre-loaded storage using full filename
        if data_file not in self.raw_data:
            raise ValueError(f"No data found for file {data_file}")
        
        # Create a copy of the raw data for this optimization run
        self.current_data = self.raw_data[data_file].copy()
        
        # Store current metrics
        self.current_metrics = {}
        
        # Run optimization with reduced number of iterations for faster testing
        result = gp_minimize(
            func=self.objective,
            dimensions=self.space,
            n_calls=20,  # Reduced from 50
            n_random_starts=5,  # Reduced from 10
            noise=0.1,
            n_jobs=-1,
            verbose=True
        )
        
        print(f"\nOptimization completed for {data_file}")
        print(f"Best parameters: {self.params_to_dict(result.x)}")
        print(f"Best score: {-result.fun:.2f}")
        
        return self.save_results(data_file, result)
    
    def run_optimization(self):
        """Run optimization for all data files"""
        print("Starting optimization process...")
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]
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

    def save_results(self, data_file, result):
        """Save optimization results to file (trending style)"""
        try:
            os.makedirs(self.results_dir, exist_ok=True)
            symbol = self.current_symbol
            best_params = self.params_to_dict(result.x)
            best_metrics = self.current_metrics

            # Run final backtest with best parameters
            strategy = CryptoTrendingRsiBbStrategy(best_params)
            df_with_indicators = strategy.calculate_indicators(self.current_data.copy())
            trade_log = strategy.run_backtest(df_with_indicators, symbol)

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
                'symbol': symbol,
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

            print(f"\nResults saved to {results_path}")
            print(f"Plot saved to {plot_path}")
            return results
        except Exception as e:
            print(f"Error saving results: {str(e)}")
            return None

if __name__ == "__main__":
    optimizer = RsiBbOptimizer()
    optimizer.run_optimization() 
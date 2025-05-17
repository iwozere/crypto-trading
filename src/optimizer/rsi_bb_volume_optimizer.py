import os
import json
import pandas as pd
import numpy as np
from skopt import gp_minimize
from skopt.space import Real, Integer
from skopt.utils import use_named_args
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy
import backtrader as bt
import matplotlib.gridspec as gridspec
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from datetime import datetime
from src.optimizer.base_optimizer import BaseOptimizer

class RsiBBVolumeOptimizer(BaseOptimizer):
    def __init__(self, initial_capital=1000.0, commission=0.001):
        super().__init__(initial_capital, commission)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Set up plotting style
        plt.style.use('default')
        sns.set_theme(style="darkgrid")
        plt.rcParams['figure.figsize'] = (15, 10)
        plt.rcParams['font.size'] = 10
        
        # Define parameter space for optimization
        self.space = [
            Integer(7, 21, name='rsi_period'),
            Integer(15, 40, name='boll_period'),
            Real(1.5, 3.5, name='boll_devfactor'),
            Integer(10, 25, name='atr_period'),
            Integer(15, 40, name='vol_ma_period'),
            Real(1.5, 4.0, name='tp_atr_mult'),
            Real(0.8, 2.5, name='sl_atr_mult'),
            Real(25, 35, name='rsi_oversold'),
            Real(65, 75, name='rsi_overbought')
        ]
        
        # Store current metrics and data
        self.current_metrics = {}
        self.current_data = None
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
                
                # Ensure all required columns are present and in correct format
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in required_columns:
                    if col not in df.columns:
                        raise ValueError(f"Missing required column: {col}")
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Store data with full filename as key
                self.raw_data[data_file] = df
                print(f"Loaded data for {data_file}")
                print(f"Data shape: {df.shape}")
                print(f"Columns: {df.columns.tolist()}")
                print(f"Date range: {df.index.min()} to {df.index.max()}")
            except Exception as e:
                print(f"Error loading {data_file}: {str(e)}")
                raise
    
    def params_to_dict(self, params):
        """Convert parameter list to dictionary with proper types"""
        param_types = {
            'rsi_period': int,
            'boll_period': int,
            'boll_devfactor': float,
            'atr_period': int,
            'vol_ma_period': int,
            'tp_atr_mult': float,
            'sl_atr_mult': float,
            'rsi_oversold': float,
            'rsi_overbought': float
        }
        return {name: param_types[name](value) for name, value in zip([p.name for p in self.space], params)}
    
    def run_backtest(self, data, params):
        """Run backtest with given parameters"""
        cerebro = bt.Cerebro()
        
        # Add data with proper column mapping
        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # Use index as datetime
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1  # No open interest data
        )
        cerebro.adddata(data_feed)
               
        # Add strategy with parameters
        cerebro.addstrategy(RSIBollVolumeATRStrategy, **params)
        
        # Set initial capital
        cerebro.broker.setcash(self.initial_capital)
        
        # Set commission
        cerebro.broker.setcommission(0.001)  # 0.1% commission
        
        cerebro.broker.set_slippage_perc(perc=0.001)  # 0.1% slippage
        
        # Use default broker settings
        cerebro.broker.set_checksubmit(False)  # Don't check if we can submit orders
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')

        # Run backtest
        results = cerebro.run()
        
        # Get analyzer results
        sharpe = results[0].analyzers.sharpe.get_analysis()
        drawdown = results[0].analyzers.drawdown.get_analysis()
        trades = results[0].analyzers.trades.get_analysis()
        
        return {
            'strategy': results[0],
            'sharpe': sharpe,
            'drawdown': drawdown,
            'trades': trades
        }
    
    def objective(self, params):
        """Objective function for optimization"""
        try:
            # Convert parameters to dictionary
            param_dict = self.params_to_dict(params)
            
            # Run backtest
            results = self.run_backtest(self.current_data, param_dict)
            
            # Get metrics from analyzer results
            trades = results['trades']
            sharpe = results['sharpe']
            drawdown = results['drawdown']
            
            # Calculate metrics with proper error handling
            total_trades = trades.get('total', {}).get('total', 0)
            if total_trades == 0:
                print("No trades executed")
                return 1000  # Penalize no trades
            
            # Calculate win rate
            won_trades = trades.get('won', {}).get('total', 0)
            win_rate = won_trades / total_trades if total_trades > 0 else 0
            
            # Calculate PnL metrics with proper type handling
            pnl = trades.get('pnl', {})
            net_profit = float(pnl.get('net', {}).get('total', 0))
            gross_loss = abs(float(pnl.get('lost', {}).get('total', 1)))
            profit_factor = net_profit / gross_loss if gross_loss != 0 else 0
            
            # Get drawdown and Sharpe ratio
            max_drawdown = float(drawdown.get('max', {}).get('drawdown', 0) or 0)
            sharpe_ratio = float(sharpe.get('sharperatio', 0) or 0)
            
            # Calculate portfolio growth percentage
            final_value = results['strategy'].broker.getvalue()
            portfolio_growth = ((final_value - self.initial_capital) / self.initial_capital) * 100
            
            # Calculate additional metrics
            avg_trade = net_profit / total_trades if total_trades > 0 else 0
            max_consecutive_wins = trades.get('streak', {}).get('won', {}).get('longest', 0)
            max_consecutive_losses = trades.get('streak', {}).get('lost', {}).get('longest', 0)
            
            # Store metrics
            self.current_metrics = {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'avg_trade': avg_trade,
                'max_consecutive_wins': max_consecutive_wins,
                'max_consecutive_losses': max_consecutive_losses,
                'total_profit': net_profit,
                'portfolio_growth': portfolio_growth,
                'final_value': final_value,
                'params': param_dict
            }
            
            # Print optimization progress
            print(f"\nOptimization Progress:")
            print(f"Parameters: {param_dict}")
            print(f"Total Trades: {total_trades}")
            print(f"Win Rate: {win_rate:.2%}")
            print(f"Profit Factor: {profit_factor:.2f}")
            print(f"Total Profit: ${net_profit:.2f}")
            print(f"Portfolio Growth: {portfolio_growth:.2f}%")
            print(f"Final Value: ${final_value:.2f}")
            print(f"Max Drawdown: {max_drawdown:.2f}%")
            print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
            print(f"Avg Trade: {avg_trade:.2f}")
            print(f"Max Consecutive Wins: {max_consecutive_wins}")
            print(f"Max Consecutive Losses: {max_consecutive_losses}")
            
            # Calculate composite score
            # Higher values are worse, so we negate the score
            score = -net_profit
            #score = -(
            #    0.3 * sharpe_ratio +  # 30% weight to Sharpe ratio
            #    0.25 * profit_factor +  # 25% weight to profit factor
            #    0.2 * win_rate +      # 20% weight to win rate
            #    0.15 * (net_profit / self.initial_capital) -    # 15% weight to return
            #    0.1 * (max_drawdown / 100)  # 10% penalty for drawdown
            #)
            
            # Add penalties for undesirable conditions
            if total_trades < 10:  # Penalize too few trades
                score += 100
            if win_rate < 0.3:  # Penalize very low win rates
                score += 50
            if max_consecutive_losses > 5:  # Penalize long losing streaks
                score += 25
            if profit_factor < 1.0:  # Penalize negative profit factors
                score += 75
                
            return score
            
        except Exception as e:
            print(f"Error in objective function: {str(e)}")
            print(f"Error details: {type(e).__name__}")
            import traceback
            print(traceback.format_exc())
            return 1000  # Return a high score (bad) in case of error
    
    def optimize_single_file(self, data_file):
        """Optimize parameters for a single data file"""
        print(f"\nOptimizing for {data_file}...")
        
        # Extract symbol from filename
        self.current_symbol = data_file.split('_')[0]
        
        # Get data from pre-loaded storage
        if data_file not in self.raw_data:
            raise ValueError(f"No data found for file {data_file}")
        
        # Create a copy of the raw data for this optimization run
        self.current_data = self.raw_data[data_file].copy()
        
        # Validate data
        if len(self.current_data) < 100:  # Minimum required data points
            print(f"Warning: Insufficient data points in {data_file}. Skipping...")
            return None
            
        # Check for missing or invalid values
        if self.current_data.isnull().any().any():
            print(f"Warning: Found missing values in {data_file}. Cleaning data...")
            self.current_data = self.current_data.fillna(method='ffill').fillna(method='bfill')
            
        # Store current metrics
        self.current_metrics = {}
        
        try:
            # Run optimization with reduced iterations for faster testing
            result = gp_minimize(
                func=self.objective,
                dimensions=self.space,
                n_calls=100,  # Reduced from 50
                n_random_starts=42,  # Reduced from 10
                noise=0.1,
                n_jobs=1,  # Use all available CPU cores
                verbose=False
            )
            
            print(f"\nOptimization completed for {data_file}")
            print(f"Best parameters: {self.params_to_dict(result.x)}")
            print(f"Best score: {-result.fun:.2f}")
            
            # Save results regardless of score
            return self.save_results(data_file, result)
            
        except Exception as e:
            print(f"Error during optimization for {data_file}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def plot_results(self, data, trades_df, params, data_file):
        """Plot the results of the optimization"""
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(60, 30))
        
        # Create subplots
        gs = gridspec.GridSpec(4, 1, height_ratios=[3, 1, 1, 1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        ax4 = plt.subplot(gs[3], sharex=ax1)
        
        # Calculate Bollinger Bands
        bb = BollingerBands(close=data['close'], window=params['boll_period'], window_dev=params['boll_devfactor'])
        bb_high = bb.bollinger_hband()
        bb_mid = bb.bollinger_mavg()
        bb_low = bb.bollinger_lband()
        
        # Plot price and Bollinger Bands
        ax1.plot(data.index, data['close'], label='Price', color='white', linewidth=2)
        ax1.plot(data.index, bb_high, label=f'BB High ({params["boll_period"]}, {params["boll_devfactor"]})', color='red', alpha=0.7, linewidth=1)
        ax1.plot(data.index, bb_mid, label=f'BB Mid ({params["boll_period"]})', color='yellow', alpha=0.7, linewidth=1)
        ax1.plot(data.index, bb_low, label=f'BB Low ({params["boll_period"]}, {params["boll_devfactor"]})', color='green', alpha=0.7, linewidth=1)
        
        # Plot trades
        if not trades_df.empty:
            # Plot entry (buy) points
            ax1.scatter(trades_df['entry_time'], trades_df['entry_price'], color='green', marker='^', s=200, label='Buy')
            # Plot exit (sell) points
            ax1.scatter(trades_df['exit_time'], trades_df['exit_price'], color='red', marker='v', s=200, label='Sell')
        
        # Plot RSI
        rsi = RSIIndicator(close=data['close'], window=params['rsi_period']).rsi()
        ax2.plot(data.index, rsi, label=f'RSI ({params["rsi_period"]})', color='cyan', linewidth=2)
        ax2.axhline(y=params['rsi_overbought'], color='red', linestyle='--', alpha=0.5)
        ax2.axhline(y=params['rsi_oversold'], color='green', linestyle='--', alpha=0.5)
        ax2.fill_between(data.index, params['rsi_overbought'], 100, color='red', alpha=0.1)
        ax2.fill_between(data.index, 0, params['rsi_oversold'], color='green', alpha=0.1)
        
        # Plot volume
        ax3.bar(data.index, data['volume'], label='Volume', color='blue', alpha=0.7)
        vol_ma = data['volume'].rolling(window=params['vol_ma_period']).mean()
        ax3.plot(data.index, vol_ma, label=f'Volume MA ({params["vol_ma_period"]})', color='yellow', linewidth=2)
        
        # Calculate and plot equity curve
        if not trades_df.empty:
            # Calculate cumulative returns
            trades_df['returns'] = trades_df['pnl'] / 100  # Convert percentage to decimal
            cumulative_returns = (1 + trades_df['returns']).cumprod()
            initial_equity = self.initial_capital
            equity_curve = initial_equity * cumulative_returns
            
            # Plot equity curve
            ax4.plot(trades_df['exit_time'], equity_curve, label='Equity Curve', color='green', linewidth=2)
            
            # Add drawdown visualization
            rolling_max = equity_curve.expanding().max()
            drawdown = (equity_curve - rolling_max) / rolling_max * 100
            ax4.fill_between(trades_df['exit_time'], drawdown, 0, color='red', alpha=0.3, label='Drawdown')
            
            # Add horizontal line at initial capital
            ax4.axhline(y=initial_equity, color='white', linestyle='--', alpha=0.5, label='Initial Capital')
        
        # Set titles and labels
        ax1.set_title(f'Trading Results - {data_file}', fontsize=20)
        ax1.set_ylabel('Price', fontsize=16)
        ax2.set_ylabel('RSI', fontsize=16)
        ax3.set_ylabel('Volume', fontsize=16)
        ax4.set_ylabel('Equity', fontsize=16)
        ax4.set_xlabel('Date', fontsize=16)
        
        # Set legend
        ax1.legend(loc='upper left', fontsize=12)
        ax2.legend(loc='upper left', fontsize=12)
        ax3.legend(loc='upper left', fontsize=12)
        ax4.legend(loc='upper left', fontsize=12)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save plot
        plot_path = os.path.join(self.results_dir, f'{data_file}_plot.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return plot_path

    def save_results(self, data_file, result):
        """Save optimization results to file"""
        try:
            print(f"\nSaving results for {data_file}...")
            os.makedirs(self.results_dir, exist_ok=True)
            
            # Get best parameters
            best_params = self.params_to_dict(result.x)
            print(f"Best parameters: {best_params}")
            
            # Run final backtest with best parameters
            print("Running final backtest...")
            results = self.run_backtest(self.current_data, best_params)
            
            # Get trade information
            print("Getting trade information...")
            trades_df = results['strategy'].get_trades()
            print(f"Number of trades: {len(trades_df)}")
            
            # Calculate additional metrics
            total_trades = len(trades_df) if not trades_df.empty else 0
            winning_trades = len(trades_df[trades_df['pnl'] > 0]) if not trades_df.empty else 0
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calculate profit metrics
            total_profit = trades_df['pnl'].sum() if not trades_df.empty else 0
            avg_profit = trades_df['pnl'].mean() if not trades_df.empty else 0
            max_profit = trades_df['pnl'].max() if not trades_df.empty else 0
            max_loss = trades_df['pnl'].min() if not trades_df.empty else 0
            
            # Get drawdown and Sharpe ratio from analyzer results with safe handling
            print("Getting analyzer results...")
            drawdown = results['drawdown']
            sharpe = results['sharpe']
            
            # Safely get values with defaults
            max_drawdown = float(drawdown.get('max', {}).get('drawdown', 0) or 0)
            sharpe_ratio = float(sharpe.get('sharperatio', 0) or 0)
            
            # Get trades analysis
            trades = results['trades']
            
            # Calculate portfolio growth percentage
            final_value = results['strategy'].broker.getvalue()
            portfolio_growth = ((final_value - self.initial_capital) / self.initial_capital) * 100
            
            # Calculate additional metrics
            avg_trade = total_profit / total_trades if total_trades > 0 else 0
            max_consecutive_wins = trades.get('streak', {}).get('won', {}).get('longest', 0)
            max_consecutive_losses = trades.get('streak', {}).get('lost', {}).get('longest', 0)
            
            # Prepare metrics dictionary
            metrics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': float(win_rate),
                'total_profit': float(total_profit),
                'avg_profit': float(avg_profit),
                'max_profit': float(max_profit),
                'max_loss': float(max_loss),
                'max_drawdown': float(max_drawdown),
                'sharpe_ratio': float(sharpe_ratio),
                'portfolio_growth': float(portfolio_growth),
                'final_value': float(final_value)
            }
            print(f"Metrics calculated: {metrics}")
            
            # Generate plot
            print("Generating plot...")
            plot_path = self.plot_results(self.current_data, trades_df, best_params, data_file)
            print(f"Plot generated at: {plot_path}")
            
            # Convert trades DataFrame to records with proper timestamp handling
            trades_records = []
            if not trades_df.empty:
                for _, trade in trades_df.iterrows():
                    trade_dict = {}
                    for col in trades_df.columns:
                        value = trade[col]
                        if pd.isna(value):
                            trade_dict[col] = None
                        elif isinstance(value, (pd.Timestamp, datetime)):
                            trade_dict[col] = value.isoformat()
                        elif isinstance(value, (np.integer, np.floating)):
                            trade_dict[col] = float(value)
                        else:
                            trade_dict[col] = value
                    trades_records.append(trade_dict)
            
            # Prepare optimization history
            optimization_history = []
            for x, score in zip(result.x_iters, result.func_vals):
                try:
                    param_dict = self.params_to_dict(x)
                    optimization_history.append({
                        'params': param_dict,
                        'score': float(score)
                    })
                except Exception as e:
                    print(f"Warning: Could not process optimization history entry: {e}")
                    continue
            
            # Prepare results dictionary
            results_dict = {
                'timestamp': datetime.now().isoformat(),
                'data_file': data_file,
                'best_params': best_params,
                'metrics': metrics,
                'best_score': float(-result.fun),
                'trades': trades_records,
                'optimization_history': optimization_history,
                'plot_path': plot_path
            }
            
            # Save to JSON with custom encoder
            results_path = os.path.join(self.results_dir, f'{data_file}_optimization_results.json')
            print(f"Saving results to: {results_path}")
            
            # Calculate sqn_pct and cagr using BaseOptimizer utilities
            sqn_pct = None
            cagr = None
            try:
                trades_log = results['strategy'].get_trades() if hasattr(results['strategy'], 'get_trades') else []
                if trades_log and len(trades_log) > 1:
                    trades_df = trades_log if isinstance(trades_log, pd.DataFrame) else pd.DataFrame(trades_log)
                    sqn_pct = BaseOptimizer.calculate_sqn_pct(trades_df)
                    if 'entry_time' in trades_df.columns and 'exit_time' in trades_df.columns:
                        trades_df = trades_df.dropna(subset=['entry_time', 'exit_time'])
                        if not trades_df.empty:
                            cagr = BaseOptimizer.calculate_cagr(self.initial_capital, final_value, trades_df['entry_time'].iloc[0], trades_df['exit_time'].iloc[-1])
            except Exception:
                pass
            
            try:
                json_str = json.dumps(results_dict, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                with open(results_path, 'w') as f: f.write(json_str)
            except Exception as e:
                print(f"Error during JSON serialization: {e}. Trying to save simplified.")
                simplified_dict = {k: v for k, v in results_dict.items() if k not in ['trades_log', 'optimization_history']}
                simplified_dict['error_in_serialization'] = str(e)
                json_str = json.dumps(simplified_dict, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                with open(results_path, 'w') as f: f.write(json_str)
                print("Saved simplified results due to serialization error.")
            
            print(f"\nResults saved to {results_path}")
            print(f"Plot saved to {plot_path}")
            return results_dict
            
        except Exception as e:
            print(f"Error saving results: {str(e)}")
            import traceback
            print("Full traceback:")
            print(traceback.format_exc())
            return None
    
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
            json.dump(combined_results, f, indent=4)
        print(f"\nCombined results saved to {combined_path}")

if __name__ == "__main__":
    # Create optimizer with custom initial capital
    optimizer = RsiBBVolumeOptimizer(initial_capital=1000.0, commission=0.001)  # $1,000 initial capital
    optimizer.run_optimization()

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
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
    
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
        self.log_message(f"\nOptimizing for {data_file}...", level='info')
        self.current_symbol = data_file.split('_')[0]
        if data_file not in self.raw_data:
            raise ValueError(f"No data found for file {data_file}")
        self.current_data = self.raw_data[data_file].copy()
        if len(self.current_data) < 100:
            self.log_message(f"Warning: Insufficient data points in {data_file}. Skipping...", level='info')
            return None
        if self.current_data.isnull().any().any():
            self.log_message(f"Warning: Found missing values in {data_file}. Cleaning data...", level='info')
            self.current_data = self.current_data.fillna(method='ffill').fillna(method='bfill')
        self.current_metrics = {}
        try:
            result = gp_minimize(
                func=self.objective,
                dimensions=self.space,
                n_calls=100,
                n_random_starts=42,
                noise=0.1,
                n_jobs=1,
                verbose=False
            )
            self.log_message(f"\nOptimization completed for {data_file}", level='info')
            best_params = self.params_to_dict(result.x)
            self.log_message(f"Best parameters: {best_params}", level='info')
            self.log_message(f"Best score: {-result.fun:.2f}", level='info')
            # Run final backtest with best params
            final_backtest_results = self.run_backtest(self.current_data, best_params)
            trades_df = final_backtest_results['strategy'].get_trades() if final_backtest_results and 'strategy' in final_backtest_results else pd.DataFrame()
            plot_path = self.plot_results(self.current_data, trades_df, best_params, data_file)
            return self.save_results(
                data_file=data_file,
                best_params=best_params,
                metrics=self.current_metrics,
                trades_df=trades_df,
                optimization_result=result,
                plot_path=plot_path,
                strategy_name='RSIBollVolumeATRStrategy'
            )
        except Exception as e:
            self.log_message(f"Error during optimization for {data_file}: {str(e)}", level='error')
            import traceback
            self.log_message(str(traceback.format_exc()), level='error')
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

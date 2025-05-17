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
from src.strats.rsi_bb_atr_strategy import MeanReversionRSBBATRStrategy
import backtrader as bt
import matplotlib.gridspec as gridspec
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from datetime import datetime
from src.optimizer.base_optimizer import BaseOptimizer

class MeanReversionRSBBATROptimizer(BaseOptimizer):
    def __init__(self, initial_capital=1000.0, commission=0.001):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.initial_capital = initial_capital
        self.commission = commission
        plt.style.use('default')
        sns.set_theme(style="darkgrid")
        plt.rcParams['figure.figsize'] = (15, 10)
        plt.rcParams['font.size'] = 10
        
        self.space = [
            Integer(10, 50, name='bb_period'),
            Real(1.5, 3.5, name='bb_devfactor'),
            Integer(7, 28, name='rsi_period'),
            Real(20.0, 40.0, name='rsi_oversold'),
            Real(60.0, 80.0, name='rsi_overbought'),
            Real(45.0, 55.0, name='rsi_mid_level'),
            Integer(7, 28, name='atr_period'),
            Real(1.0, 3.0, name='tp_atr_mult'),
            Real(0.5, 2.0, name='sl_atr_mult'),
            Integer(0, 1, name='check_rsi_slope')
        ]
        
        self.current_metrics = {}
        self.current_data = None
        self.current_symbol = None
        self.raw_data = {}
        self.load_all_data()
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
        warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    def load_all_data(self):
        """Load all data files once during initialization"""
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]
        for data_file in data_files:
            try:
                df = pd.read_csv(os.path.join(self.data_dir, data_file))
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in required_columns:
                    if col not in df.columns:
                        if col == 'volume':
                            self.log_message(f"Warning: 'volume' column missing in {data_file}. Creating dummy 'volume' column with zeros.")
                            df['volume'] = 0 
                        else:
                            raise ValueError(f"Missing required column: {col} in {data_file}")
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df.sort_index(inplace=True) 
                if df.isnull().any().any():
                    self.log_message(f"Warning: NaN values found in {data_file} after loading. Forward-filling and back-filling.")
                    df.ffill(inplace=True)
                    df.bfill(inplace=True)
                
                if df.isnull().any().any():
                    self.log_message(f"Error: NaN values persist in {data_file} after fill. Skipping.")
                    continue

                self.raw_data[data_file] = df
                self.log_message(f"Loaded data for {data_file}, shape: {df.shape}, date range: {df.index.min()} to {df.index.max()}")
            except Exception as e:
                self.log_message(f"Error loading {data_file}: {str(e)}")
    
    def log_message(self, message):
        print(f"[{datetime.now().isoformat()}] {message}")
    
    def params_to_dict(self, params):
        param_names = [p.name for p in self.space]
        param_dict = dict(zip(param_names, params))
        
        typed_param_dict = {}
        for name, value in param_dict.items():
            if name in ['bb_period', 'rsi_period', 'atr_period']:
                typed_param_dict[name] = int(value)
            elif name == 'check_rsi_slope':
                typed_param_dict[name] = bool(int(value))
            elif name in ['bb_devfactor', 'rsi_oversold', 'rsi_overbought', 'rsi_mid_level', 'tp_atr_mult', 'sl_atr_mult']:
                typed_param_dict[name] = float(value)
            else:
                 typed_param_dict[name] = value 
        return typed_param_dict
    
    def run_backtest(self, data, params):
        cerebro = bt.Cerebro()
        if not isinstance(data.index, pd.DatetimeIndex):
            self.log_message("Error: Data for backtest must have a DatetimeIndex.")
            return None
        expected_cols = ['open', 'high', 'low', 'close', 'volume'] 
        if not all(col in data.columns for col in expected_cols):
            self.log_message(f"Error: Data missing one of required columns: {expected_cols}. Check load_all_data.")
            return None

        data_feed = bt.feeds.PandasData(
            dataname=data.copy(),
            datetime=None, open='open', high='high', low='low', close='close', volume='volume',
            openinterest=-1
        )
        
        cerebro.adddata(data_feed)
        cerebro.addstrategy(MeanReversionRSBBATRStrategy, **params)
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)
        cerebro.broker.set_checksubmit(False)  # Don't check if we can submit orders
        
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0, timeframe=bt.TimeFrame.Days, compression=1, annualize=True)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
        
        try:
            results = cerebro.run()
            if not results:
                self.log_message(f"Backtest with params {params} did not yield valid results object.")
                return None
            
            # Get analyzer results
            sharpe = results[0].analyzers.sharpe.get_analysis()
            drawdown = results[0].analyzers.drawdown.get_analysis()
            trades = results[0].analyzers.trades.get_analysis()
            sqn = results[0].analyzers.sqn.get_analysis()
            annual_return = results[0].analyzers.annual_return.get_analysis()

            return {
                'strategy_instance': results[0],
                'sharpe': sharpe,
                'drawdown': drawdown,
                'sqn': sqn,
                'annual_return': annual_return,
                'trades': trades
            }            
        except Exception as e:
            self.log_message(f"Error during backtest run for params {params}: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
            return None

    
    def objective(self, params):
        param_dict = self.params_to_dict(params)
        backtest_results = self.run_backtest(self.current_data.copy(), param_dict)
        
        if backtest_results is None:
            self.log_message(f"Backtest failed for params {param_dict}, returning high penalty.")
            return 1000.0 

        trades_analysis = backtest_results.get('trades', {})
        sharpe_analysis = backtest_results.get('sharpe', {})
        drawdown_analysis = backtest_results.get('drawdown', {})
        sqn_analysis = backtest_results.get('sqn', {})

        total_trades = trades_analysis.get('total', {}).get('total', 0)
        if total_trades < 5:
            #self.log_message(f"Penalizing due to low trade count: {total_trades} for params {param_dict}")
            return 500.0 - total_trades * 10 

        net_profit = float(trades_analysis.get('pnl', {}).get('net', {}).get('total', 0.0))
        objective_score = -net_profit

        max_drawdown_pct = float(drawdown_analysis.get('max', {}).get('drawdown', 100.0))
        if max_drawdown_pct > 35: 
            objective_score += (max_drawdown_pct - 35) * 10 

        sharpe_ratio = float(sharpe_analysis.get('sharperatio', -5.0) if sharpe_analysis.get('sharperatio') is not None else -5.0)
        if sharpe_ratio < 0.1:
             objective_score += (0.1 - sharpe_ratio) * 1000 

        sqn_val = float(sqn_analysis.get('sqn', -5.0) if sqn_analysis.get('sqn') is not None else -5.0)
        if sqn_val < 1.0:
            objective_score += (1.0 - sqn_val) * 200

        final_value = backtest_results['strategy_instance'].broker.getvalue()
        portfolio_growth = ((final_value - self.initial_capital) / self.initial_capital) * 100
        win_rate = trades_analysis.get('won', {}).get('total', 0) / total_trades if total_trades > 0 else 0
        gross_profit = trades_analysis.get('won', {}).get('pnl', {}).get('total', 0)
        gross_loss = abs(trades_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
        profit_factor_val = gross_profit / gross_loss if gross_loss > 0 else 0

        # Calculate sqn_pct and cagr using BaseOptimizer utilities
        sqn_pct = None
        cagr = None
        try:
            trades_log = backtest_results['strategy_instance'].trades_log if hasattr(backtest_results['strategy_instance'], 'trades_log') else []
            if trades_log and len(trades_log) > 1:
                import pandas as pd
                trades_df = pd.DataFrame(trades_log)
                sqn_pct = BaseOptimizer.calculate_sqn_pct(trades_df)
                if 'entry_dt' in trades_df.columns and 'exit_dt' in trades_df.columns:
                    trades_df = trades_df.dropna(subset=['entry_dt', 'exit_dt'])
                    if not trades_df.empty:
                        cagr = BaseOptimizer.calculate_cagr(self.initial_capital, final_value, trades_df['entry_dt'].iloc[0], trades_df['exit_dt'].iloc[-1])
        except Exception:
            pass

        self.current_metrics = {
            'total_trades': total_trades, 
            'win_rate': win_rate, 
            'profit_factor': profit_factor_val,
            'max_drawdown_pct': max_drawdown_pct, 
            'sharpe_ratio': sharpe_ratio, 
            'sqn': sqn_val,
            'sqn_pct': sqn_pct,
            'cagr': cagr,
            'net_profit': net_profit,
            'portfolio_growth_pct': portfolio_growth,
            'final_value': final_value, 
            'params': param_dict
        }
        #self.log_message(f"Params: {param_dict} -> Score: {objective_score:.2f}, NetProfit%: {net_profit_pct:.2f}, Trades: {total_trades}, Sharpe: {sharpe_ratio:.2f}, DD: {max_drawdown_pct:.2f}%, SQN: {sqn_val:.2f}")
        return float(-net_profit)
    
    def optimize_single_file(self, data_file):
        self.log_message(f"\nOptimizing {data_file} for MeanReversionRSBBATRStrategy...")
        self.current_symbol = data_file.split('_')[0]
        
        
        if data_file not in self.raw_data:
            self.log_message(f"Error: No data for {data_file}.")
            return None
        
        self.current_data = self.raw_data[data_file].copy()
        
        max_period_param = max(self.space[i].low for i, p_name in enumerate([p.name for p in self.space]) 
                               if p_name in ['bb_period', 'rsi_period', 'atr_period'])
        min_data_len = max(max_period_param * 2, 100)

        if len(self.current_data) < min_data_len:
            self.log_message(f"Warning: Insufficient data ({len(self.current_data)} < {min_data_len}) in {data_file}. Skipping.")
            return None
        
        self.current_metrics = {} 
        try:
            result = gp_minimize(
                func=self.objective, 
                dimensions=self.space,
                n_calls=100, 
                n_random_starts=20, 
                noise=0.01, 
                n_jobs=-1, 
                verbose=False, 
                acq_func="EI")
            
            self.log_message(f"\nOptimization completed for {data_file}")
            best_params_values = result.x
            best_score = result.fun
            
            final_metrics_for_best_params = self.current_metrics 
            if not final_metrics_for_best_params or self.params_to_dict(best_params_values) != final_metrics_for_best_params.get('params'):
                self.log_message("Re-evaluating with best skopt params for consistent metrics.")
                _ = self.objective(best_params_values) 
                final_metrics_for_best_params = self.current_metrics
            
            self.log_message(f"Best params for {data_file}: {final_metrics_for_best_params.get('params')}")
            self.log_message(f"Best score: {best_score:.2f}. Metrics: {final_metrics_for_best_params}")
            return self.save_results(data_file, result, final_metrics_for_best_params)
        except Exception as e:
            self.log_message(f"Error during optimization for {data_file}: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
            return None
    
    def plot_results(self, data_df: pd.DataFrame, trades_df: pd.DataFrame, params: dict, data_file_name: str):
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(60, 30))
        gs = gridspec.GridSpec(4, 1, height_ratios=[3, 1, 1, 1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        ax4 = plt.subplot(gs[3], sharex=ax1)

        # Price and Bollinger Bands
        ax1.plot(data_df.index, data_df['close'], label='Price', color='white', linewidth=2)
        bb_period = params.get('bb_period', 20)
        bb_devfactor = params.get('bb_devfactor', 2.0)
        bb_indicator = BollingerBands(close=data_df['close'], window=bb_period, window_dev=bb_devfactor, fillna=False)
        ax1.plot(data_df.index, bb_indicator.bollinger_hband(), label=f'BB Top ({bb_period},{bb_devfactor})', color='cyan', linestyle='--', alpha=0.7, linewidth=1)
        ax1.plot(data_df.index, bb_indicator.bollinger_lband(), label=f'BB Low ({bb_period},{bb_devfactor})', color='cyan', linestyle='--', alpha=0.7, linewidth=1)
        ax1.plot(data_df.index, bb_indicator.bollinger_mavg(), label=f'BB Mid ({bb_period})', color='blue', linestyle=':', alpha=0.6, linewidth=1)
        ax1.fill_between(data_df.index, bb_indicator.bollinger_lband(), bb_indicator.bollinger_hband(), color='cyan', alpha=0.1)

        # Plot only long trades
        if not trades_df.empty:
            trades_df_plot = trades_df.copy()
            if 'entry_dt' in trades_df_plot.columns: trades_df_plot['entry_dt'] = pd.to_datetime(trades_df_plot['entry_dt'])
            if 'exit_dt' in trades_df_plot.columns: trades_df_plot['exit_dt'] = pd.to_datetime(trades_df_plot['exit_dt'])
            long_trades = trades_df_plot[trades_df_plot['direction'] == 'long']
            if not long_trades.empty:
                ax1.scatter(long_trades['entry_dt'], long_trades['entry_price'], color='lime', marker='^', s=200, label='Long Entry', zorder=5)
                valid_exits = long_trades.dropna(subset=['exit_dt', 'exit_price'])
                if not valid_exits.empty:
                    ax1.scatter(valid_exits['exit_dt'], valid_exits['exit_price'], color='red', marker='v', s=200, label='Long Exit', zorder=5)
        ax1.set_ylabel('Price / BB', fontsize=12)

        # RSI
        rsi_period = params.get('rsi_period', 14)
        rsi_oversold = params.get('rsi_oversold', 30)
        rsi_overbought = params.get('rsi_overbought', 70)
        rsi_mid_level = params.get('rsi_mid_level', 50)
        rsi_indicator = RSIIndicator(close=data_df['close'], window=rsi_period, fillna=False).rsi()
        ax2.plot(data_df.index, rsi_indicator, label=f'RSI ({rsi_period})', color='cyan', linewidth=2)
        ax2.axhline(y=rsi_overbought, color='red', linestyle='--', alpha=0.7, label=f'Overbought ({rsi_overbought})')
        ax2.axhline(y=rsi_mid_level, color='gray', linestyle=':', alpha=0.7, label=f'Mid Level ({rsi_mid_level})')
        ax2.axhline(y=rsi_oversold, color='green', linestyle='--', alpha=0.7, label=f'Oversold ({rsi_oversold})')
        ax2.set_ylabel('RSI', fontsize=12)
        ax2.set_ylim(0, 100)

        # Volume
        vol_ma_period = 10
        ax3.bar(data_df.index, data_df['volume'], label='Volume', color='blue', alpha=0.7)
        vol_ma = data_df['volume'].rolling(window=vol_ma_period).mean()
        ax3.plot(data_df.index, vol_ma, label=f'Volume MA ({vol_ma_period})', color='yellow', linewidth=2)
        ax3.set_ylabel('Volume', fontsize=12)

        # Equity Curve
        if not trades_df.empty and 'pnl_comm' in trades_df.columns and 'exit_dt' in trades_df.columns:
            trades_df_sorted = trades_df_plot.dropna(subset=['exit_dt']).sort_values(by='exit_dt').copy()
            if not trades_df_sorted.empty:
                trades_df_sorted['cumulative_pnl'] = trades_df_sorted['pnl_comm'].cumsum()
                equity_curve = self.initial_capital + trades_df_sorted['cumulative_pnl']
                ax4.plot(trades_df_sorted['exit_dt'], equity_curve, label='Equity Curve', color='green', linewidth=2)
                rolling_max_equity = equity_curve.expanding().max()
                ax4.fill_between(trades_df_sorted['exit_dt'], equity_curve, rolling_max_equity, where=equity_curve < rolling_max_equity, color='red', alpha=0.3, label='Drawdown')
        ax4.axhline(y=self.initial_capital, color='white', linestyle='--', alpha=0.7, label='Initial Capital')
        ax4.set_ylabel('Equity', fontsize=12)
        ax4.set_xlabel('Date', fontsize=12)

        # Titles and legends
        ax1.set_title(f'Trading Results - {data_file_name} - Params: {params}', fontsize=16)
        for ax in [ax1, ax2, ax3, ax4]: ax.legend(loc='upper left', fontsize=10)
        plt.xticks(rotation=45); plt.tight_layout()
        plot_path = os.path.join(self.results_dir, f'{data_file_name}_plot.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight'); plt.close()
        return plot_path

    def save_results(self, data_file, optimization_result, final_metrics):
        try:
            self.log_message(f"\nSaving results for {data_file} (MeanReversionRSBBATRStrategy)...")
            os.makedirs(self.results_dir, exist_ok=True)
            best_params_values = optimization_result.x
            best_params_dict = self.params_to_dict(best_params_values)
            
            self.log_message(f"Best parameters from skopt: {best_params_dict}")
            self.log_message(f"Metrics for these best params: {final_metrics}")

            self.log_message("Running final backtest with best parameters for trade log...")
            final_backtest_run = self.run_backtest(self.current_data.copy(), best_params_dict)
            
            trades_df = pd.DataFrame()
            if final_backtest_run and hasattr(final_backtest_run['strategy_instance'], 'trades_log'):
                trades_log_list = final_backtest_run['strategy_instance'].trades_log
                if trades_log_list:
                    trades_df = pd.DataFrame(trades_log_list)
                    self.log_message(f"Retrieved {len(trades_df)} trades from final backtest.")
                else: self.log_message("No trades in trades_log from final backtest.")
            else: self.log_message("Could not get trade log from final backtest.")

            self.log_message("Generating plot for best parameters...")
            plot_path = self.plot_results(self.current_data.copy(), trades_df, best_params_dict, data_file)
            self.log_message(f"Plot for {data_file} at: {plot_path}")
            
            trades_records_for_json = []
            if not trades_df.empty:
                for col in ['entry_dt', 'exit_dt']:
                    if col in trades_df.columns and pd.api.types.is_datetime64_any_dtype(trades_df[col]):
                        trades_df[col] = pd.to_datetime(trades_df[col]).apply(lambda x: x.isoformat() if pd.notnull(x) else None)
                trades_records_for_json = trades_df.to_dict(orient='records')
            
            opt_history = []
            for x_iter, score_iter in zip(optimization_result.x_iters, optimization_result.func_vals):
                try: opt_history.append({'params': self.params_to_dict(x_iter), 'score': float(score_iter)})
                except Exception as e_hist: self.log_message(f"Warn: Can't process opt history item: {e_hist}")
            
            filename_base = f"{data_file}_optimization_results"

            results_dict = {
                'timestamp': datetime.now().isoformat(), 'data_file': data_file,
                'strategy_name': 'MeanReversionRSBBATRStrategy',
                'best_params': best_params_dict, 
                'final_metrics': final_metrics,
                'best_score_from_optimizer': float(optimization_result.fun), 
                'trades_log': trades_records_for_json, 
                'optimization_history': opt_history,
                'plot_path': plot_path 
            }
            
            results_path = os.path.join(self.results_dir, f'{filename_base}.json')
            self.log_message(f"Saving results to: {results_path}")
            try:
                with open(results_path, 'w') as f: json.dump(results_dict, f, indent=4, cls=BaseOptimizer.DateTimeEncoder)
            except Exception as e_json: 
                self.log_message(f"Error during JSON serialization: {e_json}. Saving simplified.")
                simplified_dict = {k: (v if isinstance(v, (dict, list, str, int, float, bool, type(None))) else str(v)) for k, v in results_dict.items()}
                for key_complex in ['trades_log', 'optimization_history', 'final_metrics', 'best_params']:
                    if key_complex in simplified_dict and not isinstance(simplified_dict[key_complex], (list,dict)):
                         simplified_dict[key_complex] = f"Error serializing {key_complex}, see logs or original dict."
                simplified_dict['serialization_error'] = str(e_json)
                with open(results_path, 'w') as f: json.dump(simplified_dict, f, indent=4, cls=BaseOptimizer.DateTimeEncoder)
            self.log_message(f"Results for {data_file} saved.")
            return results_dict
        except Exception as e_save:
            self.log_message(f"Error in save_results for {data_file}: {str(e_save)}")
            import traceback
            self.log_message(f"Full save_results traceback: {traceback.format_exc()}")
            return None
    
    def run_optimization(self):
        self.log_message(f"Starting {self.__class__.__name__} optimization process...")
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv') and not f.startswith('.')]
        if not data_files: self.log_message("No data files found. Exiting."); return
        
        all_results = []
        for data_file in data_files:
            try:
                if data_file not in self.raw_data:
                    self.log_message(f"Data for {data_file} not pre-loaded. Attempting dynamic load.")
                    try:
                        df = pd.read_csv(os.path.join(self.data_dir, data_file), index_col='timestamp', parse_dates=True)
                        required_cols = ['open', 'high', 'low', 'close', 'volume']
                        if not all(col in df.columns for col in required_cols):
                             df['volume'] = 0
                        if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                            self.log_message(f"Skipping {data_file}, missing OHLC columns.")
                            continue
                        df = df[required_cols].copy()
                        for col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
                        df.sort_index(inplace=True)
                        df.ffill(inplace=True).bfill(inplace=True)
                        if df.isnull().values.any(): self.log_message(f"Skipping {data_file}, NaNs persist after fill."); continue
                        self.raw_data[data_file] = df
                        self.log_message(f"Dynamically loaded and prepared {data_file}.")
                    except Exception as load_e: self.log_message(f"Dynamic load for {data_file} failed: {load_e}. Skipping."); continue
                
                result = self.optimize_single_file(data_file)
                if result is not None: all_results.append(result)
            except Exception as e_file_opt:
                self.log_message(f"Major error optimizing {data_file}: {str(e_file_opt)}")
                import traceback
                self.log_message(f"Traceback: {traceback.format_exc()}")

        if not all_results: self.log_message("No optimization results generated."); return
            
        combined_results_data = {
            'optimization_run_timestamp': datetime.now().isoformat(),
            'optimizer_class': self.__class__.__name__,
            'strategy_name': 'MeanReversionRSBBATRStrategy',
            'results_summary': [
                { 'data_file': r.get('data_file'), 'best_score': r.get('best_score_from_optimizer'),
                  'best_params': r.get('best_params'),
                  'total_trades': r.get('final_metrics',{}).get('total_trades'),
                  'net_profit': r.get('final_metrics',{}).get('net_profit'),
                  'sharpe_ratio': r.get('final_metrics',{}).get('sharpe_ratio'),
                  'max_drawdown_pct': r.get('final_metrics',{}).get('max_drawdown_pct'),
                  'sqn': r.get('final_metrics',{}).get('sqn'),
                  'plot_path': r.get('plot_path') } for r in all_results if r
            ],
            'full_results': all_results
        }
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_filename = f'combined_optim_results.json'
        combined_path = os.path.join(self.results_dir, combined_filename)
        try:
            with open(combined_path, 'w') as f: json.dump(combined_results_data, f, indent=4, cls=BaseOptimizer.DateTimeEncoder)
            self.log_message(f"\nCombined results saved to {combined_path}")
        except Exception as e_comb_save: self.log_message(f"Error saving combined JSON: {e_comb_save}")

if __name__ == "__main__":
    optimizer = MeanReversionRSBBATROptimizer(initial_capital=1000.0, commission=0.001)
    optimizer.run_optimization()

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
from src.strats.bb_volume_supertrend_strategy import BBSuperTrendVolumeBreakoutStrategy
import backtrader as bt
import matplotlib.gridspec as gridspec
from datetime import datetime
from ta.volatility import AverageTrueRange, BollingerBands
from src.optimizer.base_optimizer import BaseOptimizer

class BBSuperTrendVolumeBreakoutOptimizer(BaseOptimizer):
    def __init__(self, initial_capital=1000.0, commission=0.001):
        super().__init__(initial_capital, commission)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results_bb_supertrend_volume_breakout')
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.space = [
            Integer(10, 50, name='bb_period'),
            Real(1.5, 3.5, name='bb_devfactor'),
            Integer(7, 21, name='st_period'),
            Real(1.0, 4.0, name='st_multiplier'),
            Integer(10, 50, name='vol_ma_period'),
            Real(1.2, 3.0, name='vol_strength_mult'),
            Integer(7, 21, name='atr_period'),
            Real(1.0, 5.0, name='tp_atr_mult'),
            Real(0.5, 3.0, name='sl_atr_mult')
        ]
        
        self.current_metrics = {}
        self.current_data = None
        self.current_symbol = None
        self.raw_data = {}
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
        warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    def _calculate_supertrend_for_plot(self, data_df: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
        """Helper to calculate SuperTrend for plotting, using ta library for ATR."""
        if not all(col in data_df.columns for col in ['high', 'low', 'close']):
            self.log_message("Warning: Dataframe for SuperTrend calculation must contain 'high', 'low', 'close' columns.")
            return pd.Series(index=data_df.index, dtype='float64')

        atr_calculator = AverageTrueRange(high=data_df['high'], low=data_df['low'], close=data_df['close'], window=period, fillna=False)
        atr = atr_calculator.average_true_range()

        if atr is None or atr.empty or atr.isnull().all():
            self.log_message(f"ATR calculation failed or all NaN for ST plot. Period: {period}")
            return pd.Series(index=data_df.index, dtype='float64')
        
        atr = atr.reindex(data_df.index)

        hl2 = (data_df['high'] + data_df['low']) / 2
        basic_upperband = hl2 + multiplier * atr
        basic_lowerband = hl2 - multiplier * atr

        final_upperband = pd.Series(index=data_df.index, dtype='float64')
        final_lowerband = pd.Series(index=data_df.index, dtype='float64')
        supertrend = pd.Series(index=data_df.index, dtype='float64')

        final_upperband.iloc[0] = basic_upperband.iloc[0] if not pd.isna(basic_upperband.iloc[0]) else np.nan
        final_lowerband.iloc[0] = basic_lowerband.iloc[0] if not pd.isna(basic_lowerband.iloc[0]) else np.nan
        trend = 0

        first_valid_idx = atr.first_valid_index()
        if first_valid_idx is None:
            self.log_message("No valid ATR values to start SuperTrend calculation for plot.")
            return supertrend
        
        start_loc = data_df.index.get_loc(first_valid_idx)

        if data_df['close'].iloc[start_loc] > basic_upperband.iloc[start_loc]:
            trend = 1
            supertrend.iloc[start_loc] = basic_lowerband.iloc[start_loc]
        elif data_df['close'].iloc[start_loc] < basic_lowerband.iloc[start_loc]:
            trend = -1
            supertrend.iloc[start_loc] = basic_upperband.iloc[start_loc]
        else:
            supertrend.iloc[start_loc] = np.nan
            trend = 0 
        
        final_upperband.iloc[start_loc] = basic_upperband.iloc[start_loc]
        final_lowerband.iloc[start_loc] = basic_lowerband.iloc[start_loc]

        for i in range(start_loc + 1, len(data_df)):
            if pd.isna(atr.iloc[i]):
                final_upperband.iloc[i] = final_upperband.iloc[i-1]
                final_lowerband.iloc[i] = final_lowerband.iloc[i-1]
                supertrend.iloc[i] = supertrend.iloc[i-1]
                continue

            close = data_df['close'].iloc[i]
            prev_close = data_df['close'].iloc[i-1]
            
            if basic_upperband.iloc[i] < final_upperband.iloc[i-1] or prev_close > final_upperband.iloc[i-1]:
                final_upperband.iloc[i] = basic_upperband.iloc[i]
            else:
                final_upperband.iloc[i] = final_upperband.iloc[i-1]

            if basic_lowerband.iloc[i] > final_lowerband.iloc[i-1] or prev_close < final_lowerband.iloc[i-1]:
                final_lowerband.iloc[i] = basic_lowerband.iloc[i]
            else:
                final_lowerband.iloc[i] = final_lowerband.iloc[i-1]
            
            if trend == 1 and close < final_lowerband.iloc[i]:
                trend = -1
            elif trend == -1 and close > final_upperband.iloc[i]:
                trend = 1
            elif trend == 0:
                if close > basic_upperband.iloc[i]:
                    trend = 1
                elif close < basic_lowerband.iloc[i]:
                    trend = -1
            
            if trend == 1:
                supertrend.iloc[i] = final_lowerband.iloc[i]
            elif trend == -1:
                supertrend.iloc[i] = final_upperband.iloc[i]
            else:
                 supertrend.iloc[i] = np.nan
        return supertrend

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
                        raise ValueError(f"Missing required column: {col} in {data_file}")
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df.sort_index(inplace=True)
                if df.isnull().values.any():
                    self.log_message(f"Warning: NaN values found in {data_file}. Forward-filling and back-filling.")
                    df.ffill(inplace=True)
                    df.bfill(inplace=True)
                
                if df.isnull().values.any():
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
            if name in ['bb_period', 'st_period', 'vol_ma_period', 'atr_period']:
                typed_param_dict[name] = int(value)
            elif name in ['bb_devfactor', 'st_multiplier', 'vol_strength_mult', 'tp_atr_mult', 'sl_atr_mult']:
                typed_param_dict[name] = float(value)
            else:
                 typed_param_dict[name] = value
        return typed_param_dict
    
    def run_backtest(self, data, params):
        """Run backtest with given parameters"""
        cerebro = bt.Cerebro(stdstats=False)
        
        if not isinstance(data.index, pd.DatetimeIndex):
            self.log_message("Error: Data for backtest must have a DatetimeIndex.")
            return None
        expected_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in expected_cols):
            self.log_message(f"Error: Data missing one of required columns: {expected_cols}")
            return None

        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime=None,
            open='open', high='high', low='low', close='close', volume='volume',
            openinterest=-1
        )
        cerebro.adddata(data_feed)
               
        cerebro.addstrategy(BBSuperTrendVolumeBreakoutStrategy, **params)
        
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)
        
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0, timeframe=bt.TimeFrame.Days, compression=1, annualize=True)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
        
        try:
            results = cerebro.run()
            if not results or not results[0]:
                self.log_message(f"Backtest with params {params} did not yield valid results object.")
                return None
            strategy_instance = results[0]
        except Exception as e:
            self.log_message(f"Error during backtest run for params {params}: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
            return None

        if not strategy_instance:
             self.log_message(f"Backtest failed to produce strategy instance for params {params}")
             return None

        sharpe = strategy_instance.analyzers.sharpe.get_analysis() if hasattr(strategy_instance.analyzers, 'sharpe') else {}
        drawdown = strategy_instance.analyzers.drawdown.get_analysis() if hasattr(strategy_instance.analyzers, 'drawdown') else {}
        trades = strategy_instance.analyzers.trades.get_analysis() if hasattr(strategy_instance.analyzers, 'trades') else {}
        sqn = strategy_instance.analyzers.sqn.get_analysis() if hasattr(strategy_instance.analyzers, 'sqn') else {}
        annual_return = strategy_instance.analyzers.annual_return.get_analysis() if hasattr(strategy_instance.analyzers, 'annual_return') else {}
        
        return {
            'strategy_instance': strategy_instance,
            'sharpe': sharpe,
            'drawdown': drawdown,
            'trades': trades,
            'sqn': sqn,
            'annual_return': annual_return
        }
    
    def objective(self, params):
        param_dict = self.params_to_dict(params)
        self.log_message(f"Testing params: {param_dict}")
            
        backtest_results = self.run_backtest(self.current_data.copy(), param_dict)
        
        if backtest_results is None:
            self.log_message(f"Backtest failed for params {param_dict}, returning high penalty.")
            return 1000.0

        trades_analysis = backtest_results.get('trades', {})
        sharpe_analysis = backtest_results.get('sharpe', {})
        drawdown_analysis = backtest_results.get('drawdown', {})
        sqn_analysis = backtest_results.get('sqn', {})

        total_trades = trades_analysis.get('total', {}).get('total', 0)
        
        if total_trades < 10:
            self.log_message(f"Penalizing due to low trade count: {total_trades} for params {param_dict}")
            return 500.0 - total_trades * 10

        net_profit_pct = float(trades_analysis.get('pnl', {}).get('net', {}).get('total', 0.0)) / self.initial_capital * 100
        
        objective_score = -net_profit_pct

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
        total_pnl = trades_analysis.get('pnl', {}).get('net', {}).get('total', 0)
        gross_profit = trades_analysis.get('won', {}).get('pnl', {}).get('total', 0)
        gross_loss = abs(trades_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
        profit_factor_val = gross_profit / gross_loss if gross_loss > 0 else 0

        self.current_metrics = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor_val,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'sqn': sqn_val,
            'net_profit_pct': net_profit_pct,
            'portfolio_growth_pct': portfolio_growth,
            'final_value': final_value,
            'params': param_dict
        }
        self.log_message(f"Params: {param_dict} -> Score: {objective_score:.2f}, NetProfit%: {net_profit_pct:.2f}, Trades: {total_trades}, Sharpe: {sharpe_ratio:.2f}, DD: {max_drawdown_pct:.2f}%, SQN: {sqn_val:.2f}")
        return float(objective_score)
    
    def optimize_single_file(self, data_file):
        self.log_message(f"\nOptimizing for {data_file}...")
        self.current_symbol = data_file.split('_')[0]
        if data_file not in self.raw_data:
            self.log_message(f"Error: No data found for file {data_file}. Ensure it was loaded.")
            return None
        self.current_data = self.raw_data[data_file].copy()
        min_data_len = max(s.low for s in self.space if hasattr(s, 'low')) * 2
        min_data_len = max(min_data_len, 50)

        if len(self.current_data) < min_data_len:
            self.log_message(f"Warning: Insufficient data points ({len(self.current_data)} < {min_data_len}) in {data_file}. Skipping...")
            return None
        if self.current_data.isnull().any().any():
            self.log_message(f"Warning: Found missing values in {data_file} before optimization. Cleaning data...")
            self.current_data.ffill(inplace=True)
            self.current_data.bfill(inplace=True)
            if self.current_data.isnull().any().any():
                 self.log_message(f"Error: NaN values persist in {data_file} even after fill. Skipping.")
                 return None
        self.current_metrics = {} 
        try:
            result = gp_minimize(
                func=self.objective, dimensions=self.space, n_calls=100,
                n_random_starts=20, noise=0.01, n_jobs=-1, verbose=False, acq_func="EI")
            self.log_message(f"\nOptimization completed for {data_file}")
            best_params_values = result.x
            best_score = result.fun
            
            final_metrics_for_best_params = self.current_metrics 
            if not final_metrics_for_best_params or self.params_to_dict(best_params_values) != final_metrics_for_best_params.get('params'):
                self.log_message("Warning: current_metrics might not correspond to best skopt result. Re-evaluating for report.")
                _ = self.objective(best_params_values)
                final_metrics_for_best_params = self.current_metrics
            
            self.log_message(f"Best parameters found: {final_metrics_for_best_params.get('params')}")
            self.log_message(f"Achieved objective score: {best_score:.2f}")
            self.log_message(f"Metrics for best: {final_metrics_for_best_params}")

            return self.save_results(data_file, result, final_metrics_for_best_params)
        except Exception as e:
            self.log_message(f"Error during optimization for {data_file}: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
            return None
    
    def plot_results(self, data_df: pd.DataFrame, trades_df: pd.DataFrame, params: dict, data_file_name: str):
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(20, 16))
        gs = gridspec.GridSpec(3, 1, height_ratios=[3, 1, 1]) 
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        
        ax1.plot(data_df.index, data_df['close'], label='Price', color='lightgray', linewidth=1.5)
        
        bb_period = params.get('bb_period', 20)
        bb_devfactor = params.get('bb_devfactor', 2.0)
        bb_indicator = BollingerBands(close=data_df['close'], window=bb_period, window_dev=bb_devfactor, fillna=False)
        ax1.plot(data_df.index, bb_indicator.bollinger_hband(), label=f'BB Top ({bb_period},{bb_devfactor})', color='cyan', linestyle='--', alpha=0.7, linewidth=1)
        ax1.plot(data_df.index, bb_indicator.bollinger_lband(), label=f'BB Low ({bb_period},{bb_devfactor})', color='cyan', linestyle='--', alpha=0.7, linewidth=1)
        ax1.plot(data_df.index, bb_indicator.bollinger_mavg(), label=f'BB Mid ({bb_period})', color='blue', linestyle=':', alpha=0.6, linewidth=1)
        ax1.fill_between(data_df.index, bb_indicator.bollinger_lband(), bb_indicator.bollinger_hband(), color='cyan', alpha=0.1)

        st_period = params.get('st_period', 10)
        st_multiplier = params.get('st_multiplier', 3.0)
        supertrend_plot_values = self._calculate_supertrend_for_plot(data_df, st_period, st_multiplier)
        ax1.plot(data_df.index, supertrend_plot_values, label=f'SuperTrend ({st_period},{st_multiplier})', color='orange', linestyle='-', linewidth=1.5, alpha=0.9)
        
        if not trades_df.empty:
            long_trades = trades_df[trades_df['direction'] == 'long']
            short_trades = trades_df[trades_df['direction'] == 'short']
            if not long_trades.empty:
                ax1.scatter(long_trades['entry_dt'], long_trades['entry_price'], color='lime', marker='^', s=100, label='Long Entry', zorder=5, edgecolors='black')
                ax1.scatter(long_trades['exit_dt'], long_trades['exit_price'], color='red', marker='v', s=100, label='Long Exit', zorder=5, edgecolors='black')
            if not short_trades.empty:
                ax1.scatter(short_trades['entry_dt'], short_trades['entry_price'], color='fuchsia', marker='v', s=100, label='Short Entry', zorder=5, edgecolors='black')
                ax1.scatter(short_trades['exit_dt'], short_trades['exit_price'], color='aqua', marker='^', s=100, label='Short Exit', zorder=5, edgecolors='black')
        
        vol_ma_period = params.get('vol_ma_period', 20)
        ax2.bar(data_df.index, data_df['volume'], label='Volume', color='lightblue', alpha=0.7)
        vol_ma = data_df['volume'].rolling(window=vol_ma_period).mean()
        ax2.plot(data_df.index, vol_ma, label=f'Volume MA ({vol_ma_period})', color='yellow', linewidth=1.5)
        
        if not trades_df.empty and 'pnl_comm' in trades_df.columns:
            trades_df_sorted = trades_df.sort_values(by='exit_dt').copy()
            trades_df_sorted['cumulative_pnl'] = trades_df_sorted['pnl_comm'].cumsum()
            equity_curve = self.initial_capital + trades_df_sorted['cumulative_pnl']
            ax3.plot(trades_df_sorted['exit_dt'], equity_curve, label='Equity Curve (PnL based)', color='lightgreen', linewidth=2)
            
            rolling_max_equity = equity_curve.expanding().max()
            drawdown_values = equity_curve - rolling_max_equity
            ax3.fill_between(trades_df_sorted['exit_dt'], equity_curve, rolling_max_equity, where=equity_curve < rolling_max_equity, color='red', alpha=0.3, label='Drawdown from Peak')
        ax3.axhline(y=self.initial_capital, color='white', linestyle='--', alpha=0.7, label='Initial Capital')
        
        ax1.set_title(f'Trading Results - {data_file_name} - Params: {json.dumps(params,indent=1)}', fontsize=14)
        ax1.set_ylabel('Price / Indicators', fontsize=12); 
        ax2.set_ylabel('Volume', fontsize=12); 
        ax3.set_ylabel('Equity', fontsize=12)
        ax3.set_xlabel('Date', fontsize=12)
        for ax in [ax1, ax2, ax3]: 
            ax.legend(loc='upper left', fontsize=9)
            ax.grid(True, linestyle=':', alpha=0.5)
        plt.setp(ax1.get_xticklabels(), visible=False)
        plt.setp(ax2.get_xticklabels(), visible=False)
        plt.tight_layout(pad=1.5)
        plot_filename = f'{self.current_symbol}_{data_file_name.replace(".csv","")}_plot.png'
        plot_path = os.path.join(self.results_dir, plot_filename)
        plt.savefig(plot_path, dpi=200, bbox_inches='tight'); plt.close(fig)
        self.log_message(f"Plot saved to {plot_path}")
        return plot_path

    def save_results(self, data_file, optimization_result, final_metrics):
        try:
            self.log_message(f"\nSaving results for {data_file}...")
            os.makedirs(self.results_dir, exist_ok=True)
            best_params_values = optimization_result.x
            best_params_dict = self.params_to_dict(best_params_values)
            
            self.log_message(f"Best parameters determined by skopt: {best_params_dict}")
            self.log_message(f"Metrics from final evaluation with these params: {final_metrics}")

            self.log_message("Running final backtest with best parameters to capture trade log...")
            final_backtest_run = self.run_backtest(self.current_data.copy(), best_params_dict)
            
            trades_df = pd.DataFrame()
            if final_backtest_run and hasattr(final_backtest_run['strategy_instance'], 'trades_log'):
                trades_log_list = final_backtest_run['strategy_instance'].trades_log
                if trades_log_list:
                    trades_df = pd.DataFrame(trades_log_list)
                    self.log_message(f"Retrieved {len(trades_df)} trades from final backtest run.")
                else:
                    self.log_message("No trades in the trades_log from final backtest run.")
            else:
                self.log_message("Could not retrieve trade log from final backtest run.")

            self.log_message("Generating plot for best parameters...")
            plot_path = self.plot_results(self.current_data, trades_df, best_params_dict, data_file)
            self.log_message(f"Plot generated at: {plot_path}")
            
            trades_records_for_json = []
            if not trades_df.empty:
                for col in ['entry_dt', 'exit_dt']:
                    if col in trades_df.columns and pd.api.types.is_datetime64_any_dtype(trades_df[col]):
                        trades_df[col] = pd.to_datetime(trades_df[col]).apply(lambda x: x.isoformat() if pd.notnull(x) else None)
                trades_records_for_json = trades_df.to_dict(orient='records')
            
            optimization_history = []
            for x_iter, score_iter in zip(optimization_result.x_iters, optimization_result.func_vals):
                try:
                    param_dict_iter = self.params_to_dict(x_iter)
                    optimization_history.append({'params': param_dict_iter, 'score': float(score_iter)})
                except Exception as e:
                    self.log_message(f"Warning: Could not process optimization history entry: {e}")
            
            param_str_part = "_params_" + "_".join([f"{k[:3]}{v:.2f if isinstance(v, float) else v}" for k,v in best_params_dict.items()])[:60].replace(" ","").replace(".", "")
            filename_base = f"{self.current_symbol}_{data_file.replace('.csv','')}{param_str_part}_BBSTV_optim"

            results_dict = {
                'timestamp': datetime.now().isoformat(), 'data_file': data_file,
                'best_params': best_params_dict, 
                'final_metrics': final_metrics,
                'best_score_from_optimizer': float(optimization_result.fun), 
                'trades_log': trades_records_for_json, 
                'optimization_history': optimization_history,
                'plot_path': plot_path 
            }
            
            results_path = os.path.join(self.results_dir, f'{filename_base}_results.json')
            self.log_message(f"Saving results to: {results_path}")
            
            # Calculate sqn_pct and cagr using BaseOptimizer utilities
            sqn_pct = None
            cagr = None
            try:
                trades_log = final_backtest_run['strategy_instance'].trades_log if final_backtest_run and hasattr(final_backtest_run['strategy_instance'], 'trades_log') else []
                if trades_log and len(trades_log) > 1:
                    import pandas as pd
                    trades_df = pd.DataFrame(trades_log)
                    sqn_pct = BaseOptimizer.calculate_sqn_pct(trades_df)
                    if 'entry_dt' in trades_df.columns and 'exit_dt' in trades_df.columns:
                        trades_df = trades_df.dropna(subset=['entry_dt', 'exit_dt'])
                        if not trades_df.empty:
                            cagr = BaseOptimizer.calculate_cagr(self.initial_capital, final_metrics.get('final_value', 0), trades_df['entry_dt'].iloc[0], trades_df['exit_dt'].iloc[-1])
            except Exception:
                pass
            try:
                with open(results_path, 'w') as f: json.dump(results_dict, f, indent=4, cls=BaseOptimizer.DateTimeEncoder)
            except Exception as e_json: 
                self.log_message(f"Error during JSON serialization: {e_json}. Trying to save simplified.")
                simplified_dict = {k: (v if isinstance(v, (dict, list, str, int, float, bool)) else str(v)) for k, v in results_dict.items()}
                if 'trades_log' in simplified_dict: simplified_dict['trades_log'] = "Error during serialization, see logs"
                if 'optimization_history' in simplified_dict: simplified_dict['optimization_history'] = "Error during serialization, see logs"
                simplified_dict['serialization_error'] = str(e_json)
                with open(results_path, 'w') as f: json.dump(simplified_dict, f, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                self.log_message("Saved simplified results due to serialization error.")
            
            self.log_message(f"Results for {data_file} saved.")
            return results_dict
            
        except Exception as e:
            self.log_message(f"Error in save_results for {data_file}: {str(e)}")
            import traceback
            self.log_message(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def run_optimization(self):
        self.log_message("Starting BBSuperTrendVolumeBreakoutStrategy optimization process...")
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv') and not f.startswith('.')]
        if not data_files:
            self.log_message("No data files found in data directory. Exiting optimization.")
            return
        
        all_results = []
        for data_file in data_files:
            try:
                if data_file not in self.raw_data:
                    self.log_message(f"Data for {data_file} not pre-loaded. Attempting to load now.")
                    try:
                        df = pd.read_csv(os.path.join(self.data_dir, data_file))
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df.set_index('timestamp', inplace=True)
                        required_columns = ['open', 'high', 'low', 'close', 'volume']
                        if not all(col in df.columns for col in required_columns):
                            self.log_message(f"Skipping {data_file} due to missing columns.")
                            continue
                        df.ffill(inplace=True); df.bfill(inplace=True)
                        if df.isnull().values.any():
                             self.log_message(f"Skipping {data_file} due to persistent NaNs.")
                             continue
                        self.raw_data[data_file] = df
                        self.log_message(f"Dynamically loaded {data_file}.")
                    except Exception as load_e:
                        self.log_message(f"Could not dynamically load {data_file}: {load_e}. Skipping.")
                        continue
                
                result = self.optimize_single_file(data_file)
                if result is not None: 
                    all_results.append(result)
            except Exception as e:
                self.log_message(f"Major error processing {data_file}: {str(e)}")
                import traceback
                self.log_message(f"Traceback for {data_file} error: {traceback.format_exc()}")

        if not all_results:
            self.log_message("No optimization results were generated for any data file.")
            return
            
        combined_results_data = {
            'optimization_run_timestamp': pd.Timestamp.now().isoformat(),
            'strategy_name': 'BBSuperTrendVolumeBreakoutStrategy',
            'results_summary': [
                {
                    'data_file': r.get('data_file'),
                    'best_score': r.get('best_score_from_optimizer'),
                    'best_params': r.get('best_params'),
                    'total_trades': r.get('final_metrics',{}).get('total_trades'),
                    'net_profit_pct': r.get('final_metrics',{}).get('net_profit_pct'),
                    'sharpe_ratio': r.get('final_metrics',{}).get('sharpe_ratio'),
                    'max_drawdown_pct': r.get('final_metrics',{}).get('max_drawdown_pct'),
                    'sqn': r.get('final_metrics',{}).get('sqn'),
                    'plot_path': r.get('plot_path')
                } for r in all_results
            ],
            'full_results': all_results
        }
        combined_filename = f'combined_BBSTV_optimization_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        combined_path = os.path.join(self.results_dir, combined_filename)
        try:
            with open(combined_path, 'w') as f: 
                json.dump(combined_results_data, f, indent=4, cls=BaseOptimizer.DateTimeEncoder)
            self.log_message(f"\nCombined optimization results saved to {combined_path}")
        except Exception as e:
            self.log_message(f"Error saving combined JSON results: {e}")

if __name__ == "__main__":
    optimizer = BBSuperTrendVolumeBreakoutOptimizer(initial_capital=10000.0, commission=0.001)
    optimizer.run_optimization()

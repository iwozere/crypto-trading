import os
import json
import numpy as np
import pandas as pd
import traceback
import backtrader as bt
from datetime import datetime
from ta.volatility import AverageTrueRange
from src.notification.logger import _logger
from skopt import gp_minimize

class BaseOptimizer:
    def __init__(self, initial_capital=1000.0, commission=0.001, notify=False):
        self.initial_capital = initial_capital
        self.commission = commission
        self.current_metrics = {}
        self.current_data = None
        self.current_symbol = None
        self.raw_data = {}
        self.load_all_data()
        self.notify = notify

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (pd.Timestamp, datetime)):
                return obj.isoformat()
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    @staticmethod
    def calculate_sqn_pct(trades_df):
        """Calculate SQN on percent returns per trade (pnl_comm / entry_price * 100)."""
        if trades_df is None or len(trades_df) < 2:
            return None
        trades_df = trades_df.dropna(subset=['entry_price', 'pnl_comm'])
        if trades_df.empty:
            return None
        trades_df['pct_return'] = trades_df['pnl_comm'] / trades_df['entry_price'] * 100
        returns = trades_df['pct_return'].values
        n = len(returns)
        if n > 1 and np.std(returns) > 0:
            return float(np.mean(returns) / np.std(returns) * np.sqrt(n))
        return None

    @staticmethod
    def calculate_cagr(initial_value, final_value, start_date, end_date):
        """Calculate CAGR given initial/final value and start/end date (datetime or str)."""
        try:
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
            years = (end_date - start_date).days / 365.25
            if years > 0:
                cagr = (final_value / initial_value) ** (1/years) - 1
                return float(cagr)
        except Exception:
            pass
        return None

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

    def log_message(self, message, level="info"):
        """
        Log a message using the configured logger.
        - level: "info" (default) for normal messages, "error" for errors.
        """
        if level == "error":
            _logger.error(message)
        else:
            _logger.info(message)

    def load_all_data(self, data_dir=None, required_columns=None, parse_dates=True, sort_index=True, fillna=True, log=True):
        """
        Load all CSV files in data_dir into self.raw_data.
        - required_columns: list of columns to ensure exist (e.g. ['open','high','low','close','volume'])
        - parse_dates: whether to parse 'timestamp' as datetime
        - sort_index: whether to sort index after loading
        - fillna: whether to ffill/bfill NaNs
        - log: whether to print/log messages
        """
        if data_dir is None:
            data_dir = self.data_dir
        if required_columns is None:
            required_columns = ['open', 'high', 'low', 'close', 'volume']
        self.raw_data = {}
        data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        for data_file in data_files:
            try:
                df = pd.read_csv(os.path.join(data_dir, data_file))
                if parse_dates and 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                for col in required_columns:
                    if col not in df.columns:
                        if col == 'volume':
                            self.log_message(f"Warning: 'volume' column missing in {data_file}. Creating dummy 'volume' column with zeros.")
                            df['volume'] = 0
                        else:
                            raise ValueError(f"Missing required column: {col} in {data_file}")
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                if sort_index:
                    df.sort_index(inplace=True)
                if fillna:
                    if df.isnull().any().any():
                        self.log_message(f"Warning: NaN values found in {data_file}. Forward-filling and back-filling.")
                        df.ffill(inplace=True)
                        df.bfill(inplace=True)
                    if df.isnull().any().any():
                        self.log_message(f"Error: NaN values persist in {data_file} after fill. Skipping.")
                        continue
                self.raw_data[data_file] = df
                if log:
                    self.log_message(f"Loaded data for {data_file}, shape: {df.shape}, date range: {df.index.min()} to {df.index.max()}")
            except Exception as e:
                self.log_message(f"Error loading {data_file}: {str(e)}")

    def params_to_dict(self, params, param_types=None):
        """
        Convert parameter list to dictionary with proper types.
        - param_types: dict of {param_name: type}, e.g. {'rsi_period': int, ...}
        If not provided, will use int for names containing 'period', else float.
        """
        if not hasattr(self, 'space'):
            raise AttributeError("Optimizer must have a 'space' attribute with parameter names.")
        param_names = [p.name for p in self.space]
        param_dict = dict(zip(param_names, params))
        typed_param_dict = {}
        for name, value in param_dict.items():
            if param_types and name in param_types:
                typed_param_dict[name] = param_types[name](value)
            elif 'period' in name or 'window' in name or 'fast' in name or 'slow' in name or 'mid' in name:
                typed_param_dict[name] = int(value)
            elif isinstance(value, bool):
                typed_param_dict[name] = bool(value)
            else:
                typed_param_dict[name] = float(value)
        return typed_param_dict 

    def save_results(self, data_file, best_params, metrics, trades_df, optimization_result=None, plot_path=None, strategy_name=None):
        """
        Unified method to save optimization results. Handles serialization, extra metrics, and logging.
        """
        try:
            self.log_message(f"\nSaving results for {data_file}...", level='info')
            os.makedirs(self.results_dir, exist_ok=True)
            # Calculate extra metrics if possible
            sqn_pct = None
            cagr = None
            final_value = metrics.get('final_value') or metrics.get('portfolio_value')
            if trades_df is not None and not trades_df.empty and final_value is not None:
                try:
                    sqn_pct = self.calculate_sqn_pct(trades_df)
                    if 'entry_dt' in trades_df.columns and 'exit_dt' in trades_df.columns:
                        trades_df = trades_df.dropna(subset=['entry_dt', 'exit_dt'])
                        if not trades_df.empty:
                            cagr = self.calculate_cagr(self.initial_capital, final_value, trades_df['entry_dt'].iloc[0], trades_df['exit_dt'].iloc[-1])
                except Exception as e:
                    self.log_message(f"Error calculating sqn_pct/cagr: {e}", level='error')
            # Prepare trades log
            trades_records = []
            if trades_df is not None and not trades_df.empty:
                for _, trade_row in trades_df.iterrows():
                    trade_dict = {}
                    for col in trades_df.columns:
                        value = trade_row[col]
                        if pd.isna(value): trade_dict[col] = None
                        elif isinstance(value, (pd.Timestamp, datetime)): trade_dict[col] = value.isoformat()
                        elif isinstance(value, (np.integer, np.floating, int, float)): trade_dict[col] = float(value)
                        else: trade_dict[col] = str(value)
                    trades_records.append(trade_dict)
            # Prepare optimization history
            optimization_history = []
            if optimization_result is not None and hasattr(optimization_result, 'x_iters'):
                for x_iter, score_iter in zip(optimization_result.x_iters, optimization_result.func_vals):
                    try:
                        param_dict_iter = self.params_to_dict(x_iter)
                        optimization_history.append({'params': param_dict_iter, 'score': float(score_iter)})
                    except Exception as e:
                        self.log_message(f"Warning: Could not process optimization history entry: {e}", level='warning')
                        continue
            # Compose results dict
            results_dict = {
                'timestamp': datetime.now().isoformat(),
                'data_file': data_file,
                'strategy_name': strategy_name,
                'best_params': best_params,
                'metrics': metrics,
                'sqn_pct': sqn_pct,
                'cagr': cagr,
                'trades': trades_records,
                'optimization_history': optimization_history,
                'plot_path': plot_path
            }
            filename_base = f"{data_file}_optimization_results"
            results_path = os.path.join(self.results_dir, f'{filename_base}.json')
            self.log_message(f"Saving results to: {results_path}", level='info')
            try:
                json_str = json.dumps(results_dict, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                with open(results_path, 'w') as f: f.write(json_str)
            except Exception as e:
                self.log_message(f"Error during JSON serialization: {e}. Trying to save simplified.", level='error')
                simplified_dict = {k: v for k, v in results_dict.items() if k not in ['trades', 'optimization_history']}
                simplified_dict['error_in_serialization'] = str(e)
                json_str = json.dumps(simplified_dict, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                with open(results_path, 'w') as f: f.write(json_str)
                self.log_message("Saved simplified results due to serialization error.", level='error')
            self.log_message(f"Results saved to {results_path}", level='info')
            return results_dict
        except Exception as e:
            self.log_message(f"Error in save_results: {str(e)}", level='error')
            self.log_message(f"Full traceback: {traceback.format_exc()}", level='error')
            return None 

    def optimize_single_file(self, data_file):
        """
        Generalized optimization routine for a single data file.
        Subclasses must set self.strategy_name and implement self.plot_results.
        """
        self.log_message(f"\nOptimizing {data_file} for {getattr(self, 'strategy_name', 'UnknownStrategy')}...", level='info')
        self.current_symbol = data_file.split('_')[0]
        if data_file not in self.raw_data:
            self.log_message(f"Error: No data for {data_file}.", level='error')
            return None
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
                n_random_starts=20, 
                noise=0.01, 
                n_jobs=-1, 
                verbose=False
            )
            self.log_message(f"\nOptimization completed for {data_file}", level='info')
            best_params = self.params_to_dict(result.x)
            self.log_message(f"Best params for {data_file}: {best_params}", level='info')
            self.log_message(f"Best score: {result.fun:.2f}. Metrics: {self.current_metrics}", level='info')
            final_backtest_run = self.run_backtest(self.current_data.copy(), best_params)
            trades_df = pd.DataFrame()
            if final_backtest_run and hasattr(final_backtest_run.get('strategy', None), 'trades'):
                trades_list = final_backtest_run['strategy'].trades
                if trades_list:
                    trades_df = pd.DataFrame(trades_list)

            plot_path = None

            if hasattr(self, 'plot_results') and callable(self.plot_results):
                plot_path = self.plot_results(self.current_data.copy(), trades_df, best_params, data_file)

            return self.save_results(
                data_file=data_file,
                best_params=best_params,
                metrics=self.current_metrics,
                trades_df=trades_df,
                optimization_result=result,
                plot_path=plot_path,
                strategy_name=getattr(self, 'strategy_name', 'UnknownStrategy')
            )
        except Exception as e:
            self.log_message(f"Error during optimization for {data_file}: {str(e)}", level='error')
            self.log_message(traceback.format_exc(), level='error')
            return None 

    def run_optimization(self):
        """
        Generalized optimization routine for all data files in self.data_dir.
        Calls optimize_single_file for each .csv file, collects results, and saves a combined results JSON.
        Subclasses can override for extra summary fields or dynamic loading.
        """
        self.log_message(f"Starting {self.__class__.__name__} optimization process...", level='info')
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv') and not f.startswith('.')]
        if not data_files:
            self.log_message("No data files found. Exiting.", level='error')
            return

        all_results = []
        for data_file in data_files:
            try:
                if data_file not in self.raw_data:
                    self.log_message(f"Data for {data_file} not pre-loaded. Skipping.", level='warning')
                    continue
                result = self.optimize_single_file(data_file)
                if result is not None:
                    all_results.append(result)
            except Exception as e:
                self.log_message(f"Error processing {data_file}: {str(e)}", level='error')
                self.log_message(traceback.format_exc(), level='error')

        if not all_results:
            self.log_message("No optimization results generated.", level='error')
            return

        combined_results = {
            'timestamp': datetime.now().isoformat(),
            'optimizer_class': self.__class__.__name__,
            'strategy_name': getattr(self, 'strategy_name', 'UnknownStrategy'),
            'results': all_results
        }
        combined_path = os.path.join(self.results_dir, f'combined_optimization_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        try:
            with open(combined_path, 'w') as f:
                json.dump(combined_results, f, indent=4, cls=BaseOptimizer.DateTimeEncoder)
            self.log_message(f"\nCombined results saved to {combined_path}", level='info')
        except Exception as e:
            self.log_message(f"Error saving combined JSON: {e}", level='error') 

    def objective(self, params):
        """
        Generic objective function for optimization. Subclasses can override score_objective for custom penalty logic.
        """
        param_dict = self.params_to_dict(params)
        backtest_results = self.run_backtest(self.current_data.copy(), param_dict)
        if backtest_results is None:
            self.log_message(f"Backtest failed for params {param_dict}, returning high penalty.")
            return 1000.0

        # Extract metrics
        trades_analysis = backtest_results.get('trades', {})
        sharpe_analysis = backtest_results.get('sharpe', {})
        drawdown_analysis = backtest_results.get('drawdown', {})
        sqn_analysis = backtest_results.get('sqn', {})

        total_trades = trades_analysis.get('total', {}).get('total', 0)
        net_profit = float(trades_analysis.get('pnl', {}).get('net', {}).get('total', 0.0))
        max_drawdown_pct = float(drawdown_analysis.get('max', {}).get('drawdown', 100.0))
        sharpe_ratio = float(sharpe_analysis.get('sharperatio', -5.0) if sharpe_analysis.get('sharperatio') is not None else -5.0)
        sqn_val = float(sqn_analysis.get('sqn', -5.0) if sqn_analysis.get('sqn') is not None else -5.0)
        final_value = backtest_results['strategy'].broker.getvalue()
        portfolio_growth = ((final_value - self.initial_capital) / self.initial_capital) * 100 if final_value is not None else None
        win_rate = trades_analysis.get('won', {}).get('total', 0) / total_trades if total_trades > 0 else 0
        gross_profit = trades_analysis.get('won', {}).get('pnl', {}).get('total', 0)
        gross_loss = abs(trades_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
        profit_factor_val = gross_profit / gross_loss if gross_loss > 0 else 0

        # Calculate sqn_pct and cagr using BaseOptimizer utilities
        sqn_pct = None
        cagr = None
        try:
            trades = None
            if 'strategy' in backtest_results and hasattr(backtest_results['strategy'], 'get_trades'):
                trades = backtest_results['strategy'].get_trades()
            if trades and len(trades) > 1:
                trades_df = pd.DataFrame(trades)
                sqn_pct = BaseOptimizer.calculate_sqn_pct(trades_df)
                if 'entry_dt' in trades_df.columns and 'exit_dt' in trades_df.columns:
                    trades_df = trades_df.dropna(subset=['entry_dt', 'exit_dt'])
                    if not trades_df.empty:
                        cagr = BaseOptimizer.calculate_cagr(self.initial_capital, final_value, trades_df['entry_dt'].iloc[0], trades_df['exit_dt'].iloc[-1])
                elif 'entry_time' in trades_df.columns and 'exit_time' in trades_df.columns:
                    trades_df = trades_df.dropna(subset=['entry_time', 'exit_time'])
                    if not trades_df.empty:
                        cagr = BaseOptimizer.calculate_cagr(self.initial_capital, final_value, trades_df['entry_time'].iloc[0], trades_df['exit_time'].iloc[-1])
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
        return self.score_objective(self.current_metrics)

    def score_objective(self, metrics):
        """
        Default scoring: just return -net_profit. Subclasses can override for custom penalty logic.
        """
        return -metrics.get('net_profit', 0.0)

    def run_backtest(self, data, params):
        """
        Generic Backtrader backtest runner. Uses self.strategy_class for the strategy.
        Subclasses can override customize_cerebro(self, cerebro) for custom analyzers or broker setup.
        """
        cerebro = bt.Cerebro()
        if not isinstance(data.index, pd.DatetimeIndex):
            self.log_message("Error: Data for backtest must have a DatetimeIndex.")
            return None
        expected_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in expected_cols):
            self.log_message(f"Error: Data missing one of required columns: {expected_cols}")
            return None

        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime=None, open='open', high='high', low='low', close='close', volume='volume',
            openinterest=-1
        )
        cerebro.adddata(data_feed)
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)
        cerebro.broker.set_checksubmit(False)
        cerebro.addstrategy(self.strategy_class, notify=self.notify, **params)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0, timeframe=bt.TimeFrame.Days, compression=1, annualize=True)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
        # Allow subclass customization
        if hasattr(self, 'customize_cerebro') and callable(self.customize_cerebro):
            self.customize_cerebro(cerebro)
        try:
            results = cerebro.run()
            if not results:
                self.log_message(f"Backtest with params {params} did not yield valid results object.")
                return None
            strategy = results[0]
            sharpe = strategy.analyzers.sharpe.get_analysis()
            drawdown = strategy.analyzers.drawdown.get_analysis()
            trades = strategy.analyzers.trades.get_analysis()
            sqn = strategy.analyzers.sqn.get_analysis()
            annual_return = strategy.analyzers.annual_return.get_analysis()
            return {
                'strategy': strategy,
                'sharpe': sharpe,
                'drawdown': drawdown,
                'sqn': sqn,
                'annual_return': annual_return,
                'trades': trades
            }
        except Exception as e:
            self.log_message(f"Error during backtest run for params {params}: {str(e)}")
            self.log_message(traceback.format_exc())
            return None 
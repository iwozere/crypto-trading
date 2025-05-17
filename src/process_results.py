import os
import json
import pandas as pd
from datetime import datetime

def extract_symbol_interval_dates(filename):
    """Extract symbol, interval, start_date, end_date from filename like LTCUSDT_4h_20240501_20250501.csv_optimization_results.json"""
    base = os.path.basename(filename)
    # Remove the trailing .csv_optimization_results.json
    if base.endswith('.csv_optimization_results.json'):
        base = base[:-len('.csv_optimization_results.json')]
    parts = base.split('_')
    if len(parts) >= 4:
        symbol = parts[0]
        interval = parts[1]
        start_date = parts[2]
        end_date = parts[3]
        return symbol, interval, start_date, end_date
    else:
        return None, None, None, None

def process_json_file(file_path):
    """Process a single JSON file and extract relevant information"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    # Always extract symbol, interval, start_date, end_date from filename
    symbol, interval, start_date, end_date = extract_symbol_interval_dates(file_path)
    if not all([symbol, interval, start_date, end_date]):
        print(f"Warning: Could not extract symbol/interval/dates from filename: {file_path}")
        return None
    # Get best parameters and metrics
    best_params = data.get('best_params', {})
    metrics = data.get('metrics', {})
    # Always present metrics
    always_metrics = [
        'total_trades', 'win_rate', 'profit_factor', 'max_drawdown_pct', 'sharpe_ratio',
        'sqn', 'sqn_pct', 'cagr', 'net_profit', 'portfolio_growth_pct', 'final_value'
    ]
    result = {
        'symbol': symbol,
        'interval': interval,
        'data_start_date': start_date,
        'data_end_date': end_date,
        'strategy_type': data.get('strategy_name') or metrics.get('strategy_type') or 'unknown',
    }
    # Add always-present metrics
    for k in always_metrics:
        result[k] = metrics.get(k)
    # Add all best_params as columns (variable part)
    for k, v in best_params.items():
        result[k] = v
    return result

def main():
    results_dir = 'results'
    all_results = []
    for filename in os.listdir(results_dir):
        if filename.endswith('_optimization_results.json'):
            file_path = os.path.join(results_dir, filename)
            try:
                result = process_json_file(file_path)
                if result is not None:
                    all_results.append(result)
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    df = pd.DataFrame(all_results)
    print("Columns in DataFrame:", df.columns)
    if not df.empty:
        df = df.sort_values(['symbol', 'interval', 'data_start_date'])
        output_file = os.path.join(results_dir, 'optimization_results_summary.csv')
        df.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")
    else:
        print("No valid results to save.")

if __name__ == "__main__":
    main() 
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional

class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.join('config', 'bots')
        self.archive_dir = os.path.join('config', 'bots', 'archive')
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure config and archive directories exist"""
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def get_available_bots(self) -> List[str]:
        """Get list of available bot configurations"""
        configs = []
        for file in os.listdir(self.config_dir):
            if file.endswith('.json') and file != 'archive':
                configs.append(file[:-5])  # Remove .json extension
        return configs
    
    def get_bot_config(self, bot_id: str) -> Optional[Dict]:
        """Get configuration for a specific bot"""
        config_path = os.path.join(self.config_dir, f"{bot_id}.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return None
    
    def save_bot_config(self, bot_id: str, config: Dict) -> bool:
        """Save bot configuration and archive old one if exists"""
        config_path = os.path.join(self.config_dir, f"{bot_id}.json")
        
        # Archive existing config if it exists
        if os.path.exists(config_path):
            self._archive_config(bot_id)
        
        # Save new config
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            return False
    
    def _archive_config(self, bot_id: str):
        """Archive existing configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source = os.path.join(self.config_dir, f"{bot_id}.json")
        dest = os.path.join(self.archive_dir, f"{bot_id}_{timestamp}.json")
        shutil.copy2(source, dest)
    
    def get_bot_parameters(self, bot_id: str) -> Dict:
        """Get available parameters for a specific bot type"""
        # Define parameter templates for different bot types
        parameter_templates = {
            'rsi_bb': {
                'rsi_period': {'type': 'int', 'min': 2, 'max': 50, 'default': 14},
                'boll_period': {'type': 'int', 'min': 5, 'max': 100, 'default': 20},
                'boll_devfactor': {'type': 'float', 'min': 0.5, 'max': 5.0, 'default': 2.0},
                'atr_period': {'type': 'int', 'min': 2, 'max': 50, 'default': 14},
                'vol_ma_period': {'type': 'int', 'min': 5, 'max': 100, 'default': 20},
                'tp_atr_mult': {'type': 'float', 'min': 0.5, 'max': 5.0, 'default': 2.0},
                'sl_atr_mult': {'type': 'float', 'min': 0.5, 'max': 5.0, 'default': 1.0},
                'rsi_oversold': {'type': 'int', 'min': 10, 'max': 40, 'default': 30},
                'rsi_overbought': {'type': 'int', 'min': 60, 'max': 90, 'default': 70}
            },
            'trending': {
                'ema_fast': {'type': 'int', 'min': 5, 'max': 50, 'default': 12},
                'ema_slow': {'type': 'int', 'min': 10, 'max': 200, 'default': 26},
                'rsi_period': {'type': 'int', 'min': 2, 'max': 50, 'default': 14},
                'volume_ma_period': {'type': 'int', 'min': 5, 'max': 100, 'default': 20}
            }
        }
        
        # Get bot type from config
        config = self.get_bot_config(bot_id)
        if config and 'type' in config:
            return parameter_templates.get(config['type'], {})
        return {}
    
    def get_archived_configs(self, bot_id: str) -> List[Dict]:
        """Get list of archived configurations for a bot"""
        archives = []
        for file in os.listdir(self.archive_dir):
            if file.startswith(f"{bot_id}_") and file.endswith('.json'):
                timestamp = file[len(bot_id)+1:-5]  # Extract timestamp
                try:
                    with open(os.path.join(self.archive_dir, file), 'r') as f:
                        config = json.load(f)
                    archives.append({
                        'timestamp': timestamp,
                        'config': config
                    })
                except Exception as e:
                    print(f"Error reading archive {file}: {str(e)}")
        return sorted(archives, key=lambda x: x['timestamp'], reverse=True) 
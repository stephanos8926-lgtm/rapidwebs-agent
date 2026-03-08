"""Configuration layer loader for multi-source configuration.

This module implements a 6-layer configuration system with precedence:
1. CLI arguments (highest priority)
2. Environment variables
3. Project settings (.qwen/settings.json)
4. User settings (~/.config/rapidwebs-agent/config.yaml)
5. System settings (/etc/rapidwebs-agent/config.yaml)
6. Default values (lowest priority)

Each layer can override values from lower priority layers.
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .logging_config import get_logger

logger = get_logger('config_layers')


class ConfigLayerLoader:
    """Load configuration from multiple layers with precedence.
    
    Example:
        loader = ConfigLayerLoader()
        config = loader.load_all(cli_args={'model': 'gemini'})
        # config['model'] will be 'gemini' regardless of other layers
    """
    
    LAYERS = [
        'cli_args',      # Highest priority
        'env_vars',
        'project',
        'user',
        'system',
        'defaults'       # Lowest priority
    ]
    
    def __init__(self):
        """Initialize configuration layer loader."""
        self.logger = get_logger('config_layers')
    
    def load_all(self, cli_args: Optional[Dict] = None) -> Dict[str, Any]:
        """Load all configuration layers and merge with precedence.
        
        Args:
            cli_args: Optional CLI arguments (highest priority)
            
        Returns:
            Merged configuration dictionary
        """
        layers = []
        loaded_layers = []
        
        # 1. CLI arguments
        if cli_args:
            cli_config = self._load_cli_args(cli_args)
            if cli_config:
                layers.append(('cli', cli_config))
                loaded_layers.append('cli')
        
        # 2. Environment variables
        env_config = self._load_env_vars()
        if env_config:
            layers.append(('env', env_config))
            loaded_layers.append('env')
        
        # 3. Project settings
        project_config = self._load_project_config()
        if project_config:
            layers.append(('project', project_config))
            loaded_layers.append('project')
        
        # 4. User settings
        user_config = self._load_user_config()
        if user_config:
            layers.append(('user', user_config))
            loaded_layers.append('user')
        
        # 5. System settings
        system_config = self._load_system_config()
        if system_config:
            layers.append(('system', system_config))
            loaded_layers.append('system')
        
        # 6. Defaults
        layers.append(('defaults', self._get_defaults()))
        loaded_layers.append('defaults')
        
        self.logger.info(f'Loaded configuration layers: {", ".join(loaded_layers)}')
        
        # Merge layers (reverse order so higher priority overwrites)
        merged = {}
        for layer_name, layer_config in reversed(layers):
            merged = self._deep_merge(merged, layer_config)
            self.logger.debug(f'Merged layer {layer_name}: {len(layer_config)} keys')
        
        self.logger.debug(f'Final configuration: {len(merged)} keys')
        return merged
    
    def _load_cli_args(self, cli_args: Dict) -> Dict[str, Any]:
        """Load configuration from CLI arguments.
        
        Args:
            cli_args: CLI arguments dictionary
            
        Returns:
            Configuration dictionary
        """
        config = {}
        
        # Map CLI args to config structure
        if cli_args.get('model'):
            config['default_model'] = cli_args['model']
        
        if cli_args.get('workspace'):
            config['workspace'] = cli_args['workspace']
        
        if cli_args.get('no_cache'):
            config['cache_enabled'] = False
        
        if cli_args.get('token_limit'):
            config['token_budget'] = cli_args['token_limit']
        
        if cli_args.get('verbose'):
            config['verbose'] = True
        
        return config
    
    def _load_env_vars(self) -> Optional[Dict[str, Any]]:
        """Load configuration from environment variables.
        
        Environment variables use RW_ prefix:
        - RW_QWEN_API_KEY
        - RW_GEMINI_API_KEY
        - RW_DAILY_TOKEN_LIMIT
        - RW_DEFAULT_MODEL
        - RW_WORKSPACE
        
        Returns:
            Configuration dictionary or None if no env vars set
        """
        config = {}
        
        # API keys
        if os.environ.get('RW_QWEN_API_KEY'):
            config['qwen_api_key'] = os.environ['RW_QWEN_API_KEY']
        
        if os.environ.get('RW_GEMINI_API_KEY'):
            config['gemini_api_key'] = os.environ['RW_GEMINI_API_KEY']
        
        # Token budget
        if os.environ.get('RW_DAILY_TOKEN_LIMIT'):
            try:
                config['token_budget'] = int(os.environ['RW_DAILY_TOKEN_LIMIT'])
            except ValueError:
                self.logger.warning(f'Invalid RW_DAILY_TOKEN_LIMIT: {os.environ.get("RW_DAILY_TOKEN_LIMIT")}')
        
        # Default model
        if os.environ.get('RW_DEFAULT_MODEL'):
            config['default_model'] = os.environ['RW_DEFAULT_MODEL']
        
        # Workspace
        if os.environ.get('RW_WORKSPACE'):
            config['workspace'] = os.environ['RW_WORKSPACE']
        
        # Cache
        if os.environ.get('RW_CACHE_ENABLED') == 'false':
            config['cache_enabled'] = False
        
        return config if config else None
    
    def _load_project_config(self) -> Optional[Dict[str, Any]]:
        """Load project-specific configuration.
        
        Looks for .qwen/settings.json in current directory.
        
        Returns:
            Configuration dictionary or None if not found
        """
        project_file = Path.cwd() / '.qwen' / 'settings.json'
        
        if not project_file.exists():
            self.logger.debug(f'Project config not found: {project_file}')
            return None
        
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.logger.info(f'Loaded project config: {project_file}')
            return config
        except json.JSONDecodeError as e:
            self.logger.error(f'Invalid JSON in project config: {e}')
            return None
        except Exception as e:
            self.logger.error(f'Failed to load project config: {e}')
            return None
    
    def _load_user_config(self) -> Optional[Dict[str, Any]]:
        """Load user-specific configuration.
        
        Looks for config at:
        - ~/.config/rapidwebs-agent/config.yaml
        - ~/.config/rapidwebs-agent/config.yml
        
        Returns:
            Configuration dictionary or None if not found
        """
        # Try YAML first
        user_file_yaml = Path.home() / '.config' / 'rapidwebs-agent' / 'config.yaml'
        user_file_yml = Path.home() / '.config' / 'rapidwebs-agent' / 'config.yml'
        
        user_file = user_file_yaml if user_file_yaml.exists() else (
            user_file_yml if user_file_yml.exists() else None
        )
        
        if not user_file:
            self.logger.debug('User config not found')
            return None
        
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.logger.info(f'Loaded user config: {user_file}')
            return config
        except yaml.YAMLError as e:
            self.logger.error(f'Invalid YAML in user config: {e}')
            return None
        except Exception as e:
            self.logger.error(f'Failed to load user config: {e}')
            return None
    
    def _load_system_config(self) -> Optional[Dict[str, Any]]:
        """Load system-wide configuration.
        
        Looks for config at:
        - Windows: C:\\ProgramData\\rapidwebs-agent\\config.yaml
        - Linux/macOS: /etc/rapidwebs-agent/config.yaml
        
        Returns:
            Configuration dictionary or None if not found
        """
        if sys.platform == 'win32':
            system_file = Path(r'C:\ProgramData\rapidwebs-agent\config.yaml')
        else:
            system_file = Path('/etc/rapidwebs-agent/config.yaml')
        
        if not system_file.exists():
            self.logger.debug(f'System config not found: {system_file}')
            return None
        
        try:
            with open(system_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.logger.info(f'Loaded system config: {system_file}')
            return config
        except yaml.YAMLError as e:
            self.logger.error(f'Invalid YAML in system config: {e}')
            return None
        except Exception as e:
            self.logger.error(f'Failed to load system config: {e}')
            return None
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Returns:
            Default configuration dictionary
        """
        return {
            # Model configuration
            'default_model': 'qwen_coder',
            'token_budget': 100000,
            
            # Cache configuration
            'cache_enabled': True,
            'cache_ttl': 3600,  # 1 hour
            
            # Conversation configuration
            'conversation': {
                'auto_save': True,
                'auto_save_interval': 30
            },
            
            # TODO configuration
            'todo': {
                'enabled': True,
                'auto_create': True
            },
            
            # Approval workflow
            'approval': {
                'default_mode': 'default',
                'timeout_seconds': 300
            },
            
            # Logging
            'logging': {
                'level': 'INFO',
                'enabled': True,
                'console': True,
                'json_format': False
            },
            
            # Performance
            'performance': {
                'token_budget': 100000
            },
            
            # Output management
            'output_management': {
                'inline_max_bytes': 10000,
                'max_inline_lines': 20,
                'summary_max_bytes': 1000
            },
            
            # UI
            'ui': {
                'collapsible_tool_output': True,
                'default_collapsed_lines': 3,
                'show_output_hints': True
            }
        }
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries.
        
        Values from override take precedence. Nested dictionaries
        are merged recursively.
        
        Args:
            base: Base dictionary
            override: Dictionary with override values
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value
        
        return result


def load_config(cli_args: Optional[Dict] = None) -> Dict[str, Any]:
    """Convenience function to load configuration.
    
    Args:
        cli_args: Optional CLI arguments
        
    Returns:
        Merged configuration dictionary
    """
    loader = ConfigLayerLoader()
    return loader.load_all(cli_args=cli_args)

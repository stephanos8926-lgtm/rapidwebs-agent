"""Configuration management with multi-layer support and validation"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

# Import configuration layer loader
try:
    from .config_layers import ConfigLayerLoader
    LAYERS_AVAILABLE = True
except ImportError:
    ConfigLayerLoader = None
    LAYERS_AVAILABLE = False

@dataclass
class ModelConfig:
    """Configuration for a single LLM model"""
    enabled: bool = False
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_requests_per_day: int = 1000
    rate_limit: int = 60  # requests per minute
    timeout: int = 30  # seconds

@dataclass
class SkillConfig:
    """Configuration for agent skills"""
    enabled: bool = True
    whitelist: list = field(default_factory=list)
    max_execution_time: int = 30
    timeout: int = 10

@dataclass
class TokenMonitoringConfig:
    """Token usage monitoring settings"""
    enabled: bool = True
    daily_cost_cap: float = 0.00
    alert_threshold: float = 0.8

@dataclass
class PerformanceConfig:
    """Performance optimization settings"""
    streaming: bool = True
    parallel_tool_calls: bool = True
    max_concurrent_tools: int = 5
    cache_responses: bool = True
    cache_ttl: int = 3600
    token_budget: int = 100000  # Daily token budget (default: 100k)
    semantic_chunking: bool = True
    context_optimization: str = "aggressive"

@dataclass
class UIConfig:
    """User interface settings"""
    theme: str = "default"
    show_token_usage: bool = True
    show_cost_estimates: bool = True
    collapse_tool_output: bool = True
    output_preview_lines: int = 5

@dataclass
class AgentConfig:
    """Agent behavior settings"""
    default_approval_mode: str = "default"
    max_tool_iterations: int = 15
    auto_approve_safe: bool = False

class Config:
    """Main configuration manager"""

    DEFAULT_CONFIG = {
        'default_model': 'qwen_coder',
        'models': {
            'qwen_coder': {
                'enabled': True,
                'api_key': '',
                'base_url': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
                'model': 'qwen-coder',
                'max_requests_per_day': 2000,
                'rate_limit': 60,
                'timeout': 30
            },
            'gemini': {
                'enabled': False,
                'api_key': '',
                'base_url': 'https://generativelanguage.googleapis.com/v1beta/models',
                'model': 'gemini-2.5-flash',
                'max_requests_per_day': 1000,
                'timeout': 30
            },
            'openai_gpt4o': {
                'enabled': False,
                'api_key': '',
                'base_url': 'https://api.openai.com/v1',
                'model': 'gpt-4o',
                'max_requests_per_day': 1000,
                'rate_limit': 60,
                'timeout': 30
            },
            'openai_gpt4_turbo': {
                'enabled': False,
                'api_key': '',
                'base_url': 'https://api.openai.com/v1',
                'model': 'gpt-4-turbo',
                'max_requests_per_day': 1000,
                'rate_limit': 60,
                'timeout': 30
            },
            'anthropic_claude_sonnet': {
                'enabled': False,
                'api_key': '',
                'base_url': 'https://api.anthropic.com',
                'model': 'claude-sonnet-4-20250514',
                'max_requests_per_day': 1000,
                'rate_limit': 60,
                'timeout': 30
            },
            'openrouter': {
                'enabled': False,
                'api_key': '',
                'base_url': 'https://openrouter.ai/api/v1',
                'model': 'anthropic/claude-3.5-sonnet',  # Default OpenRouter model
                'max_requests_per_day': 1000,
                'rate_limit': 60,
                'timeout': 30
            }
        },
        'token_monitoring': {
            'enabled': True,
            'daily_cost_cap': 0.00,
            'alert_threshold': 0.8
        },
        'performance': {
            'streaming': True,
            'parallel_tool_calls': True,
            'max_concurrent_tools': 5,
            'cache_responses': True,
            'cache_ttl': 3600,
            'token_budget': 100000,  # Daily token budget (default: 100k)
            'semantic_chunking': True,
            'context_optimization': 'aggressive'
        },
        'skills': {
            'terminal_executor': {
                'enabled': True,
                'whitelist': ['ls', 'pwd', 'cat', 'grep', 'find', 'echo', 'which', 'git'],
                'max_execution_time': 30
            },
            'web_scraper': {
                'enabled': True,
                'user_agent': 'RapidWebs-Agent/1.0',
                'timeout': 10
            },
            'filesystem': {
                'enabled': True,
                'allowed_directories': ['~', './'],
                'max_file_size': 1048576,  # 1MB
                'operation_timeout': 30  # Timeout for individual operations (seconds)
            }
        },
        'ui': {
            'theme': 'default',
            'show_token_usage': True,
            'show_cost_estimates': True
        },
        'agent': {
            'default_approval_mode': 'default',
            'max_tool_iterations': 15,
            'auto_approve_safe': False
        },
        'logging': {
            'level': 'INFO',
            'file': '~/.local/share/rapidwebs-agent/logs/agent.log',
            'enabled': True,
            'console': True,
            'json_format': False,
            'max_bytes': 10485760,  # 10MB
            'backup_count': 5
        },
        'output_management': {
            'enabled': True,
            'inline_max_bytes': 2 * 1024,  # 2KB (reduced from 10KB to save TUI space)
            'summary_max_bytes': 512 * 1024,  # 512KB
            'max_inline_lines': 20,  # Reduced from 50 to save TUI space
            'context_lines': 30,
            'enable_summarization': True,
            'temp_file_retention_hours': 24
        },
        'tui': {
            'theme': 'dracula',
            'show_tool_cards': True,
            'collapsible_results': True,
            'max_inline_lines': 20  # Reduced from 50 to match output_management
        },
        'approval_workflow': {
            'timeout_seconds': 300,  # 5 minutes
            'fail_on_timeout': True,
            'log_decisions': True
        },
        'subagents': {
            'enabled': True,
            'max_concurrent': 3,
            'test_agent': {
                'command_timeout': 300,  # 5 minutes for test commands
                'max_output_size': 1024 * 1024  # 1MB
            }
        }
    }

    API_KEY_ENV_VARS = {
        'qwen_coder': 'RW_QWEN_API_KEY',
        'gemini': 'RW_GEMINI_API_KEY',
    }

    def __init__(self, config_path: Optional[str] = None, cli_args: Optional[Dict] = None):
        """Initialize configuration.
        
        Args:
            config_path: Optional path to config file (for backward compatibility)
            cli_args: Optional CLI arguments (highest priority layer)
        """
        self.config_path = config_path or self._default_config_path()
        self.cli_args = cli_args or {}
        self._config: Dict[str, Any] = {}
        
        # Use layer loader if available, otherwise fall back to old method
        if LAYERS_AVAILABLE:
            self._load_with_layers()
        else:
            self._load_config()
        
        self._load_api_keys_from_env()

    def _load_with_layers(self):
        """Load configuration using multi-layer loader."""
        loader = ConfigLayerLoader()
        self._config = loader.load_all(cli_args=self.cli_args)

    def _default_config_path(self) -> str:
        config_dir = Path.home() / '.config' / 'rapidwebs-agent'
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / 'config.yaml')

    def _load_config(self):
        """Legacy config loading (fallback if layers not available)."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
            self._merge_with_defaults()
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()

    def _merge_with_defaults(self):
        def merge_dict(defaults, loaded):
            result = defaults.copy()
            for key, value in loaded.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        self._config = merge_dict(self.DEFAULT_CONFIG, self._config)

    def _load_api_keys_from_env(self):
        models = self._config.get('models', {})
        for model_name, env_var in self.API_KEY_ENV_VARS.items():
            env_value = os.environ.get(env_var)
            if env_value:
                if model_name not in models:
                    models[model_name] = {}
                models[model_name]['api_key'] = env_value
                models[model_name]['enabled'] = True

    def save(self):
        config_to_save = self._config.copy()
        for model_name, env_var in self.API_KEY_ENV_VARS.items():
            if os.environ.get(env_var):
                if model_name in config_to_save.get('models', {}):
                    config_to_save['models'][model_name]['api_key'] = ''
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config_to_save, f, default_flow_style=False, sort_keys=False)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    @property
    def default_model(self) -> str:
        return self.get('default_model', 'qwen_coder')

    @property
    def models(self) -> Dict[str, ModelConfig]:
        models_config = self.get('models', {})
        return {
            name: ModelConfig(**config)
            for name, config in models_config.items()
        }

    @property
    def token_monitoring(self) -> TokenMonitoringConfig:
        cfg = self.get('token_monitoring', {})
        return TokenMonitoringConfig(**cfg)

    @property
    def performance(self) -> PerformanceConfig:
        cfg = self.get('performance', {})
        return PerformanceConfig(**cfg)

    @property
    def ui(self) -> UIConfig:
        cfg = self.get('ui', {})
        return UIConfig(**cfg)

    @property
    def agent(self) -> AgentConfig:
        cfg = self.get('agent', {})
        return AgentConfig(**cfg)

    def validate(self) -> bool:
        default = self.default_model
        models = self.models
        if default not in models or not models[default].enabled:
            return False
        if not models[default].api_key:
            return False
        return True

    def get_api_key_source(self, model_name: str) -> str:
        if model_name in self.API_KEY_ENV_VARS:
            env_var = self.API_KEY_ENV_VARS[model_name]
            if os.environ.get(env_var):
                return f"environment variable ({env_var})"
        return "config file"

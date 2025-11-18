"""
Configuration Loader
Loads configuration from config.yaml and environment variables
Environment variables take precedence over config file
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

class Config:
    """Centralized configuration management"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize configuration
        
        Args:
            config_file: Path to YAML config file
        """
        self.config_file = Path(config_file)
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"⚠️  Warning: Could not load config.yaml: {e}")
                self._config = {}
        else:
            # Use defaults if config file doesn't exist
            self._config = self._get_defaults()
    
    def _get_defaults(self) -> Dict:
        """Get default configuration"""
        return {
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'env': 'development'
            },
            'cors': {
                'allowed_origins': ['http://localhost:3000', 'http://localhost:8000']
            },
            'llm': {
                'provider': 'gemini',
                'use_llm': True
            },
            'retrieval': {
                'top_k': 5,
                'search_k_multiplier': 3,
                'field_filter_threshold': 3,
                'use_reranking': True
            },
            'scraper': {
                'max_concurrent_requests': 10,
                'cache_ttl_hours': 24,
                'request_timeout': 15,
                'auto_rebuild_index': True
            },
            'cache': {
                'enabled': True,
                'ttl_seconds': 3600,
                'max_size': 100
            },
            'logging': {
                'level': 'INFO',
                'format': 'json'
            },
            'health': {
                'check_index_validity': True,
                'check_data_freshness': True,
                'data_freshness_days': 7
            },
            'validation': {
                'max_query_length': 1000,
                'min_query_length': 1
            },
            'metrics': {
                'enabled': True,
                'use_database': True,
                'db_path': 'metrics/metrics.db'
            },
            'session': {
                'max_history': 20,
                'max_summary_length': 500,
                'use_redis': False,
                'redis_host': 'localhost',
                'redis_port': 6379
            },
            'redis': {
                'enabled': False,
                'host': 'localhost',
                'port': 6379,
                'db': 1,
                'decode_responses': False
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path (e.g., 'server.port')
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_with_env(self, key_path: str, env_var: Optional[str] = None, default: Any = None) -> Any:
        """
        Get configuration value, checking environment variable first
        
        Args:
            key_path: Dot-separated path in config file
            env_var: Environment variable name (optional)
            default: Default value if not found
            
        Returns:
            Configuration value (env var takes precedence)
        """
        # Check environment variable first
        if env_var and os.getenv(env_var):
            env_value = os.getenv(env_var)
            # Try to convert to appropriate type
            if env_value.lower() in ('true', 'false'):
                return env_value.lower() == 'true'
            try:
                return int(env_value)
            except ValueError:
                try:
                    return float(env_value)
                except ValueError:
                    return env_value
        
        # Fall back to config file
        return self.get(key_path, default)
    
    def get_list(self, key_path: str, env_var: Optional[str] = None, default: Optional[List] = None) -> List:
        """
        Get list configuration value
        
        Args:
            key_path: Dot-separated path
            env_var: Environment variable (comma-separated)
            default: Default list
            
        Returns:
            List of values
        """
        if default is None:
            default = []
        
        # Check environment variable first
        if env_var and os.getenv(env_var):
            env_value = os.getenv(env_var)
            return [item.strip() for item in env_value.split(',') if item.strip()]
        
        # Get from config file
        value = self.get(key_path, default)
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        return default
    
    # Convenience properties
    @property
    def server_host(self) -> str:
        return self.get('server.host', '0.0.0.0')
    
    @property
    def server_port(self) -> int:
        return self.get_with_env('server.port', 'PORT', 8000)
    
    @property
    def env(self) -> str:
        return self.get_with_env('server.env', 'ENV', 'development')
    
    @property
    def is_production(self) -> bool:
        return self.env.lower() == 'production'
    
    @property
    def allowed_origins(self) -> List[str]:
        return self.get_list('cors.allowed_origins', 'ALLOWED_ORIGINS', ['*'])
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        return os.getenv('GEMINI_API_KEY')
    
    @property
    def openai_api_key(self) -> Optional[str]:
        return os.getenv('OPENAI_API_KEY')
    
    @property
    def llm_provider(self) -> str:
        return self.get_with_env('llm.provider', 'LLM_PROVIDER', 'gemini')
    
    @property
    def use_llm(self) -> bool:
        return self.get_with_env('llm.use_llm', 'USE_LLM', True)
    
    @property
    def retrieval_top_k(self) -> int:
        return self.get('retrieval.top_k', 5)
    
    @property
    def cache_enabled(self) -> bool:
        return self.get('cache.enabled', True)
    
    @property
    def cache_ttl(self) -> int:
        return self.get('cache.ttl_seconds', 3600)
    
    @property
    def max_query_length(self) -> int:
        return self.get('validation.max_query_length', 1000)
    
    @property
    def log_level(self) -> str:
        return self.get_with_env('logging.level', 'LOG_LEVEL', 'INFO')

# Global config instance
_config_instance: Optional[Config] = None

def get_config() -> Config:
    """Get global config instance (singleton)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


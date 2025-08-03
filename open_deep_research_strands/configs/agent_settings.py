"""
Agent-specific settings and configuration.
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path

from ..exceptions import ConfigurationError


class AgentSettings:
    """Configuration settings for agents."""
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """
        Initialize agent settings.
        
        Args:
            config_data: Optional configuration dictionary
        """
        self._config = config_data or {}
        self._load_defaults()
    
    def _load_defaults(self) -> None:
        """Load default configuration values."""
        self._defaults = {
            "quality_thresholds": {
                "accuracy": float(os.getenv("AGENT_QUALITY_ACCURACY", "0.85")),
                "depth": float(os.getenv("AGENT_QUALITY_DEPTH", "0.80")),
                "completeness": float(os.getenv("AGENT_QUALITY_COMPLETENESS", "0.80")),
                "source_quality": float(os.getenv("AGENT_QUALITY_SOURCE", "0.90"))
            },
            "timeouts": {
                "task_execution": int(os.getenv("AGENT_TASK_TIMEOUT", "300")),  # 5 minutes
                "communication": int(os.getenv("AGENT_COMM_TIMEOUT", "30")),    # 30 seconds
                "initialization": int(os.getenv("AGENT_INIT_TIMEOUT", "60"))    # 1 minute
            },
            "retry_settings": {
                "max_retries": int(os.getenv("AGENT_MAX_RETRIES", "3")),
                "backoff_factor": float(os.getenv("AGENT_BACKOFF_FACTOR", "1.5")),
                "retry_delay": float(os.getenv("AGENT_RETRY_DELAY", "1.0"))
            },
            "concurrency": {
                "max_sub_agents": int(os.getenv("AGENT_MAX_SUB_AGENTS", "5")),
                "parallel_tasks": int(os.getenv("AGENT_PARALLEL_TASKS", "3"))
            },
            "memory_settings": {
                "max_memory_entries": int(os.getenv("AGENT_MAX_MEMORY", "1000")),
                "memory_cleanup_threshold": float(os.getenv("AGENT_MEMORY_CLEANUP", "0.8"))
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (supports nested keys with dots)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            keys = key.split('.')
            value = self._config
            
            # First try user config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    value = None
                    break
            
            # Fall back to defaults if not found
            if value is None:
                value = self._defaults
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
            
            return value
            
        except Exception as e:
            raise ConfigurationError(f"Error accessing config key '{key}': {str(e)}")
    
    def get_quality_thresholds(self) -> Dict[str, float]:
        """Get quality threshold settings."""
        return self.get("quality_thresholds", {})
    
    def get_timeouts(self) -> Dict[str, int]:
        """Get timeout settings."""
        return self.get("timeouts", {})
    
    def get_retry_settings(self) -> Dict[str, Any]:
        """Get retry settings."""
        return self.get("retry_settings", {})
    
    def get_concurrency_settings(self) -> Dict[str, int]:
        """Get concurrency settings."""
        return self.get("concurrency", {})
    
    def get_memory_settings(self) -> Dict[str, Any]:
        """Get memory settings."""
        return self.get("memory_settings", {})
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate quality thresholds
        thresholds = self.get_quality_thresholds()
        for key, value in thresholds.items():
            if not 0.0 <= value <= 1.0:
                raise ConfigurationError(
                    f"Quality threshold '{key}' must be between 0.0 and 1.0, got {value}"
                )
        
        # Validate timeouts
        timeouts = self.get_timeouts()
        for key, value in timeouts.items():
            if value <= 0:
                raise ConfigurationError(
                    f"Timeout '{key}' must be positive, got {value}"
                )
        
        # Validate concurrency settings
        concurrency = self.get_concurrency_settings()
        for key, value in concurrency.items():
            if value <= 0:
                raise ConfigurationError(
                    f"Concurrency setting '{key}' must be positive, got {value}"
                )
        
        return True


# Global settings instance
_agent_settings: Optional[AgentSettings] = None


def get_agent_settings(config_data: Optional[Dict[str, Any]] = None) -> AgentSettings:
    """
    Get global agent settings instance.
    
    Args:
        config_data: Optional configuration data to initialize with
        
    Returns:
        AgentSettings instance
    """
    global _agent_settings
    
    if _agent_settings is None:
        _agent_settings = AgentSettings(config_data)
        _agent_settings.validate()
    
    return _agent_settings


def load_agent_settings_from_file(config_path: Path) -> AgentSettings:
    """
    Load agent settings from a file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        AgentSettings instance
        
    Raises:
        ConfigurationError: If file cannot be loaded
    """
    try:
        import json
        
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix == '.json':
                config_data = json.load(f)
            else:
                # Support Python config files
                import importlib.util
                spec = importlib.util.spec_from_file_location("config", config_path)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                config_data = getattr(config_module, 'AGENT_CONFIG', {})
        
        return AgentSettings(config_data)
        
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration from {config_path}: {str(e)}")
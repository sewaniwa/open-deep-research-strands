"""
Local development configuration for Open Deep Research Strands.
"""
from pathlib import Path
from typing import Dict, Any

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Local development configuration
LOCAL_CONFIG: Dict[str, Any] = {
    # Runtime configuration
    "runtime": "strands_agents_local",
    "memory_backend": "file_based",
    "tool_mode": "mock",
    "debug_mode": True,
    "log_level": "DEBUG",
    
    # LLM provider configuration
    "llm_provider": "openai",  # Options: "openai", "anthropic", "local"
    "llm_config": {
        "openai": {
            "model": "gpt-4",
            "api_key_env": "OPENAI_API_KEY",
            "max_tokens": 4000,
            "temperature": 0.1,
        },
        "anthropic": {
            "model": "claude-3-sonnet",
            "api_key_env": "ANTHROPIC_API_KEY",
            "max_tokens": 4000,
            "temperature": 0.1,
        }
    },
    
    # Memory configuration
    "memory_config": {
        "storage_path": PROJECT_ROOT / "local_memory",
        "max_session_memory": "500MB",
        "retention_days": 30,
        "enable_semantic_search": False,  # Disabled for local development
    },
    
    # Agent configuration
    "agent_config": {
        "max_concurrent_agents": 5,
        "agent_timeout": 300,  # 5 minutes
        "max_iterations": 5,
        "resource_limits": {
            "supervisor": {"memory": "1GB", "cpu": "1vCPU"},
            "research_sub": {"memory": "512MB", "cpu": "0.5vCPU"},
            "scoping": {"memory": "256MB", "cpu": "0.25vCPU"},
            "report": {"memory": "512MB", "cpu": "0.5vCPU"},
        }
    },
    
    # Tool configuration
    "tool_config": {
        "web_search": {
            "provider": "mock",  # "mock", "serpapi", "bing"
            "max_results": 10,
            "timeout": 30,
        },
        "mcp_servers": {
            "enabled": False,  # Disabled for local development
            "servers": []
        }
    },
    
    # Communication configuration
    "communication_config": {
        "message_queue": "memory",  # "memory", "redis", "sqs"
        "max_message_size": "10MB",
        "message_retention": 3600,  # 1 hour
    },
    
    # Evaluation configuration
    "evaluation_config": {
        "enabled": True,
        "metrics": ["accuracy", "depth", "source_quality", "reasoning_clarity", "completeness"],
        "thresholds": {
            "accuracy": 0.85,
            "depth": 0.80,
            "source_quality": 0.90,
            "reasoning_clarity": 0.85,
            "completeness": 0.80
        }
    },
    
    # Paths
    "paths": {
        "project_root": PROJECT_ROOT,
        "src": PROJECT_ROOT / "src",
        "tests": PROJECT_ROOT / "tests",
        "configs": PROJECT_ROOT / "configs",
        "scripts": PROJECT_ROOT / "scripts",
        "local_memory": PROJECT_ROOT / "local_memory",
        "logs": PROJECT_ROOT / "logs",
    }
}


def get_config() -> Dict[str, Any]:
    """Get the local configuration dictionary."""
    return LOCAL_CONFIG.copy()


def get_llm_config(provider: str = None) -> Dict[str, Any]:
    """Get LLM configuration for specified provider."""
    if provider is None:
        provider = LOCAL_CONFIG["llm_provider"]
    
    return LOCAL_CONFIG["llm_config"].get(provider, {})


def get_paths() -> Dict[str, Path]:
    """Get project paths."""
    return LOCAL_CONFIG["paths"].copy()
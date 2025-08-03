"""
Strands Agents SDK configuration for local development.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StrandsRuntimeConfig:
    """Configuration for Strands Agents runtime."""
    runtime_mode: str = "local"
    session_isolation: bool = True
    max_session_duration: str = "8h"
    memory_limit: str = "4GB"
    cpu_allocation: str = "2vCPU"
    debug_mode: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)


@dataclass
class StrandsMemoryConfig:
    """Configuration for Strands memory system."""
    backend: str = "file_based"
    storage_path: Path = None
    max_session_memory: str = "500MB"
    retention_days: int = 30
    enable_semantic_search: bool = False
    namespace_isolation: bool = True
    
    def __post_init__(self):
        if self.storage_path is None:
            self.storage_path = Path(__file__).parent.parent.parent / "local_memory"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        data = asdict(self)
        data["storage_path"] = str(self.storage_path)
        return data


@dataclass
class StrandsAgentConfig:
    """Configuration for individual agents."""
    max_concurrent_agents: int = 5
    agent_timeout: int = 300  # 5 minutes
    max_iterations: int = 5
    resource_limits: Dict[str, Dict[str, str]] = None
    
    def __post_init__(self):
        if self.resource_limits is None:
            self.resource_limits = {
                "supervisor": {"memory": "1GB", "cpu": "1vCPU"},
                "research_sub": {"memory": "512MB", "cpu": "0.5vCPU"},
                "scoping": {"memory": "256MB", "cpu": "0.25vCPU"},
                "report": {"memory": "512MB", "cpu": "0.5vCPU"},
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)


class StrandsSDKManager:
    """Manager for Strands Agents SDK configuration and initialization."""
    
    def __init__(self, config_override: Dict[str, Any] = None):
        """
        Initialize Strands SDK Manager.
        
        Args:
            config_override: Optional configuration overrides
        """
        self.logger = get_logger(self.__class__.__name__)
        
        # Load configuration
        self.runtime_config = StrandsRuntimeConfig()
        self.memory_config = StrandsMemoryConfig()
        self.agent_config = StrandsAgentConfig()
        
        # Apply overrides if provided
        if config_override:
            self._apply_config_overrides(config_override)
        
        # Initialize SDK components
        self._initialized = False
        self._runtime = None
        self._memory_system = None
    
    def _apply_config_overrides(self, overrides: Dict[str, Any]):
        """Apply configuration overrides."""
        for key, value in overrides.items():
            if hasattr(self.runtime_config, key):
                setattr(self.runtime_config, key, value)
            elif hasattr(self.memory_config, key):
                setattr(self.memory_config, key, value)
            elif hasattr(self.agent_config, key):
                setattr(self.agent_config, key, value)
    
    async def initialize_sdk(self) -> bool:
        """
        Initialize the Strands Agents SDK.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing Strands Agents SDK", mode="local")
            
            # Initialize runtime (mock for local development)
            self._runtime = await self._initialize_local_runtime()
            
            # Initialize memory system
            self._memory_system = await self._initialize_memory_system()
            
            # Create necessary directories
            await self._setup_local_directories()
            
            self._initialized = True
            self.logger.info("Strands Agents SDK initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Strands SDK", error=str(e))
            return False
    
    async def _initialize_local_runtime(self):
        """Initialize local runtime (mock implementation)."""
        self.logger.debug("Initializing local runtime")
        
        # For local development, we'll use a mock runtime
        class MockStrandsRuntime:
            def __init__(self, config: StrandsRuntimeConfig):
                self.config = config
                self.sessions = {}
            
            async def create_session(self, agent_id: str, capabilities: list) -> str:
                session_id = f"session_{agent_id}_{len(self.sessions)}"
                self.sessions[session_id] = {
                    "agent_id": agent_id,
                    "capabilities": capabilities,
                    "status": "active"
                }
                return session_id
            
            async def terminate_session(self, session_id: str):
                if session_id in self.sessions:
                    self.sessions[session_id]["status"] = "terminated"
        
        return MockStrandsRuntime(self.runtime_config)
    
    async def _initialize_memory_system(self):
        """Initialize memory system."""
        self.logger.debug("Initializing memory system")
        
        # Ensure storage directory exists
        self.memory_config.storage_path.mkdir(parents=True, exist_ok=True)
        
        # For local development, we'll use a file-based memory system
        from ..tools.local_memory import LocalMemorySystem
        return LocalMemorySystem(self.memory_config)
    
    async def _setup_local_directories(self):
        """Set up necessary local directories."""
        directories = [
            self.memory_config.storage_path / "sessions",
            self.memory_config.storage_path / "cache",
            self.memory_config.storage_path / "temp",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {directory}")
    
    def get_runtime(self):
        """Get the runtime instance."""
        if not self._initialized:
            raise RuntimeError("SDK not initialized. Call initialize_sdk() first.")
        return self._runtime
    
    def get_memory_system(self):
        """Get the memory system instance."""
        if not self._initialized:
            raise RuntimeError("SDK not initialized. Call initialize_sdk() first.")
        return self._memory_system
    
    def is_initialized(self) -> bool:
        """Check if SDK is initialized."""
        return self._initialized
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        return {
            "runtime": self.runtime_config.to_dict(),
            "memory": self.memory_config.to_dict(),
            "agents": self.agent_config.to_dict(),
            "initialized": self._initialized
        }


# Global SDK manager instance
_sdk_manager: Optional[StrandsSDKManager] = None


def get_sdk_manager(config_override: Dict[str, Any] = None) -> StrandsSDKManager:
    """
    Get the global SDK manager instance.
    
    Args:
        config_override: Optional configuration overrides
        
    Returns:
        StrandsSDKManager instance
    """
    global _sdk_manager
    
    if _sdk_manager is None:
        _sdk_manager = StrandsSDKManager(config_override)
    
    return _sdk_manager


async def initialize_strands_sdk(config_override: Dict[str, Any] = None) -> bool:
    """
    Initialize the Strands Agents SDK.
    
    Args:
        config_override: Optional configuration overrides
        
    Returns:
        True if initialization successful, False otherwise
    """
    sdk_manager = get_sdk_manager(config_override)
    return await sdk_manager.initialize_sdk()
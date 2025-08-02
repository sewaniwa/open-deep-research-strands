"""
Base agent class for Open Deep Research Strands agents.
"""
import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from ..config.logging_config import LoggerMixin
from ..config.strands_config import get_sdk_manager
from ..tools.llm_interface import LLMManager, LLMMessage, create_message


@dataclass
class TaskData:
    """Represents task data passed to agents."""
    task_id: str
    task_type: str
    content: Dict[str, Any]
    priority: str = "normal"
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "content": self.content,
            "priority": self.priority,
            "metadata": self.metadata or {},
            "created_at": self.created_at
        }


@dataclass
class AgentResult:
    """Represents result from agent task execution."""
    agent_id: str
    task_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata or {},
            "completed_at": self.completed_at
        }


class BaseResearchAgent(ABC, LoggerMixin):
    """Base class for all research agents in the system."""
    
    def __init__(self, name: str, role: str, capabilities: List[str]):
        """
        Initialize base research agent.
        
        Args:
            name: Agent name/identifier
            role: Agent role description
            capabilities: List of agent capabilities
        """
        self.agent_id = f"{name}_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.role = role
        self.capabilities = capabilities
        
        # Session and state management
        self.session_id: Optional[str] = None
        self.is_active = False
        self.current_task: Optional[TaskData] = None
        
        # SDK components
        self.sdk_manager = get_sdk_manager()
        self.runtime = None
        self.memory_system = None
        self.llm_manager: Optional[LLMManager] = None
        
        # Performance tracking
        self.task_count = 0
        self.total_execution_time = 0.0
        self.last_activity = datetime.utcnow().isoformat()
        
        self.logger.info("Agent initialized", 
                        agent_id=self.agent_id, 
                        role=self.role, 
                        capabilities=self.capabilities)
    
    async def initialize(self, session_id: str = None) -> bool:
        """
        Initialize agent with SDK components.
        
        Args:
            session_id: Optional session identifier
            
        Returns:
            True if initialization successful
        """
        try:
            # Ensure SDK is initialized
            if not self.sdk_manager.is_initialized():
                await self.sdk_manager.initialize_sdk()
            
            # Get SDK components
            self.runtime = self.sdk_manager.get_runtime()
            self.memory_system = self.sdk_manager.get_memory_system()
            
            # Initialize LLM manager
            from ..configs.local_config import get_config
            config = get_config()
            self.llm_manager = LLMManager(config)
            
            # Create agent session
            if session_id:
                self.session_id = session_id
            else:
                self.session_id = await self.runtime.create_session(
                    self.agent_id, 
                    self.capabilities
                )
            
            # Create memory namespace for this agent
            await self.memory_system.create_namespace(
                f"agent_{self.agent_id}",
                retention_policy="session_end"
            )
            
            self.is_active = True
            self.logger.info("Agent initialized successfully", 
                           agent_id=self.agent_id,
                           session_id=self.session_id)
            
            return True
            
        except Exception as e:
            self.logger.error("Agent initialization failed", 
                            agent_id=self.agent_id, 
                            error=str(e))
            return False
    
    @abstractmethod
    async def execute_task(self, task_data: TaskData) -> AgentResult:
        """
        Execute a task assigned to this agent.
        
        Args:
            task_data: Task data to execute
            
        Returns:
            Result of task execution
        """
        pass
    
    async def process_message(self, messages: List[LLMMessage], 
                            context: Dict[str, Any] = None) -> str:
        """
        Process messages using LLM.
        
        Args:
            messages: Messages to process
            context: Optional context information
            
        Returns:
            LLM response content
        """
        if not self.llm_manager:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        try:
            # Add system context if provided
            if context:
                system_message = create_message(
                    "system", 
                    f"You are {self.role}. Context: {context}"
                )
                messages = [system_message] + messages
            
            response = await self.llm_manager.generate(messages)
            return response.content
            
        except Exception as e:
            self.logger.error("LLM processing failed", 
                            agent_id=self.agent_id, 
                            error=str(e))
            raise
    
    async def store_memory(self, key: str, data: Any, ttl: int = None) -> str:
        """
        Store data in agent's memory namespace.
        
        Args:
            key: Storage key
            data: Data to store
            ttl: Optional time-to-live in seconds
            
        Returns:
            Entry ID
        """
        if not self.memory_system:
            raise RuntimeError("Agent not initialized")
        
        namespace = f"agent_{self.agent_id}"
        return await self.memory_system.store(namespace, key, data, ttl=ttl)
    
    async def retrieve_memory(self, key: str) -> Any:
        """
        Retrieve data from agent's memory namespace.
        
        Args:
            key: Storage key
            
        Returns:
            Stored data or None if not found
        """
        if not self.memory_system:
            raise RuntimeError("Agent not initialized")
        
        namespace = f"agent_{self.agent_id}"
        return await self.memory_system.retrieve(namespace, key)
    
    async def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search agent's memory.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            Search results
        """
        if not self.memory_system:
            raise RuntimeError("Agent not initialized")
        
        namespace = f"agent_{self.agent_id}"
        return await self.memory_system.search(namespace, query, limit)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow().isoformat()
    
    async def shutdown(self):
        """Shutdown agent and cleanup resources."""
        try:
            if self.runtime and self.session_id:
                await self.runtime.terminate_session(self.session_id)
            
            self.is_active = False
            self.logger.info("Agent shutdown completed", agent_id=self.agent_id)
            
        except Exception as e:
            self.logger.error("Agent shutdown failed", 
                            agent_id=self.agent_id, 
                            error=str(e))
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status information."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "session_id": self.session_id,
            "is_active": self.is_active,
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "task_count": self.task_count,
            "total_execution_time": self.total_execution_time,
            "last_activity": self.last_activity
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        avg_execution_time = (
            self.total_execution_time / self.task_count 
            if self.task_count > 0 else 0.0
        )
        
        return {
            "task_count": self.task_count,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_execution_time,
            "last_activity": self.last_activity,
            "active_session": self.session_id is not None
        }
    
    async def _execute_with_timing(self, task_data: TaskData) -> AgentResult:
        """Execute task with timing and error handling."""
        start_time = asyncio.get_event_loop().time()
        self.current_task = task_data
        self.task_count += 1
        
        try:
            result = await self.execute_task(task_data)
            result.execution_time = asyncio.get_event_loop().time() - start_time
            self.total_execution_time += result.execution_time
            
            self.logger.info("Task completed successfully",
                           agent_id=self.agent_id,
                           task_id=task_data.task_id,
                           execution_time=result.execution_time)
            
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.total_execution_time += execution_time
            
            error_result = AgentResult(
                agent_id=self.agent_id,
                task_id=task_data.task_id,
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time
            )
            
            self.logger.error("Task execution failed",
                            agent_id=self.agent_id,
                            task_id=task_data.task_id,
                            error=str(e))
            
            return error_result
            
        finally:
            self.current_task = None
            self.update_activity()


class AgentCapabilityMixin:
    """Mixin class providing common agent capabilities."""
    
    async def validate_task_data(self, task_data: TaskData, 
                               required_fields: List[str]) -> bool:
        """
        Validate task data contains required fields.
        
        Args:
            task_data: Task data to validate
            required_fields: List of required field names
            
        Returns:
            True if valid, False otherwise
        """
        for field in required_fields:
            if field not in task_data.content:
                self.logger.error(f"Missing required field: {field}",
                                agent_id=self.agent_id,
                                task_id=task_data.task_id)
                return False
        return True
    
    async def log_task_progress(self, task_id: str, stage: str, 
                              details: Dict[str, Any] = None):
        """Log task progress information."""
        self.logger.info(f"Task progress: {stage}",
                        agent_id=self.agent_id,
                        task_id=task_id,
                        details=details or {})
    
    def create_result(self, task_id: str, success: bool, 
                     result: Any = None, error: str = None,
                     metadata: Dict[str, Any] = None) -> AgentResult:
        """Create a standardized agent result."""
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task_id,
            success=success,
            result=result,
            error=error,
            metadata=metadata
        )


def create_task_data(task_type: str, content: Dict[str, Any], 
                    priority: str = "normal",
                    metadata: Dict[str, Any] = None) -> TaskData:
    """
    Create task data with auto-generated ID.
    
    Args:
        task_type: Type of task
        content: Task content
        priority: Task priority
        metadata: Optional metadata
        
    Returns:
        TaskData instance
    """
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    return TaskData(
        task_id=task_id,
        task_type=task_type,
        content=content,
        priority=priority,
        metadata=metadata
    )
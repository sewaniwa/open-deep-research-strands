"""
Agent Manager for dynamic agent lifecycle management.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from .base_agent import BaseResearchAgent


class AgentStatus(Enum):
    """Agent status enumeration."""
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    BUSY = "busy"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class AgentPoolEntry:
    """Entry in the agent pool."""
    
    def __init__(self, agent: BaseResearchAgent, priority: str = "normal"):
        self.agent = agent
        self.priority = priority
        self.status = AgentStatus.INITIALIZING
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.task_count = 0
        self.total_execution_time = 0.0
        self.current_task_id = None
        
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
        
    def start_task(self, task_id: str):
        """Mark agent as starting a task."""
        self.current_task_id = task_id
        self.status = AgentStatus.ACTIVE
        self.update_activity()
        
    def complete_task(self, execution_time: float):
        """Mark agent as completing a task."""
        self.task_count += 1
        self.total_execution_time += execution_time
        self.current_task_id = None
        self.status = AgentStatus.READY
        self.update_activity()
        
    def fail_task(self, error: str):
        """Mark agent as failing a task."""
        self.current_task_id = None
        self.status = AgentStatus.FAILED
        self.update_activity()
        
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "agent_id": self.agent.agent_id,
            "agent_name": self.agent.name,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "task_count": self.task_count,
            "total_execution_time": self.total_execution_time,
            "current_task_id": self.current_task_id,
            "capabilities": self.agent.capabilities
        }


class AgentManager:
    """
    Manager for dynamic agent lifecycle and resource allocation.
    
    Responsibilities:
    - Agent spawning and termination
    - Agent pool management
    - Load balancing across agents
    - Agent monitoring and health checks
    - Resource allocation and limits
    """
    
    def __init__(self, supervisor: BaseResearchAgent):
        """
        Initialize Agent Manager.
        
        Args:
            supervisor: Supervisor agent that owns this manager
        """
        self.supervisor = supervisor
        self.agent_pool: Dict[str, AgentPoolEntry] = {}
        self.agent_counter = 0
        
        # Configuration - load from settings with fallback
        try:
            from configs.agent_settings import get_agent_settings
            settings = get_agent_settings()
            concurrency_settings = settings.get_concurrency_settings()
            self.max_concurrent_agents = concurrency_settings.get("max_sub_agents", 5)
            self.max_agent_lifetime = concurrency_settings.get("max_agent_lifetime", 3600)  # 1 hour
            self.agent_idle_timeout = concurrency_settings.get("agent_idle_timeout", 300)  # 5 minutes
        except ImportError:
            # Fallback configuration
            self.max_concurrent_agents = 5
            self.max_agent_lifetime = 3600  # 1 hour
            self.agent_idle_timeout = 300  # 5 minutes
        
        # Task queue for load balancing
        self.pending_tasks = asyncio.Queue()
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id
        
        # Monitoring
        self.health_check_interval = 30  # seconds
        self._monitoring_task = None
        
    async def start_monitoring(self):
        """Start agent monitoring task."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitor_agents())
    
    async def stop_monitoring(self):
        """Stop agent monitoring task."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
    
    async def spawn_research_agent(self, subtopic: str, priority: str = "normal") -> str:
        """
        Spawn a new research sub-agent.
        
        Args:
            subtopic: Research subtopic for the agent
            priority: Priority level (high, normal, low)
            
        Returns:
            Agent ID of the spawned agent
            
        Raises:
            RuntimeError: If unable to spawn agent due to resource limits
        """
        # Check if we've hit the concurrent agent limit
        active_agents = [
            entry for entry in self.agent_pool.values()
            if entry.status in [AgentStatus.READY, AgentStatus.ACTIVE, AgentStatus.BUSY]
        ]
        
        if len(active_agents) >= self.max_concurrent_agents:
            # Try to wait for a slot or reuse an existing agent
            available_agent_id = await self._find_available_agent(priority)
            if available_agent_id:
                return available_agent_id
            else:
                # Wait for completion of some agents
                await self._wait_for_agent_completion()
        
        # Generate unique agent ID
        agent_id = f"research_sub_{self.agent_counter}"
        self.agent_counter += 1
        
        try:
            # Create the research sub-agent
            # For now, we'll import and create the agent here
            # In the full implementation, this will use proper factory patterns
            from .research_sub_agent import ResearchSubAgent
            
            sub_agent = ResearchSubAgent(subtopic, agent_id)
            
            # Initialize the agent
            await sub_agent.initialize()
            
            # Add to pool
            pool_entry = AgentPoolEntry(sub_agent, priority)
            pool_entry.status = AgentStatus.READY
            self.agent_pool[agent_id] = pool_entry
            
            await self.supervisor.log_task_progress(
                self.supervisor.session_id or "unknown",
                "agent_spawned",
                {
                    "agent_id": agent_id,
                    "subtopic": subtopic,
                    "priority": priority,
                    "total_agents": len(self.agent_pool)
                }
            )
            
            return agent_id
            
        except Exception as e:
            self.supervisor.logger.error(
                f"Failed to spawn research agent for '{subtopic}': {str(e)}"
            )
            raise RuntimeError(f"Agent spawning failed: {str(e)}")
    
    async def _find_available_agent(self, priority: str) -> Optional[str]:
        """
        Find an available agent that can handle new tasks.
        
        Args:
            priority: Required priority level
            
        Returns:
            Agent ID if available, None otherwise
        """
        for agent_id, entry in self.agent_pool.items():
            if (entry.status == AgentStatus.READY and 
                entry.priority == priority):
                return agent_id
        return None
    
    async def _wait_for_agent_completion(self, timeout: float = 60.0):
        """
        Wait for at least one agent to complete its current task.
        
        Args:
            timeout: Maximum time to wait
            
        Raises:
            asyncio.TimeoutError: If no agent becomes available within timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            # Check if any agent has become available
            for entry in self.agent_pool.values():
                if entry.status == AgentStatus.READY:
                    return
            
            await asyncio.sleep(1.0)
        
        raise asyncio.TimeoutError("No agents became available within timeout")
    
    async def assign_task(self, agent_id: str, task_data: Any) -> bool:
        """
        Assign a task to a specific agent.
        
        Args:
            agent_id: ID of the agent to assign task to
            task_data: Task data to assign
            
        Returns:
            True if assignment successful, False otherwise
        """
        if agent_id not in self.agent_pool:
            return False
        
        entry = self.agent_pool[agent_id]
        
        if entry.status != AgentStatus.READY:
            return False
        
        try:
            entry.start_task(task_data.task_id)
            self.task_assignments[task_data.task_id] = agent_id
            
            # Execute the task asynchronously
            asyncio.create_task(self._execute_agent_task(agent_id, task_data))
            
            return True
            
        except Exception as e:
            entry.fail_task(str(e))
            return False
    
    async def _execute_agent_task(self, agent_id: str, task_data: Any):
        """
        Execute a task on an agent with proper lifecycle management.
        
        Args:
            agent_id: Agent ID
            task_data: Task to execute
        """
        entry = self.agent_pool[agent_id]
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Execute the task
            result = await entry.agent.execute_task(task_data)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            entry.complete_task(execution_time)
            
            # Remove from task assignments
            if task_data.task_id in self.task_assignments:
                del self.task_assignments[task_data.task_id]
            
            await self.supervisor.log_task_progress(
                self.supervisor.session_id or "unknown",
                "agent_task_completed",
                {
                    "agent_id": agent_id,
                    "task_id": task_data.task_id,
                    "execution_time": execution_time,
                    "success": result.success
                }
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            entry.fail_task(str(e))
            
            # Remove from task assignments
            if task_data.task_id in self.task_assignments:
                del self.task_assignments[task_data.task_id]
            
            await self.supervisor.log_task_progress(
                self.supervisor.session_id or "unknown",
                "agent_task_failed",
                {
                    "agent_id": agent_id,
                    "task_id": task_data.task_id,
                    "execution_time": execution_time,
                    "error": str(e)
                }
            )
    
    async def terminate_agent(self, agent_id: str, reason: str = "normal_termination"):
        """
        Terminate a specific agent.
        
        Args:
            agent_id: Agent ID to terminate
            reason: Reason for termination
        """
        if agent_id not in self.agent_pool:
            return
        
        entry = self.agent_pool[agent_id]
        
        try:
            # Cancel current task if any
            if entry.current_task_id:
                await entry.agent.cancel_current_task()
            
            # Shutdown the agent
            await entry.agent.shutdown()
            entry.status = AgentStatus.TERMINATED
            
            await self.supervisor.log_task_progress(
                self.supervisor.session_id or "unknown",
                "agent_terminated",
                {
                    "agent_id": agent_id,
                    "reason": reason,
                    "task_count": entry.task_count,
                    "total_execution_time": entry.total_execution_time
                }
            )
            
        except Exception as e:
            self.supervisor.logger.error(
                f"Error terminating agent {agent_id}: {str(e)}"
            )
        
        finally:
            # Remove from pool
            del self.agent_pool[agent_id]
    
    async def terminate_all_agents(self, reason: str = "session_cleanup"):
        """
        Terminate all agents in the pool.
        
        Args:
            reason: Reason for termination
        """
        agent_ids = list(self.agent_pool.keys())
        
        # Terminate all agents concurrently
        await asyncio.gather(
            *[self.terminate_agent(agent_id, reason) for agent_id in agent_ids],
            return_exceptions=True
        )
    
    async def _monitor_agents(self):
        """Background task to monitor agent health and lifecycle."""
        while True:
            try:
                current_time = datetime.utcnow()
                agents_to_terminate = []
                
                for agent_id, entry in self.agent_pool.items():
                    # Check for idle timeout
                    idle_time = (current_time - entry.last_activity).total_seconds()
                    if (idle_time > self.agent_idle_timeout and 
                        entry.status == AgentStatus.READY):
                        agents_to_terminate.append((agent_id, "idle_timeout"))
                    
                    # Check for lifetime timeout
                    lifetime = (current_time - entry.created_at).total_seconds()
                    if lifetime > self.max_agent_lifetime:
                        agents_to_terminate.append((agent_id, "lifetime_exceeded"))
                    
                    # Check for failed agents
                    if entry.status == AgentStatus.FAILED:
                        agents_to_terminate.append((agent_id, "failed_status"))
                
                # Terminate agents that need cleanup
                for agent_id, reason in agents_to_terminate:
                    await self.terminate_agent(agent_id, reason)
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.supervisor.logger.error(f"Agent monitoring error: {str(e)}")
                await asyncio.sleep(self.health_check_interval)
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current status of the agent pool.
        
        Returns:
            Agent pool status information
        """
        status_counts = {}
        for status in AgentStatus:
            status_counts[status.value] = 0
        
        agent_info = []
        for entry in self.agent_pool.values():
            status_counts[entry.status.value] += 1
            agent_info.append(entry.get_info())
        
        return {
            "total_agents": len(self.agent_pool),
            "status_counts": status_counts,
            "max_concurrent_agents": self.max_concurrent_agents,
            "pending_tasks": self.pending_tasks.qsize(),
            "active_assignments": len(self.task_assignments),
            "agents": agent_info
        }
    
    async def shutdown(self):
        """Shutdown the agent manager and all managed agents."""
        await self.stop_monitoring()
        await self.terminate_all_agents("manager_shutdown")
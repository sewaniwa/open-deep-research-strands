"""
Research Swarm Controller for coordinating parallel research execution.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..agents.base_agent import BaseResearchAgent, TaskData
from ..config.logging_config import LoggerMixin


class ResearchSwarmController(LoggerMixin):
    """
    Controller for coordinating parallel research execution across multiple agents.
    
    Responsibilities:
    - Coordinate parallel research execution
    - Manage task distribution and load balancing
    - Aggregate and synchronize results
    - Handle agent failures and recovery
    """
    
    def __init__(self, supervisor: BaseResearchAgent):
        """
        Initialize Research Swarm Controller.
        
        Args:
            supervisor: Supervisor agent that owns this controller
        """
        self.supervisor = supervisor
        
        # Configuration with fallback
        try:
            from configs.agent_settings import get_agent_settings
            settings = get_agent_settings()
            concurrency_settings = settings.get_concurrency_settings()
            swarm_settings = settings.get_swarm_settings()
            
            # Use concurrency settings for parallel limits
            self.concurrent_limit = concurrency_settings.get("parallel_tasks", 3)
            
            # Use swarm settings for task-specific configuration
            self.task_timeout = swarm_settings.get("task_timeout", 300)
            self.effort_multipliers = swarm_settings.get("effort_multipliers", {
                "low": 1.0, "medium": 2.0, "high": 3.0
            })
            self.confidence_thresholds = swarm_settings.get("confidence_thresholds", {
                "high_relevance": 0.9,
                "medium_relevance": 0.85,
                "default_confidence": 0.85
            })
        except ImportError:
            # Fallback configuration
            self.concurrent_limit = 3
            self.task_timeout = 300  # 5 minutes
            self.effort_multipliers = {"low": 1.0, "medium": 2.0, "high": 3.0}
            self.confidence_thresholds = {
                "high_relevance": 0.9,
                "medium_relevance": 0.85,
                "default_confidence": 0.85
            }
        
        # Task management
        self.research_queue = asyncio.Queue()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_results: Dict[str, Any] = {}
        self.failed_tasks: Dict[str, str] = {}
        
        # Synchronization
        self.result_lock = asyncio.Lock()
        self.coordination_semaphore = asyncio.Semaphore(self.concurrent_limit)
    
    async def coordinate_parallel_research(self, subtopics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Coordinate parallel research across multiple subtopics.
        
        Args:
            subtopics: List of subtopic dictionaries to research
            
        Returns:
            Aggregated research results
        """
        self.log_method_entry("coordinate_parallel_research", 
                            subtopic_count=len(subtopics),
                            concurrent_limit=self.concurrent_limit)
        
        if not subtopics:
            self.logger.warning("No subtopics provided for parallel research")
            return {"subtopic_results": {}, "coordination_summary": "No subtopics provided"}
        
        await self.supervisor.log_task_progress(
            self.supervisor.session_id or "unknown",
            "parallel_research_started",
            {
                "subtopic_count": len(subtopics),
                "concurrent_limit": self.concurrent_limit
            }
        )
        
        try:
            # Create research tasks for each subtopic
            research_tasks = []
            for subtopic in subtopics:
                task = self._create_subtopic_research_task(subtopic)
                research_tasks.append(task)
            
            # Execute research tasks with concurrency control
            results = await self._execute_research_tasks(research_tasks)
            
            # Process and aggregate results
            aggregated_results = await self._aggregate_research_results(results)
            
            # Log structured success information
            self.logger.info("Parallel research completed successfully",
                           method="coordinate_parallel_research",
                           successful_tasks=len(aggregated_results.get("subtopic_results", {})),
                           failed_tasks=len(self.failed_tasks),
                           total_execution_time=aggregated_results.get("total_execution_time", 0))
            
            await self.supervisor.log_task_progress(
                self.supervisor.session_id or "unknown",
                "parallel_research_completed",
                {
                    "successful_tasks": len(aggregated_results.get("subtopic_results", {})),
                    "failed_tasks": len(self.failed_tasks),
                    "total_execution_time": aggregated_results.get("total_execution_time", 0)
                }
            )
            
            self.log_method_exit("coordinate_parallel_research", 
                               result_count=len(aggregated_results.get("subtopic_results", {})))
            return aggregated_results
            
        except Exception as e:
            self.logger.error("Parallel research execution failed",
                            method="coordinate_parallel_research",
                            error_type=type(e).__name__,
                            error_message=str(e),
                            subtopic_count=len(subtopics))
            
            await self.supervisor.log_task_progress(
                self.supervisor.session_id or "unknown",
                "parallel_research_failed",
                {"error": str(e)}
            )
            raise
    
    def _create_subtopic_research_task(self, subtopic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a research task for a specific subtopic.
        
        Args:
            subtopic: Subtopic information
            
        Returns:
            Task configuration
        """
        task_id = f"research_task_{subtopic.get('id', 'unknown')}"
        
        return {
            "task_id": task_id,
            "subtopic": subtopic,
            "priority": subtopic.get("priority", "normal"),
            "estimated_effort": subtopic.get("estimated_effort", "medium"),
            "created_at": datetime.utcnow()
        }
    
    async def _execute_research_tasks(self, research_tasks: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute research tasks with proper concurrency control.
        
        Args:
            research_tasks: List of research task configurations
            
        Returns:
            List of task results
        """
        # Sort tasks by priority
        priority_order = {"high": 0, "normal": 1, "low": 2}
        research_tasks.sort(key=lambda t: priority_order.get(t.get("priority", "normal"), 1))
        
        # Create semaphore-controlled execution tasks
        execution_tasks = []
        for task_config in research_tasks:
            execution_task = self._execute_subtopic_research(task_config)
            execution_tasks.append(execution_task)
        
        # Execute all tasks concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*execution_tasks, return_exceptions=True),
                timeout=self.task_timeout * len(research_tasks)  # Total timeout
            )
            
            return results
            
        except asyncio.TimeoutError:
            # Handle timeout - cancel remaining tasks
            for task in execution_tasks:
                if not task.done():
                    task.cancel()
            
            # Collect completed results
            results = []
            for task in execution_tasks:
                try:
                    if task.done():
                        results.append(task.result())
                    else:
                        results.append(Exception("Task cancelled due to timeout"))
                except Exception as e:
                    results.append(e)
            
            return results
    
    async def _execute_subtopic_research(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute research for a single subtopic with semaphore control.
        
        Args:
            task_config: Task configuration
            
        Returns:
            Research result for the subtopic
        """
        async with self.coordination_semaphore:
            task_id = task_config["task_id"]
            subtopic = task_config["subtopic"]
            
            start_time = asyncio.get_event_loop().time()
            
            try:
                # For Phase 1, simulate research execution
                # In Phase 2, this will use actual ResearchSubAgent
                result = await self._simulate_subtopic_research_execution(subtopic)
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                # Store result
                async with self.result_lock:
                    self.completed_results[task_id] = {
                        "task_id": task_id,
                        "subtopic_id": subtopic.get("id"),
                        "result": result,
                        "execution_time": execution_time,
                        "completed_at": datetime.utcnow().isoformat()
                    }
                
                await self.supervisor.log_task_progress(
                    self.supervisor.session_id or "unknown",
                    "subtopic_research_completed",
                    {
                        "task_id": task_id,
                        "subtopic_id": subtopic.get("id"),
                        "execution_time": execution_time
                    }
                )
                
                return self.completed_results[task_id]
                
            except Exception as e:
                execution_time = asyncio.get_event_loop().time() - start_time
                error_msg = str(e)
                
                # Store failure
                async with self.result_lock:
                    self.failed_tasks[task_id] = error_msg
                
                await self.supervisor.log_task_progress(
                    self.supervisor.session_id or "unknown",
                    "subtopic_research_failed",
                    {
                        "task_id": task_id,
                        "subtopic_id": subtopic.get("id"),
                        "error": error_msg,
                        "execution_time": execution_time
                    }
                )
                
                # Return error result
                return {
                    "task_id": task_id,
                    "subtopic_id": subtopic.get("id"),
                    "error": error_msg,
                    "execution_time": execution_time,
                    "failed_at": datetime.utcnow().isoformat()
                }
    
    async def _simulate_subtopic_research_execution(self, subtopic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate research execution for a subtopic (Phase 1 implementation).
        
        Args:
            subtopic: Subtopic to research
            
        Returns:
            Simulated research result
        """
        # Simulate variable execution time based on effort
        base_time = self.effort_multipliers.get(
            subtopic.get("estimated_effort", "medium"), 
            self.effort_multipliers.get("medium", 2.0)
        )
        
        await asyncio.sleep(base_time)  # Simulate work
        
        # Generate simulated result
        result = {
            "subtopic_id": subtopic.get("id"),
            "title": subtopic.get("title", "Unknown Subtopic"),
            "analysis": f"Detailed analysis of {subtopic.get('title', 'the subtopic')}. "
                      f"This covers {subtopic.get('description', 'important aspects')} "
                      f"with comprehensive insights and findings.",
            "key_findings": [
                f"Key finding 1 for {subtopic.get('title', 'subtopic')}",
                f"Important insight 2 about {subtopic.get('title', 'subtopic')}",
                f"Significant observation 3 regarding {subtopic.get('title', 'subtopic')}"
            ],
            "sources": [
                {
                    "title": f"Academic Source for {subtopic.get('title', 'topic')}",
                    "url": "https://example.com/academic1",
                    "relevance": self.confidence_thresholds.get("high_relevance", 0.9)
                },
                {
                    "title": f"Research Paper on {subtopic.get('title', 'topic')}",
                    "url": "https://example.com/paper1",
                    "relevance": self.confidence_thresholds.get("medium_relevance", 0.85)
                }
            ],
            "confidence_score": self.confidence_thresholds.get("default_confidence", 0.85),
            "research_method": "parallel_swarm_research"
        }
        
        return result
    
    async def _aggregate_research_results(self, task_results: List[Any]) -> Dict[str, Any]:
        """
        Aggregate results from parallel research tasks.
        
        Args:
            task_results: List of task results (including exceptions)
            
        Returns:
            Aggregated research results
        """
        successful_results = {}
        failed_results = {}
        total_execution_time = 0.0
        
        for result in task_results:
            if isinstance(result, Exception):
                # Handle exception results
                error_id = f"unknown_error_{len(failed_results)}"
                failed_results[error_id] = str(result)
                continue
            
            if isinstance(result, dict):
                if "error" in result:
                    # Handle error results
                    task_id = result.get("task_id", f"error_{len(failed_results)}")
                    failed_results[task_id] = result["error"]
                else:
                    # Handle successful results
                    subtopic_id = result.get("subtopic_id", result.get("task_id", "unknown"))
                    successful_results[subtopic_id] = result.get("result", result)
                    total_execution_time += result.get("execution_time", 0.0)
        
        # Calculate quality metrics
        if successful_results:
            confidence_scores = [
                result.get("confidence_score", 0.0) 
                for result in successful_results.values()
                if isinstance(result, dict)
            ]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        else:
            avg_confidence = 0.0
        
        aggregated_results = {
            "subtopic_results": successful_results,
            "failed_tasks": failed_results,
            "coordination_summary": {
                "total_tasks": len(task_results),
                "successful_tasks": len(successful_results),
                "failed_tasks": len(failed_results),
                "success_rate": len(successful_results) / len(task_results) if task_results else 0.0,
                "average_confidence": avg_confidence,
                "concurrent_limit": self.concurrent_limit
            },
            "total_execution_time": total_execution_time,
            "aggregated_at": datetime.utcnow().isoformat()
        }
        
        return aggregated_results
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """
        Get current coordination status.
        
        Returns:
            Coordination status information
        """
        return {
            "concurrent_limit": self.concurrent_limit,
            "active_tasks": len(self.active_tasks),
            "completed_results": len(self.completed_results),
            "failed_tasks": len(self.failed_tasks),
            "queue_size": self.research_queue.qsize(),
            "semaphore_available": self.coordination_semaphore._value
        }
    
    async def shutdown(self):
        """Shutdown the swarm controller and clean up resources."""
        # Cancel all active tasks
        for task in self.active_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for cancellation to complete
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        
        # Clear state
        self.active_tasks.clear()
        self.completed_results.clear()
        self.failed_tasks.clear()
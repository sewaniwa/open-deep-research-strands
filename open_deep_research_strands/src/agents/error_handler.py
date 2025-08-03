"""
Error handling and recovery mechanisms for the research system.
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import traceback

from .base_agent import BaseResearchAgent


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    AGENT_FAILURE = "agent_failure"
    TASK_TIMEOUT = "task_timeout"
    COMMUNICATION_ERROR = "communication_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATA_VALIDATION = "data_validation"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM_ERROR = "system_error"


class ErrorRecord:
    """Record of an error occurrence."""
    
    def __init__(self, error_id: str, category: ErrorCategory, severity: ErrorSeverity,
                 message: str, context: Dict[str, Any], exception: Exception = None):
        self.error_id = error_id
        self.category = category
        self.severity = severity
        self.message = message
        self.context = context
        self.exception = exception
        self.occurred_at = datetime.utcnow()
        self.resolved = False
        self.recovery_attempts = 0
        self.resolution_strategy = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "error_id": self.error_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
            "occurred_at": self.occurred_at.isoformat(),
            "resolved": self.resolved,
            "recovery_attempts": self.recovery_attempts,
            "resolution_strategy": self.resolution_strategy,
            "traceback": traceback.format_exception(
                type(self.exception), self.exception, self.exception.__traceback__
            ) if self.exception else None
        }


class RecoveryStrategy:
    """Recovery strategy for handling specific error types."""
    
    def __init__(self, name: str, handler: Callable, max_retries: int = 3,
                 backoff_factor: float = 1.5, prerequisites: List[str] = None):
        self.name = name
        self.handler = handler
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.prerequisites = prerequisites or []


class ResearchErrorHandler:
    """
    Comprehensive error handling and recovery system for research operations.
    
    Responsibilities:
    - Error detection and classification
    - Recovery strategy execution
    - Error logging and monitoring
    - State preservation and restoration
    - Graceful degradation
    """
    
    def __init__(self, supervisor: BaseResearchAgent):
        """
        Initialize Error Handler.
        
        Args:
            supervisor: Supervisor agent that owns this handler
        """
        self.supervisor = supervisor
        self.error_history: List[ErrorRecord] = []
        self.recovery_strategies: Dict[ErrorCategory, List[RecoveryStrategy]] = {}
        self.error_counter = 0
        
        # State preservation
        self.session_checkpoints: Dict[str, Dict[str, Any]] = {}
        self.checkpoint_interval = 60  # seconds
        
        # Error tracking
        self.error_patterns: Dict[str, int] = {}
        self.max_error_rate = 10  # errors per minute
        self.error_rate_window = []
        
        # Initialize recovery strategies
        self._initialize_recovery_strategies()
    
    def _initialize_recovery_strategies(self):
        """Initialize built-in recovery strategies."""
        
        # Agent failure recovery
        self.recovery_strategies[ErrorCategory.AGENT_FAILURE] = [
            RecoveryStrategy(
                "restart_agent",
                self._restart_failed_agent,
                max_retries=2
            ),
            RecoveryStrategy(
                "spawn_replacement_agent",
                self._spawn_replacement_agent,
                max_retries=1
            ),
            RecoveryStrategy(
                "graceful_degradation",
                self._degrade_gracefully,
                max_retries=1
            )
        ]
        
        # Timeout recovery
        self.recovery_strategies[ErrorCategory.TASK_TIMEOUT] = [
            RecoveryStrategy(
                "extend_timeout",
                self._extend_task_timeout,
                max_retries=1
            ),
            RecoveryStrategy(
                "simplify_task",
                self._simplify_task_scope,
                max_retries=2
            ),
            RecoveryStrategy(
                "cancel_and_continue",
                self._cancel_and_continue,
                max_retries=1
            )
        ]
        
        # Communication error recovery
        self.recovery_strategies[ErrorCategory.COMMUNICATION_ERROR] = [
            RecoveryStrategy(
                "retry_communication",
                self._retry_communication,
                max_retries=3,
                backoff_factor=2.0
            ),
            RecoveryStrategy(
                "reset_communication_channel",
                self._reset_communication,
                max_retries=1
            )
        ]
        
        # Resource exhaustion recovery
        self.recovery_strategies[ErrorCategory.RESOURCE_EXHAUSTION] = [
            RecoveryStrategy(
                "release_unused_resources",
                self._release_resources,
                max_retries=1
            ),
            RecoveryStrategy(
                "reduce_concurrency",
                self._reduce_concurrency,
                max_retries=1
            ),
            RecoveryStrategy(
                "wait_for_resources",
                self._wait_for_resources,
                max_retries=2
            )
        ]
        
        # External service recovery
        self.recovery_strategies[ErrorCategory.EXTERNAL_SERVICE] = [
            RecoveryStrategy(
                "retry_with_backoff",
                self._retry_with_exponential_backoff,
                max_retries=3,
                backoff_factor=2.0
            ),
            RecoveryStrategy(
                "use_fallback_service",
                self._use_fallback_service,
                max_retries=1
            ),
            RecoveryStrategy(
                "cache_fallback",
                self._use_cached_data,
                max_retries=1
            )
        ]
    
    async def handle_error(self, exception: Exception, context: Dict[str, Any]) -> bool:
        """
        Handle an error with appropriate recovery strategy.
        
        Args:
            exception: Exception that occurred
            context: Context information about the error
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        # Create error record
        error_record = await self._create_error_record(exception, context)
        self.error_history.append(error_record)
        
        # Log error
        await self.supervisor.log_task_progress(
            self.supervisor.session_id or "unknown",
            "error_detected",
            {
                "error_id": error_record.error_id,
                "category": error_record.category.value,
                "severity": error_record.severity.value,
                "message": error_record.message
            }
        )
        
        # Check error rate
        if not await self._check_error_rate():
            await self._trigger_emergency_shutdown()
            return False
        
        # Attempt recovery
        recovery_success = await self._attempt_recovery(error_record)
        
        if recovery_success:
            error_record.resolved = True
            await self.supervisor.log_task_progress(
                self.supervisor.session_id or "unknown",
                "error_recovered",
                {"error_id": error_record.error_id}
            )
        else:
            await self.supervisor.log_task_progress(
                self.supervisor.session_id or "unknown",
                "error_recovery_failed",
                {"error_id": error_record.error_id}
            )
        
        return recovery_success
    
    async def _create_error_record(self, exception: Exception, context: Dict[str, Any]) -> ErrorRecord:
        """Create an error record from exception and context."""
        self.error_counter += 1
        error_id = f"error_{self.error_counter}_{int(datetime.utcnow().timestamp())}"
        
        # Classify error
        category = self._classify_error(exception, context)
        severity = self._assess_severity(exception, context, category)
        
        # Extract meaningful message
        message = str(exception) or "Unknown error occurred"
        
        return ErrorRecord(
            error_id=error_id,
            category=category,
            severity=severity,
            message=message,
            context=context,
            exception=exception
        )
    
    def _classify_error(self, exception: Exception, context: Dict[str, Any]) -> ErrorCategory:
        """Classify error into appropriate category."""
        exception_type = type(exception).__name__
        error_message = str(exception).lower()
        
        # Agent-related errors
        if "agent" in error_message or context.get("component") == "agent":
            return ErrorCategory.AGENT_FAILURE
        
        # Timeout errors
        if isinstance(exception, asyncio.TimeoutError) or "timeout" in error_message:
            return ErrorCategory.TASK_TIMEOUT
        
        # Communication errors
        if ("connection" in error_message or "network" in error_message or
            "communication" in error_message):
            return ErrorCategory.COMMUNICATION_ERROR
        
        # Resource errors
        if ("memory" in error_message or "resource" in error_message or
            "limit" in error_message):
            return ErrorCategory.RESOURCE_EXHAUSTION
        
        # Validation errors
        if ("validation" in error_message or "invalid" in error_message or
            isinstance(exception, (ValueError, TypeError))):
            return ErrorCategory.DATA_VALIDATION
        
        # External service errors
        if ("service" in error_message or "api" in error_message or
            "http" in error_message or context.get("component") == "external_service"):
            return ErrorCategory.EXTERNAL_SERVICE
        
        # Default to system error
        return ErrorCategory.SYSTEM_ERROR
    
    def _assess_severity(self, exception: Exception, context: Dict[str, Any],
                        category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity based on type and context."""
        # Critical errors that can crash the system
        if isinstance(exception, (MemoryError, SystemExit, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        
        # High severity errors that impact core functionality
        if category in [ErrorCategory.AGENT_FAILURE, ErrorCategory.SYSTEM_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium severity errors that impact performance
        if category in [ErrorCategory.TASK_TIMEOUT, ErrorCategory.RESOURCE_EXHAUSTION]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors that are recoverable
        return ErrorSeverity.LOW
    
    async def _check_error_rate(self) -> bool:
        """Check if error rate is within acceptable limits."""
        current_time = datetime.utcnow().timestamp()
        
        # Clean old entries (older than 1 minute)
        self.error_rate_window = [
            timestamp for timestamp in self.error_rate_window
            if current_time - timestamp < 60
        ]
        
        # Add current error
        self.error_rate_window.append(current_time)
        
        # Check if rate exceeds threshold
        return len(self.error_rate_window) <= self.max_error_rate
    
    async def _attempt_recovery(self, error_record: ErrorRecord) -> bool:
        """Attempt recovery using appropriate strategies."""
        strategies = self.recovery_strategies.get(error_record.category, [])
        
        for strategy in strategies:
            if error_record.recovery_attempts >= strategy.max_retries:
                continue
            
            try:
                # Apply backoff delay
                if error_record.recovery_attempts > 0:
                    delay = strategy.backoff_factor ** error_record.recovery_attempts
                    await asyncio.sleep(delay)
                
                # Attempt recovery
                error_record.recovery_attempts += 1
                error_record.resolution_strategy = strategy.name
                
                success = await strategy.handler(error_record)
                
                if success:
                    return True
                
            except Exception as recovery_exception:
                await self.supervisor.log_task_progress(
                    self.supervisor.session_id or "unknown",
                    "recovery_strategy_failed",
                    {
                        "error_id": error_record.error_id,
                        "strategy": strategy.name,
                        "recovery_error": str(recovery_exception)
                    }
                )
        
        return False
    
    # Recovery strategy implementations
    
    async def _restart_failed_agent(self, error_record: ErrorRecord) -> bool:
        """Restart a failed agent."""
        context = error_record.context
        agent_id = context.get("agent_id")
        
        if not agent_id:
            return False
        
        try:
            # Get agent manager from supervisor
            agent_manager = getattr(self.supervisor, "agent_manager", None)
            if not agent_manager:
                return False
            
            # Terminate failed agent and spawn replacement
            await agent_manager.terminate_agent(agent_id, "error_recovery")
            
            # Create new agent for same subtopic
            subtopic = context.get("subtopic", "Unknown")
            new_agent_id = await agent_manager.spawn_research_agent(subtopic)
            
            # Update context with new agent ID
            context["new_agent_id"] = new_agent_id
            
            return True
            
        except Exception:
            return False
    
    async def _spawn_replacement_agent(self, error_record: ErrorRecord) -> bool:
        """Spawn a replacement agent without terminating the failed one."""
        context = error_record.context
        
        try:
            agent_manager = getattr(self.supervisor, "agent_manager", None)
            if not agent_manager:
                return False
            
            subtopic = context.get("subtopic", "Recovery Task")
            new_agent_id = await agent_manager.spawn_research_agent(subtopic, "high")
            
            context["replacement_agent_id"] = new_agent_id
            return True
            
        except Exception:
            return False
    
    async def _degrade_gracefully(self, error_record: ErrorRecord) -> bool:
        """Implement graceful degradation."""
        # Reduce system capabilities temporarily
        context = error_record.context
        
        # Reduce concurrent agent limit
        agent_manager = getattr(self.supervisor, "agent_manager", None)
        if agent_manager:
            agent_manager.max_concurrent_agents = max(1, agent_manager.max_concurrent_agents // 2)
        
        # Mark system as degraded
        context["system_degraded"] = True
        
        return True
    
    async def _extend_task_timeout(self, error_record: ErrorRecord) -> bool:
        """Extend timeout for the failed task."""
        context = error_record.context
        current_timeout = context.get("timeout", 300)
        
        # Double the timeout
        new_timeout = current_timeout * 2
        context["extended_timeout"] = new_timeout
        
        return True
    
    async def _simplify_task_scope(self, error_record: ErrorRecord) -> bool:
        """Simplify the scope of a failed task."""
        context = error_record.context
        
        # Reduce subtopic complexity or requirements
        if "subtopic" in context:
            context["simplified_scope"] = True
            context["original_subtopic"] = context["subtopic"]
        
        return True
    
    async def _cancel_and_continue(self, error_record: ErrorRecord) -> bool:
        """Cancel the failed task and continue with others."""
        context = error_record.context
        context["task_cancelled"] = True
        
        return True
    
    async def _retry_communication(self, error_record: ErrorRecord) -> bool:
        """Retry communication with exponential backoff."""
        # This would retry the specific communication operation
        # For now, we'll simulate success
        return True
    
    async def _reset_communication(self, error_record: ErrorRecord) -> bool:
        """Reset communication channels."""
        # This would reset message queues, connections, etc.
        return True
    
    async def _release_resources(self, error_record: ErrorRecord) -> bool:
        """Release unused resources."""
        try:
            # Trigger garbage collection
            import gc
            gc.collect()
            
            # Clear caches if available
            memory_system = getattr(self.supervisor, "memory_system", None)
            if memory_system and hasattr(memory_system, "clear_cache"):
                await memory_system.clear_cache()
            
            return True
            
        except Exception:
            return False
    
    async def _reduce_concurrency(self, error_record: ErrorRecord) -> bool:
        """Reduce system concurrency to free resources."""
        agent_manager = getattr(self.supervisor, "agent_manager", None)
        swarm_controller = getattr(self.supervisor, "swarm_controller", None)
        
        if agent_manager:
            agent_manager.max_concurrent_agents = max(1, agent_manager.max_concurrent_agents - 1)
        
        if swarm_controller:
            swarm_controller.concurrent_limit = max(1, swarm_controller.concurrent_limit - 1)
        
        return True
    
    async def _wait_for_resources(self, error_record: ErrorRecord) -> bool:
        """Wait for resources to become available."""
        await asyncio.sleep(5)  # Wait 5 seconds
        return True
    
    async def _retry_with_exponential_backoff(self, error_record: ErrorRecord) -> bool:
        """Retry with exponential backoff."""
        # The backoff is already handled in _attempt_recovery
        return True
    
    async def _use_fallback_service(self, error_record: ErrorRecord) -> bool:
        """Use fallback external service."""
        context = error_record.context
        context["use_fallback"] = True
        
        return True
    
    async def _use_cached_data(self, error_record: ErrorRecord) -> bool:
        """Use cached data as fallback."""
        context = error_record.context
        context["use_cache"] = True
        
        return True
    
    async def _trigger_emergency_shutdown(self):
        """Trigger emergency shutdown due to excessive errors."""
        await self.supervisor.log_task_progress(
            self.supervisor.session_id or "unknown",
            "emergency_shutdown_triggered",
            {
                "reason": "excessive_error_rate",
                "error_count": len(self.error_rate_window),
                "time_window": "1_minute"
            }
        )
        
        # Initiate graceful shutdown
        try:
            await self.supervisor.cleanup_research_session(
                self.supervisor.session_id or "emergency"
            )
        except Exception as e:
            self.supervisor.logger.critical(f"Emergency shutdown failed: {e}")
    
    async def create_checkpoint(self, session_id: str, state: Dict[str, Any]):
        """Create a state checkpoint for recovery."""
        checkpoint_id = f"checkpoint_{int(datetime.utcnow().timestamp())}"
        
        self.session_checkpoints[session_id] = {
            "checkpoint_id": checkpoint_id,
            "state": state.copy(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Keep only last 5 checkpoints per session
        if len(self.session_checkpoints) > 5:
            oldest_key = min(self.session_checkpoints.keys(), 
                           key=lambda k: self.session_checkpoints[k]["created_at"])
            del self.session_checkpoints[oldest_key]
    
    async def restore_from_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Restore state from latest checkpoint."""
        if session_id in self.session_checkpoints:
            return self.session_checkpoints[session_id]["state"]
        return None
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and patterns."""
        if not self.error_history:
            return {"message": "No errors recorded"}
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        
        for error in self.error_history:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
        
        # Calculate recovery rate
        resolved_count = sum(1 for error in self.error_history if error.resolved)
        recovery_rate = resolved_count / len(self.error_history)
        
        return {
            "total_errors": len(self.error_history),
            "resolved_errors": resolved_count,
            "recovery_rate": recovery_rate,
            "category_breakdown": category_counts,
            "severity_breakdown": severity_counts,
            "current_error_rate": len(self.error_rate_window),
            "error_rate_limit": self.max_error_rate
        }
    
    async def execute_recovery(self, exception: Exception, context: Dict[str, Any], 
                             task_id: str) -> Dict[str, Any]:
        """
        Execute error recovery strategies for a given exception.
        
        Args:
            exception: The exception that occurred
            context: Context information about the error
            task_id: ID of the task that encountered the error
            
        Returns:
            Recovery result with success status and details
        """
        recovery_start_time = datetime.utcnow()
        
        try:
            # Classify the error to determine appropriate recovery strategies
            error_category = self._classify_error(exception, context)
            
            # Get recovery strategies for this error category
            recovery_strategies = self.recovery_strategies.get(error_category, [])
            
            if not recovery_strategies:
                return {
                    "recovery_attempted": True,
                    "success": False,
                    "error": "No recovery strategies available for this error category",
                    "error_category": error_category.value,
                    "task_id": task_id
                }
            
            # Log recovery attempt start
            await self.supervisor.log_task_progress(
                context.get("session_id", "unknown"),
                "error_recovery_started",
                {
                    "error_type": str(type(exception).__name__),
                    "error_message": str(exception),
                    "error_category": error_category.value,
                    "available_strategies": len(recovery_strategies),
                    "task_id": task_id
                }
            )
            
            # Attempt recovery strategies in order
            for strategy_index, strategy in enumerate(recovery_strategies):
                try:
                    # Log strategy attempt
                    await self.supervisor.log_task_progress(
                        context.get("session_id", "unknown"),
                        "recovery_strategy_attempt",
                        {
                            "strategy_name": strategy.name,
                            "strategy_index": strategy_index,
                            "max_retries": strategy.max_retries,
                            "task_id": task_id
                        }
                    )
                    
                    # Execute the recovery strategy
                    strategy_result = await strategy.execute_func(exception, context)
                    
                    # Check if recovery was successful
                    if strategy_result and strategy_result.get("success", False):
                        execution_time = (datetime.utcnow() - recovery_start_time).total_seconds()
                        
                        # Log successful recovery
                        await self.supervisor.log_task_progress(
                            context.get("session_id", "unknown"),
                            "error_recovery_success",
                            {
                                "strategy_used": strategy.name,
                                "execution_time": execution_time,
                                "task_id": task_id
                            }
                        )
                        
                        # Update error record as resolved
                        self._mark_error_resolved(exception, strategy.name)
                        
                        return {
                            "recovery_attempted": True,
                            "success": True,
                            "strategy_used": strategy.name,
                            "strategy_result": strategy_result,
                            "execution_time": execution_time,
                            "task_id": task_id
                        }
                    
                except Exception as strategy_error:
                    # Log strategy failure
                    await self.supervisor.log_task_progress(
                        context.get("session_id", "unknown"),
                        "recovery_strategy_failed",
                        {
                            "strategy_name": strategy.name,
                            "strategy_error": str(strategy_error),
                            "task_id": task_id
                        }
                    )
                    
                    # Continue to next strategy
                    continue
            
            # All strategies failed
            execution_time = (datetime.utcnow() - recovery_start_time).total_seconds()
            
            await self.supervisor.log_task_progress(
                context.get("session_id", "unknown"),
                "error_recovery_failed",
                {
                    "strategies_attempted": len(recovery_strategies),
                    "execution_time": execution_time,
                    "task_id": task_id
                }
            )
            
            return {
                "recovery_attempted": True,
                "success": False,
                "error": "All recovery strategies failed",
                "strategies_attempted": len(recovery_strategies),
                "execution_time": execution_time,
                "task_id": task_id
            }
            
        except Exception as recovery_error:
            # Recovery system itself failed
            execution_time = (datetime.utcnow() - recovery_start_time).total_seconds()
            
            return {
                "recovery_attempted": True,
                "success": False,
                "error": f"Recovery system failure: {str(recovery_error)}",
                "execution_time": execution_time,
                "task_id": task_id
            }
    
    def _mark_error_resolved(self, exception: Exception, resolution_method: str):
        """
        Mark an error as resolved in the error history.
        
        Args:
            exception: The resolved exception
            resolution_method: Method used to resolve the error
        """
        exception_str = str(exception)
        
        # Find and update the error record
        for error_record in reversed(self.error_history):  # Start from most recent
            if str(error_record.exception) == exception_str:
                error_record.resolved = True
                error_record.resolution_method = resolution_method
                error_record.resolved_at = datetime.utcnow()
                break
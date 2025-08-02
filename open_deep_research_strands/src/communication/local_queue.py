"""
Local message queue system for A2A communication.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, AsyncIterator
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass
from enum import Enum

from .messages import A2AMessage, MessageStatus, MessagePriority
from ..config.logging_config import LoggerMixin


class QueueType(Enum):
    """Types of message queues."""
    PRIORITY = "priority"        # Priority-based queue
    FIFO = "fifo"               # First-in-first-out queue
    TOPIC = "topic"             # Topic-based routing
    DIRECT = "direct"           # Direct agent-to-agent


@dataclass
class QueueConfiguration:
    """Configuration for message queues."""
    max_size: int = 1000
    persistence_enabled: bool = False
    persistence_path: Optional[Path] = None
    message_ttl: int = 3600  # 1 hour default
    auto_acknowledge: bool = True
    batch_size: int = 10
    consumer_timeout: float = 30.0


class LocalMessageQueue(LoggerMixin):
    """
    Local message queue implementation for development and testing.
    
    Provides priority queuing, persistence, and consumer management.
    """
    
    def __init__(self, queue_name: str, queue_type: QueueType = QueueType.PRIORITY,
                 config: QueueConfiguration = None):
        """
        Initialize local message queue.
        
        Args:
            queue_name: Name of the queue
            queue_type: Type of queue behavior
            config: Queue configuration
        """
        self.queue_name = queue_name
        self.queue_type = queue_type
        self.config = config or QueueConfiguration()
        
        # Message storage
        self.messages: Dict[MessagePriority, deque] = {
            MessagePriority.URGENT: deque(),
            MessagePriority.HIGH: deque(),
            MessagePriority.NORMAL: deque(),
            MessagePriority.LOW: deque()
        }
        
        # Consumer management
        self.consumers: Dict[str, Callable] = {}
        self.consumer_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self.stats = {
            "messages_enqueued": 0,
            "messages_dequeued": 0,
            "messages_acknowledged": 0,
            "messages_rejected": 0,
            "consumers_active": 0
        }
        
        # Persistence
        self.persistence_file = None
        if self.config.persistence_enabled and self.config.persistence_path:
            self.persistence_file = self.config.persistence_path / f"{queue_name}.jsonl"
            self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Control
        self.is_running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        self.logger.info("Local message queue initialized",
                        queue_name=queue_name,
                        queue_type=queue_type.value,
                        persistence=self.config.persistence_enabled)
    
    async def start(self):
        """Start the message queue."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Load persisted messages
        if self.config.persistence_enabled:
            await self._load_persisted_messages()
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("Message queue started", queue_name=self.queue_name)
    
    async def stop(self):
        """Stop the message queue."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop all consumers
        for consumer_id in list(self.consumer_tasks.keys()):
            await self.remove_consumer(consumer_id)
        
        # Stop cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Persist remaining messages
        if self.config.persistence_enabled:
            await self._persist_messages()
        
        self.logger.info("Message queue stopped", queue_name=self.queue_name)
    
    async def enqueue(self, message: A2AMessage) -> bool:
        """
        Add message to queue.
        
        Args:
            message: Message to enqueue
            
        Returns:
            True if message was enqueued successfully
        """
        try:
            # Check queue capacity
            total_messages = sum(len(queue) for queue in self.messages.values())
            if total_messages >= self.config.max_size:
                self.logger.warning("Queue full, rejecting message",
                                  queue_name=self.queue_name,
                                  message_id=message.message_id)
                return False
            
            # Check message expiration
            if message.is_expired():
                self.logger.warning("Message expired, rejecting",
                                  queue_name=self.queue_name,
                                  message_id=message.message_id)
                return False
            
            # Add to appropriate priority queue
            priority = message.priority
            self.messages[priority].append(message)
            
            # Update statistics
            self.stats["messages_enqueued"] += 1
            
            # Persist if enabled
            if self.config.persistence_enabled:
                await self._persist_message(message)
            
            self.logger.debug("Message enqueued",
                            queue_name=self.queue_name,
                            message_id=message.message_id,
                            priority=priority.value)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to enqueue message",
                            queue_name=self.queue_name,
                            message_id=getattr(message, 'message_id', 'unknown'),
                            error=str(e))
            return False
    
    async def dequeue(self, timeout: float = None) -> Optional[A2AMessage]:
        """
        Get next message from queue.
        
        Args:
            timeout: Maximum time to wait for message
            
        Returns:
            Next message or None if timeout/empty
        """
        start_time = asyncio.get_event_loop().time()
        timeout = timeout or self.config.consumer_timeout
        
        while self.is_running:
            # Try to get message from priority queues
            for priority in [MessagePriority.URGENT, MessagePriority.HIGH, 
                           MessagePriority.NORMAL, MessagePriority.LOW]:
                if self.messages[priority]:
                    message = self.messages[priority].popleft()
                    
                    # Check if message is still valid
                    if message.is_expired():
                        self.logger.debug("Expired message removed from queue",
                                        message_id=message.message_id)
                        continue
                    
                    self.stats["messages_dequeued"] += 1
                    
                    self.logger.debug("Message dequeued",
                                    queue_name=self.queue_name,
                                    message_id=message.message_id,
                                    priority=priority.value)
                    
                    return message
            
            # Check timeout
            if timeout > 0:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    break
            
            # Wait briefly before checking again
            await asyncio.sleep(0.1)
        
        return None
    
    async def peek(self, count: int = 1) -> List[A2AMessage]:
        """
        Peek at next messages without removing them.
        
        Args:
            count: Number of messages to peek at
            
        Returns:
            List of next messages (up to count)
        """
        messages = []
        
        for priority in [MessagePriority.URGENT, MessagePriority.HIGH,
                        MessagePriority.NORMAL, MessagePriority.LOW]:
            queue = self.messages[priority]
            
            for message in list(queue):
                if len(messages) >= count:
                    break
                
                if not message.is_expired():
                    messages.append(message)
            
            if len(messages) >= count:
                break
        
        return messages
    
    def get_size(self) -> Dict[str, int]:
        """Get queue size by priority."""
        return {
            "urgent": len(self.messages[MessagePriority.URGENT]),
            "high": len(self.messages[MessagePriority.HIGH]),
            "normal": len(self.messages[MessagePriority.NORMAL]),
            "low": len(self.messages[MessagePriority.LOW]),
            "total": sum(len(queue) for queue in self.messages.values())
        }
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return all(len(queue) == 0 for queue in self.messages.values())
    
    async def clear(self):
        """Clear all messages from queue."""
        for queue in self.messages.values():
            queue.clear()
        
        self.logger.info("Queue cleared", queue_name=self.queue_name)
    
    async def add_consumer(self, consumer_id: str, handler: Callable,
                          auto_start: bool = True) -> bool:
        """
        Add message consumer.
        
        Args:
            consumer_id: Unique consumer identifier
            handler: Message handler function
            auto_start: Whether to start consuming immediately
            
        Returns:
            True if consumer was added successfully
        """
        if consumer_id in self.consumers:
            self.logger.warning("Consumer already exists",
                              consumer_id=consumer_id)
            return False
        
        self.consumers[consumer_id] = handler
        
        if auto_start:
            await self.start_consumer(consumer_id)
        
        self.logger.info("Consumer added",
                        queue_name=self.queue_name,
                        consumer_id=consumer_id)
        
        return True
    
    async def remove_consumer(self, consumer_id: str) -> bool:
        """
        Remove message consumer.
        
        Args:
            consumer_id: Consumer identifier
            
        Returns:
            True if consumer was removed
        """
        if consumer_id not in self.consumers:
            return False
        
        # Stop consumer task
        if consumer_id in self.consumer_tasks:
            task = self.consumer_tasks[consumer_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.consumer_tasks[consumer_id]
        
        # Remove consumer
        del self.consumers[consumer_id]
        
        self.logger.info("Consumer removed",
                        queue_name=self.queue_name,
                        consumer_id=consumer_id)
        
        return True
    
    async def start_consumer(self, consumer_id: str) -> bool:
        """
        Start message consumer.
        
        Args:
            consumer_id: Consumer identifier
            
        Returns:
            True if consumer was started
        """
        if consumer_id not in self.consumers:
            return False
        
        if consumer_id in self.consumer_tasks:
            return True  # Already running
        
        handler = self.consumers[consumer_id]
        task = asyncio.create_task(self._consumer_loop(consumer_id, handler))
        self.consumer_tasks[consumer_id] = task
        
        self.stats["consumers_active"] += 1
        
        self.logger.info("Consumer started",
                        queue_name=self.queue_name,
                        consumer_id=consumer_id)
        
        return True
    
    async def stop_consumer(self, consumer_id: str) -> bool:
        """
        Stop message consumer.
        
        Args:
            consumer_id: Consumer identifier
            
        Returns:
            True if consumer was stopped
        """
        if consumer_id not in self.consumer_tasks:
            return False
        
        task = self.consumer_tasks[consumer_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        del self.consumer_tasks[consumer_id]
        self.stats["consumers_active"] -= 1
        
        self.logger.info("Consumer stopped",
                        queue_name=self.queue_name,
                        consumer_id=consumer_id)
        
        return True
    
    async def _consumer_loop(self, consumer_id: str, handler: Callable):
        """Consumer message processing loop."""
        while self.is_running:
            try:
                # Get next message
                message = await self.dequeue(timeout=1.0)
                
                if message is None:
                    continue
                
                # Process message
                try:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(message)
                    else:
                        result = handler(message)
                    
                    # Handle acknowledgment
                    if self.config.auto_acknowledge or result is True:
                        await self.acknowledge_message(message)
                    elif result is False:
                        await self.reject_message(message)
                
                except Exception as e:
                    self.logger.error("Consumer handler failed",
                                    consumer_id=consumer_id,
                                    message_id=message.message_id,
                                    error=str(e))
                    await self.reject_message(message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Consumer loop error",
                                consumer_id=consumer_id,
                                error=str(e))
                await asyncio.sleep(1.0)  # Back off on error
    
    async def acknowledge_message(self, message: A2AMessage):
        """Acknowledge message processing."""
        message.status = MessageStatus.ACKNOWLEDGED
        self.stats["messages_acknowledged"] += 1
        
        self.logger.debug("Message acknowledged",
                        message_id=message.message_id)
    
    async def reject_message(self, message: A2AMessage, requeue: bool = False):
        """Reject message processing."""
        message.status = MessageStatus.FAILED
        self.stats["messages_rejected"] += 1
        
        if requeue and message.can_retry():
            # Re-add to queue for retry
            await self.enqueue(message)
            self.logger.debug("Message requeued after rejection",
                            message_id=message.message_id)
        else:
            self.logger.debug("Message rejected",
                            message_id=message.message_id)
    
    async def _cleanup_loop(self):
        """Cleanup expired messages periodically."""
        while self.is_running:
            try:
                await self._cleanup_expired_messages()
                await asyncio.sleep(60.0)  # Run every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Cleanup loop error", error=str(e))
                await asyncio.sleep(10.0)
    
    async def _cleanup_expired_messages(self):
        """Remove expired messages from queues."""
        total_removed = 0
        
        for priority, queue in self.messages.items():
            removed_count = 0
            new_queue = deque()
            
            while queue:
                message = queue.popleft()
                if not message.is_expired():
                    new_queue.append(message)
                else:
                    removed_count += 1
            
            self.messages[priority] = new_queue
            total_removed += removed_count
        
        if total_removed > 0:
            self.logger.info("Removed expired messages",
                           queue_name=self.queue_name,
                           count=total_removed)
    
    async def _persist_message(self, message: A2AMessage):
        """Persist single message to file."""
        if not self.persistence_file:
            return
        
        try:
            with open(self.persistence_file, 'a') as f:
                f.write(message.to_json() + '\n')
        except Exception as e:
            self.logger.error("Failed to persist message",
                            message_id=message.message_id,
                            error=str(e))
    
    async def _persist_messages(self):
        """Persist all current messages to file."""
        if not self.persistence_file:
            return
        
        try:
            with open(self.persistence_file, 'w') as f:
                for priority_queue in self.messages.values():
                    for message in priority_queue:
                        f.write(message.to_json() + '\n')
        except Exception as e:
            self.logger.error("Failed to persist messages", error=str(e))
    
    async def _load_persisted_messages(self):
        """Load persisted messages from file."""
        if not self.persistence_file or not self.persistence_file.exists():
            return
        
        try:
            loaded_count = 0
            with open(self.persistence_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            message = A2AMessage.from_json(line)
                            if not message.is_expired():
                                self.messages[message.priority].append(message)
                                loaded_count += 1
                        except Exception as e:
                            self.logger.warning("Failed to load message", error=str(e))
            
            self.logger.info("Loaded persisted messages",
                           queue_name=self.queue_name,
                           count=loaded_count)
            
        except Exception as e:
            self.logger.error("Failed to load persisted messages", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        size_info = self.get_size()
        
        return {
            **self.stats,
            **size_info,
            "queue_name": self.queue_name,
            "queue_type": self.queue_type.value,
            "is_running": self.is_running,
            "consumers": len(self.consumers),
            "active_consumers": len(self.consumer_tasks)
        }


class LocalQueueManager(LoggerMixin):
    """Manager for multiple local message queues."""
    
    def __init__(self):
        """Initialize queue manager."""
        self.queues: Dict[str, LocalMessageQueue] = {}
        self.default_config = QueueConfiguration()
        
        self.logger.info("Local queue manager initialized")
    
    async def create_queue(self, queue_name: str, queue_type: QueueType = QueueType.PRIORITY,
                          config: QueueConfiguration = None) -> LocalMessageQueue:
        """
        Create or get existing queue.
        
        Args:
            queue_name: Name of the queue
            queue_type: Type of queue
            config: Queue configuration
            
        Returns:
            LocalMessageQueue instance
        """
        if queue_name in self.queues:
            return self.queues[queue_name]
        
        queue_config = config or self.default_config
        queue = LocalMessageQueue(queue_name, queue_type, queue_config)
        
        self.queues[queue_name] = queue
        await queue.start()
        
        self.logger.info("Queue created", queue_name=queue_name)
        return queue
    
    async def get_queue(self, queue_name: str) -> Optional[LocalMessageQueue]:
        """Get existing queue."""
        return self.queues.get(queue_name)
    
    async def delete_queue(self, queue_name: str) -> bool:
        """Delete queue."""
        if queue_name not in self.queues:
            return False
        
        queue = self.queues[queue_name]
        await queue.stop()
        del self.queues[queue_name]
        
        self.logger.info("Queue deleted", queue_name=queue_name)
        return True
    
    async def shutdown_all(self):
        """Shutdown all queues."""
        for queue_name in list(self.queues.keys()):
            await self.delete_queue(queue_name)
        
        self.logger.info("All queues shutdown")
    
    def list_queues(self) -> List[str]:
        """List all queue names."""
        return list(self.queues.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all queues."""
        return {
            queue_name: queue.get_stats()
            for queue_name, queue in self.queues.items()
        }


# Global queue manager instance
_global_queue_manager: Optional[LocalQueueManager] = None


def get_global_queue_manager() -> LocalQueueManager:
    """Get or create global queue manager."""
    global _global_queue_manager
    if _global_queue_manager is None:
        _global_queue_manager = LocalQueueManager()
    return _global_queue_manager
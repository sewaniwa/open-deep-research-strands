"""
Message routing system for A2A communication.
"""
import asyncio
import weakref
from typing import Dict, List, Optional, Callable, Set, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

from .messages import A2AMessage, MessageType, MessageStatus, MessagePriority
from ..config.logging_config import LoggerMixin


class MessageRoute:
    """Represents a routing rule for messages."""
    
    def __init__(self, pattern: str, handler: Callable, priority: int = 0):
        """
        Initialize message route.
        
        Args:
            pattern: Routing pattern (e.g., "task_assignment.*", "*.supervisor_*")
            handler: Handler function for messages matching this route
            priority: Route priority (higher = more priority)
        """
        self.pattern = pattern
        self.handler = handler
        self.priority = priority
        self.match_count = 0
        self.last_matched = None
    
    def matches(self, message: A2AMessage) -> bool:
        """Check if message matches this route."""
        routing_key = message.get_routing_key()
        return self._pattern_match(self.pattern, routing_key)
    
    def _pattern_match(self, pattern: str, key: str) -> bool:
        """Pattern matching with wildcard support."""
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return pattern == key
        
        # Convert pattern to regex-like matching
        pattern_parts = pattern.split(".")
        key_parts = key.split(".")
        
        return self._match_parts(pattern_parts, key_parts)
    
    def _match_parts(self, pattern_parts: List[str], key_parts: List[str]) -> bool:
        """Match pattern parts against key parts."""
        i, j = 0, 0
        
        while i < len(pattern_parts) and j < len(key_parts):
            pattern_part = pattern_parts[i]
            
            if pattern_part == "*":
                # Single part wildcard
                i += 1
                j += 1
            elif pattern_part == "**":
                # Multi-part wildcard
                if i == len(pattern_parts) - 1:
                    # Last pattern part, match remaining
                    return True
                # Skip to next matching part
                next_pattern = pattern_parts[i + 1]
                while j < len(key_parts) and key_parts[j] != next_pattern:
                    j += 1
                i += 1
            else:
                # Exact match required
                if pattern_part != key_parts[j]:
                    return False
                i += 1
                j += 1
        
        # Check if we've consumed all parts
        return i == len(pattern_parts) and j == len(key_parts)


class MessageRouter(LoggerMixin):
    """
    Core message routing system for A2A communication.
    
    Handles message routing, delivery, retries, and dead letter queues.
    """
    
    def __init__(self, router_id: str = None):
        """Initialize message router."""
        self.router_id = router_id or f"router_{id(self)}"
        
        # Routing table
        self.routes: List[MessageRoute] = []
        self.agent_handlers: Dict[str, Callable] = {}
        self.broadcast_handlers: Set[Callable] = set()
        
        # Message queues
        self.pending_messages: deque = deque()
        self.retry_queue: deque = deque()
        self.dead_letter_queue: deque = deque()
        
        # Statistics and monitoring
        self.stats = {
            "messages_routed": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "messages_retried": 0,
            "routes_registered": 0
        }
        
        # Configuration
        self.max_queue_size = 10000
        self.retry_delay = 5.0  # seconds
        self.dead_letter_ttl = 3600  # 1 hour
        
        # Processing control
        self.is_running = False
        self.processing_task: Optional[asyncio.Task] = None
        
        self.logger.info("Message router initialized", router_id=self.router_id)
    
    def register_route(self, pattern: str, handler: Callable, priority: int = 0):
        """
        Register a message route.
        
        Args:
            pattern: Routing pattern
            handler: Message handler function
            priority: Route priority
        """
        route = MessageRoute(pattern, handler, priority)
        self.routes.append(route)
        
        # Sort routes by priority (higher first)
        self.routes.sort(key=lambda r: r.priority, reverse=True)
        
        self.stats["routes_registered"] += 1
        
        self.logger.info("Route registered",
                        pattern=pattern,
                        priority=priority,
                        total_routes=len(self.routes))
    
    def register_agent_handler(self, agent_id: str, handler: Callable):
        """Register handler for specific agent."""
        self.agent_handlers[agent_id] = handler
        self.logger.info("Agent handler registered", agent_id=agent_id)
    
    def unregister_agent_handler(self, agent_id: str):
        """Unregister agent handler."""
        if agent_id in self.agent_handlers:
            del self.agent_handlers[agent_id]
            self.logger.info("Agent handler unregistered", agent_id=agent_id)
    
    def register_broadcast_handler(self, handler: Callable):
        """Register handler for broadcast messages."""
        self.broadcast_handlers.add(handler)
        self.logger.info("Broadcast handler registered")
    
    def unregister_broadcast_handler(self, handler: Callable):
        """Unregister broadcast handler."""
        self.broadcast_handlers.discard(handler)
        self.logger.info("Broadcast handler unregistered")
    
    async def route_message(self, message: A2AMessage) -> bool:
        """
        Route a message to appropriate handlers.
        
        Args:
            message: Message to route
            
        Returns:
            True if message was successfully queued for delivery
        """
        try:
            # Validate message
            if message.is_expired():
                self.logger.warning("Dropping expired message",
                                  message_id=message.message_id,
                                  age=message.get_age_seconds())
                self._move_to_dead_letter(message, "expired")
                return False
            
            # Check queue capacity
            if len(self.pending_messages) >= self.max_queue_size:
                self.logger.error("Message queue full, dropping message",
                                message_id=message.message_id)
                self._move_to_dead_letter(message, "queue_full")
                return False
            
            # Update message status
            message.status = MessageStatus.SENT
            message.add_delivery_metadata("router_id", self.router_id)
            message.add_delivery_metadata("queued_at", datetime.utcnow().isoformat())
            
            # Add to pending queue
            self.pending_messages.append(message)
            self.stats["messages_routed"] += 1
            
            self.logger.debug("Message queued for routing",
                            message_id=message.message_id,
                            message_type=message.message_type.value,
                            sender=message.sender_id,
                            receiver=message.receiver_id)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to route message",
                            message_id=getattr(message, 'message_id', 'unknown'),
                            error=str(e))
            return False
    
    async def start_processing(self):
        """Start message processing loop."""
        if self.is_running:
            self.logger.warning("Message router already running")
            return
        
        self.is_running = True
        self.processing_task = asyncio.create_task(self._processing_loop())
        self.logger.info("Message router started")
    
    async def stop_processing(self):
        """Stop message processing loop."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Message router stopped")
    
    async def _processing_loop(self):
        """Main message processing loop."""
        while self.is_running:
            try:
                # Process pending messages
                await self._process_pending_messages()
                
                # Process retry queue
                await self._process_retry_queue()
                
                # Cleanup expired messages
                await self._cleanup_expired_messages()
                
                # Wait before next iteration
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in processing loop", error=str(e))
                await asyncio.sleep(1.0)  # Back off on error
    
    async def _process_pending_messages(self):
        """Process messages in pending queue."""
        processed_count = 0
        max_batch_size = 10
        
        while self.pending_messages and processed_count < max_batch_size:
            try:
                message = self.pending_messages.popleft()
                success = await self._deliver_message(message)
                
                if success:
                    message.status = MessageStatus.DELIVERED
                    self.stats["messages_delivered"] += 1
                else:
                    await self._handle_delivery_failure(message)
                
                processed_count += 1
                
            except Exception as e:
                self.logger.error("Error processing pending message", error=str(e))
    
    async def _deliver_message(self, message: A2AMessage) -> bool:
        """
        Deliver message to appropriate handlers.
        
        Args:
            message: Message to deliver
            
        Returns:
            True if delivery successful
        """
        try:
            delivered = False
            
            # Handle broadcast messages
            if message.receiver_id == "broadcast":
                return await self._deliver_broadcast(message)
            
            # Try agent-specific handler first
            if message.receiver_id in self.agent_handlers:
                handler = self.agent_handlers[message.receiver_id]
                await self._call_handler(handler, message)
                delivered = True
            
            # Try route-based handlers
            for route in self.routes:
                if route.matches(message):
                    await self._call_handler(route.handler, message)
                    route.match_count += 1
                    route.last_matched = datetime.utcnow()
                    delivered = True
                    break  # Use first matching route
            
            if not delivered:
                self.logger.warning("No handler found for message",
                                  message_id=message.message_id,
                                  receiver=message.receiver_id,
                                  routing_key=message.get_routing_key())
                return False
            
            self.logger.debug("Message delivered successfully",
                            message_id=message.message_id,
                            receiver=message.receiver_id)
            
            return True
            
        except Exception as e:
            self.logger.error("Message delivery failed",
                            message_id=message.message_id,
                            error=str(e))
            return False
    
    async def _deliver_broadcast(self, message: A2AMessage) -> bool:
        """Deliver broadcast message to all handlers."""
        if not self.broadcast_handlers:
            return False
        
        delivery_count = 0
        
        for handler in list(self.broadcast_handlers):
            try:
                await self._call_handler(handler, message)
                delivery_count += 1
            except Exception as e:
                self.logger.error("Broadcast delivery failed",
                                message_id=message.message_id,
                                error=str(e))
        
        return delivery_count > 0
    
    async def _call_handler(self, handler: Callable, message: A2AMessage):
        """Call message handler with error handling."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)
        except Exception as e:
            self.logger.error("Handler execution failed",
                            message_id=message.message_id,
                            handler=handler.__name__ if hasattr(handler, '__name__') else str(handler),
                            error=str(e))
            raise
    
    async def _handle_delivery_failure(self, message: A2AMessage):
        """Handle message delivery failure."""
        if message.can_retry():
            message.mark_retry()
            message.add_delivery_metadata("retry_scheduled_at", datetime.utcnow().isoformat())
            self.retry_queue.append((message, datetime.utcnow() + timedelta(seconds=self.retry_delay)))
            self.stats["messages_retried"] += 1
            
            self.logger.info("Message scheduled for retry",
                           message_id=message.message_id,
                           retry_count=message.retry_count)
        else:
            self._move_to_dead_letter(message, "max_retries_exceeded")
    
    async def _process_retry_queue(self):
        """Process messages in retry queue."""
        current_time = datetime.utcnow()
        ready_messages = []
        
        # Find messages ready for retry
        while self.retry_queue:
            message, retry_time = self.retry_queue[0]
            if retry_time <= current_time:
                ready_messages.append(self.retry_queue.popleft()[0])
            else:
                break
        
        # Move ready messages back to pending queue
        for message in ready_messages:
            self.pending_messages.append(message)
            self.logger.debug("Message moved from retry to pending",
                            message_id=message.message_id)
    
    def _move_to_dead_letter(self, message: A2AMessage, reason: str):
        """Move message to dead letter queue."""
        message.status = MessageStatus.FAILED
        message.add_delivery_metadata("dead_letter_reason", reason)
        message.add_delivery_metadata("dead_letter_time", datetime.utcnow().isoformat())
        
        self.dead_letter_queue.append(message)
        self.stats["messages_failed"] += 1
        
        self.logger.warning("Message moved to dead letter queue",
                          message_id=message.message_id,
                          reason=reason)
    
    async def _cleanup_expired_messages(self):
        """Clean up expired messages from dead letter queue."""
        current_time = datetime.utcnow()
        cleanup_count = 0
        
        # Create new deque with non-expired messages
        new_dead_letter_queue = deque()
        
        while self.dead_letter_queue:
            message = self.dead_letter_queue.popleft()
            
            # Check if message should be kept
            dead_letter_time_str = message.delivery_metadata.get("dead_letter_time")
            if dead_letter_time_str:
                try:
                    dead_letter_time = datetime.fromisoformat(dead_letter_time_str)
                    if (current_time - dead_letter_time).total_seconds() < self.dead_letter_ttl:
                        new_dead_letter_queue.append(message)
                    else:
                        cleanup_count += 1
                except ValueError:
                    # Invalid timestamp, keep message
                    new_dead_letter_queue.append(message)
            else:
                # No timestamp, keep message
                new_dead_letter_queue.append(message)
        
        self.dead_letter_queue = new_dead_letter_queue
        
        if cleanup_count > 0:
            self.logger.info("Cleaned up expired dead letter messages",
                           cleanup_count=cleanup_count)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            **self.stats,
            "pending_queue_size": len(self.pending_messages),
            "retry_queue_size": len(self.retry_queue),
            "dead_letter_queue_size": len(self.dead_letter_queue),
            "registered_agents": len(self.agent_handlers),
            "broadcast_handlers": len(self.broadcast_handlers),
            "active_routes": len(self.routes),
            "is_running": self.is_running
        }
    
    def get_route_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all routes."""
        return [
            {
                "pattern": route.pattern,
                "priority": route.priority,
                "match_count": route.match_count,
                "last_matched": route.last_matched.isoformat() if route.last_matched else None
            }
            for route in self.routes
        ]
    
    async def flush_queues(self):
        """Process all pending messages immediately."""
        self.logger.info("Flushing message queues")
        
        # Process all pending messages
        while self.pending_messages:
            message = self.pending_messages.popleft()
            await self._deliver_message(message)
        
        # Process ready retry messages
        await self._process_retry_queue()
        while self.pending_messages:
            message = self.pending_messages.popleft()
            await self._deliver_message(message)
        
        self.logger.info("Queue flush completed")


# Global router instance for convenience
_global_router: Optional[MessageRouter] = None


def get_global_router() -> MessageRouter:
    """Get or create global message router."""
    global _global_router
    if _global_router is None:
        _global_router = MessageRouter("global_router")
    return _global_router


async def initialize_global_router():
    """Initialize and start global message router."""
    router = get_global_router()
    if not router.is_running:
        await router.start_processing()
    return router


async def shutdown_global_router():
    """Shutdown global message router."""
    global _global_router
    if _global_router and _global_router.is_running:
        await _global_router.stop_processing()
        _global_router = None
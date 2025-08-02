"""
Agent-to-Agent communication integration system.
"""
import asyncio
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime

from .messages import A2AMessage, MessageType, MessageBuilder, MessageValidator
from .message_router import MessageRouter, get_global_router
from .local_queue import LocalQueueManager, QueueType, QueueConfiguration, get_global_queue_manager
from ..config.logging_config import LoggerMixin


class AgentCommunicationHub(LoggerMixin):
    """
    Central hub for agent-to-agent communication.
    
    Integrates message routing, queuing, and delivery for seamless
    agent communication in the research system.
    """
    
    def __init__(self, hub_id: str = None):
        """Initialize communication hub."""
        self.hub_id = hub_id or f"comm_hub_{id(self)}"
        
        # Core components
        self.router = get_global_router()
        self.queue_manager = get_global_queue_manager()
        self.validator = MessageValidator()
        
        # Agent registry
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_queues: Dict[str, str] = {}  # agent_id -> queue_name mapping
        
        # Communication patterns
        self.message_builders: Dict[str, MessageBuilder] = {}
        
        # Statistics
        self.stats = {
            "agents_registered": 0,
            "messages_sent": 0,
            "messages_delivered": 0,
            "communication_errors": 0
        }
        
        # State
        self.is_running = False
        
        self.logger.info("Agent communication hub initialized", hub_id=self.hub_id)
    
    async def start(self):
        """Start the communication hub."""
        if self.is_running:
            return
        
        # Start router
        await self.router.start_processing()
        
        # Set up default routing patterns
        await self._setup_default_routes()
        
        self.is_running = True
        self.logger.info("Communication hub started", hub_id=self.hub_id)
    
    async def stop(self):
        """Stop the communication hub."""
        if not self.is_running:
            return
        
        # Stop all agent queues
        await self.queue_manager.shutdown_all()
        
        # Stop router
        await self.router.stop_processing()
        
        self.is_running = False
        self.logger.info("Communication hub stopped", hub_id=self.hub_id)
    
    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any] = None) -> bool:
        """
        Register agent for communication.
        
        Args:
            agent_id: Unique agent identifier
            agent_info: Additional agent information
            
        Returns:
            True if registration successful
        """
        try:
            if agent_id in self.registered_agents:
                self.logger.warning("Agent already registered", agent_id=agent_id)
                return True
            
            # Create dedicated queue for agent
            queue_name = f"agent_queue_{agent_id}"
            queue_config = QueueConfiguration(
                max_size=1000,
                persistence_enabled=False,
                auto_acknowledge=True
            )
            
            queue = await self.queue_manager.create_queue(
                queue_name, 
                QueueType.PRIORITY, 
                queue_config
            )
            
            # Register agent handler with router
            agent_handler = self._create_agent_handler(agent_id, queue)
            self.router.register_agent_handler(agent_id, agent_handler)
            
            # Store agent information
            self.registered_agents[agent_id] = {
                "registered_at": datetime.utcnow().isoformat(),
                "queue_name": queue_name,
                "info": agent_info or {},
                "message_count": 0
            }
            
            self.agent_queues[agent_id] = queue_name
            
            # Create message builder for agent
            # We'll use a default session for now
            default_session = f"session_{agent_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.message_builders[agent_id] = MessageBuilder(agent_id, default_session)
            
            self.stats["agents_registered"] += 1
            
            self.logger.info("Agent registered successfully",
                           agent_id=agent_id,
                           queue_name=queue_name)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to register agent",
                            agent_id=agent_id,
                            error=str(e))
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister agent from communication.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if unregistration successful
        """
        try:
            if agent_id not in self.registered_agents:
                return False
            
            # Remove from router
            self.router.unregister_agent_handler(agent_id)
            
            # Delete agent queue
            queue_name = self.agent_queues.get(agent_id)
            if queue_name:
                await self.queue_manager.delete_queue(queue_name)
                del self.agent_queues[agent_id]
            
            # Remove from registry
            del self.registered_agents[agent_id]
            
            # Remove message builder
            if agent_id in self.message_builders:
                del self.message_builders[agent_id]
            
            self.logger.info("Agent unregistered", agent_id=agent_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to unregister agent",
                            agent_id=agent_id,
                            error=str(e))
            return False
    
    async def send_message(self, message: A2AMessage) -> bool:
        """
        Send message through the communication system.
        
        Args:
            message: Message to send
            
        Returns:
            True if message was accepted for delivery
        """
        try:
            # Validate message
            validation_result = self.validator.validate_message(message)
            if not validation_result["valid"]:
                self.logger.error("Message validation failed",
                                message_id=message.message_id,
                                errors=validation_result["errors"])
                self.stats["communication_errors"] += 1
                return False
            
            # Log warnings if any
            if validation_result["warnings"]:
                self.logger.warning("Message validation warnings",
                                  message_id=message.message_id,
                                  warnings=validation_result["warnings"])
            
            # Route message
            success = await self.router.route_message(message)
            
            if success:
                self.stats["messages_sent"] += 1
                
                # Update sender statistics
                if message.sender_id in self.registered_agents:
                    self.registered_agents[message.sender_id]["message_count"] += 1
                
                self.logger.debug("Message sent successfully",
                                message_id=message.message_id,
                                sender=message.sender_id,
                                receiver=message.receiver_id)
            else:
                self.stats["communication_errors"] += 1
                self.logger.error("Failed to route message",
                                message_id=message.message_id)
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to send message",
                            message_id=getattr(message, 'message_id', 'unknown'),
                            error=str(e))
            self.stats["communication_errors"] += 1
            return False
    
    async def send_task_assignment(self, sender_id: str, receiver_id: str,
                                  task_data: Dict[str, Any]) -> bool:
        """
        Send task assignment message.
        
        Args:
            sender_id: Sender agent ID
            receiver_id: Receiver agent ID
            task_data: Task data to assign
            
        Returns:
            True if message sent successfully
        """
        if sender_id not in self.message_builders:
            self.logger.error("Sender not registered", sender_id=sender_id)
            return False
        
        builder = self.message_builders[sender_id]
        message = builder.task_assignment(receiver_id, task_data)
        
        return await self.send_message(message)
    
    async def send_research_request(self, sender_id: str, receiver_id: str,
                                   subtopic_brief: Dict[str, Any]) -> bool:
        """
        Send research request message.
        
        Args:
            sender_id: Sender agent ID
            receiver_id: Receiver agent ID
            subtopic_brief: Research subtopic brief
            
        Returns:
            True if message sent successfully
        """
        if sender_id not in self.message_builders:
            self.logger.error("Sender not registered", sender_id=sender_id)
            return False
        
        builder = self.message_builders[sender_id]
        message = builder.research_request(receiver_id, subtopic_brief)
        
        return await self.send_message(message)
    
    async def send_research_result(self, sender_id: str, receiver_id: str,
                                  research_findings: Dict[str, Any],
                                  reply_to: str = None) -> bool:
        """
        Send research result message.
        
        Args:
            sender_id: Sender agent ID
            receiver_id: Receiver agent ID
            research_findings: Research findings
            reply_to: Optional message ID this is replying to
            
        Returns:
            True if message sent successfully
        """
        if sender_id not in self.message_builders:
            self.logger.error("Sender not registered", sender_id=sender_id)
            return False
        
        builder = self.message_builders[sender_id]
        message = builder.research_result(receiver_id, research_findings, reply_to)
        
        return await self.send_message(message)
    
    async def send_quality_feedback(self, sender_id: str, receiver_id: str,
                                   assessment: Dict[str, Any],
                                   suggestions: List[str] = None) -> bool:
        """
        Send quality feedback message.
        
        Args:
            sender_id: Sender agent ID
            receiver_id: Receiver agent ID
            assessment: Quality assessment
            suggestions: Optional improvement suggestions
            
        Returns:
            True if message sent successfully
        """
        if sender_id not in self.message_builders:
            self.logger.error("Sender not registered", sender_id=sender_id)
            return False
        
        builder = self.message_builders[sender_id]
        message = builder.quality_feedback(receiver_id, assessment, suggestions)
        
        return await self.send_message(message)
    
    async def send_status_update(self, sender_id: str, receiver_id: str,
                                status_info: Dict[str, Any]) -> bool:
        """
        Send status update message.
        
        Args:
            sender_id: Sender agent ID
            receiver_id: Receiver agent ID (or "broadcast")
            status_info: Status information
            
        Returns:
            True if message sent successfully
        """
        if sender_id not in self.message_builders:
            self.logger.error("Sender not registered", sender_id=sender_id)
            return False
        
        builder = self.message_builders[sender_id]
        message = builder.status_update(receiver_id, status_info)
        
        return await self.send_message(message)
    
    async def broadcast_message(self, sender_id: str, message_type: MessageType,
                               payload: Dict[str, Any]) -> bool:
        """
        Broadcast message to all registered agents.
        
        Args:
            sender_id: Sender agent ID
            message_type: Type of message
            payload: Message payload
            
        Returns:
            True if broadcast was sent
        """
        if sender_id not in self.message_builders:
            self.logger.error("Sender not registered", sender_id=sender_id)
            return False
        
        builder = self.message_builders[sender_id]
        
        # Create broadcast message
        message = A2AMessage(
            message_id="",
            sender_id=sender_id,
            receiver_id="broadcast",
            message_type=message_type,
            payload=payload,
            session_id=builder.session_id,
            timestamp=""
        )
        
        return await self.send_message(message)
    
    def _create_agent_handler(self, agent_id: str, queue) -> Callable:
        """Create message handler for agent."""
        async def agent_handler(message: A2AMessage):
            """Handle message for specific agent."""
            try:
                # Enqueue message for agent
                success = await queue.enqueue(message)
                
                if success:
                    self.stats["messages_delivered"] += 1
                    self.logger.debug("Message delivered to agent",
                                    agent_id=agent_id,
                                    message_id=message.message_id)
                else:
                    self.logger.error("Failed to enqueue message for agent",
                                    agent_id=agent_id,
                                    message_id=message.message_id)
            
            except Exception as e:
                self.logger.error("Agent handler error",
                                agent_id=agent_id,
                                message_id=message.message_id,
                                error=str(e))
        
        return agent_handler
    
    async def _setup_default_routes(self):
        """Set up default message routing patterns."""
        # Route task assignments
        self.router.register_route(
            "task_assignment.*",
            self._handle_task_assignment,
            priority=10
        )
        
        # Route research requests
        self.router.register_route(
            "research_request.*",
            self._handle_research_request,
            priority=10
        )
        
        # Route status updates
        self.router.register_route(
            "status_update.*",
            self._handle_status_update,
            priority=5
        )
        
        # Default catch-all route
        self.router.register_route(
            "*",
            self._handle_default_message,
            priority=1
        )
    
    async def _handle_task_assignment(self, message: A2AMessage):
        """Handle task assignment messages."""
        self.logger.debug("Handling task assignment",
                        message_id=message.message_id,
                        receiver=message.receiver_id)
        # Default handler just logs the message
        # Actual handling will be done by agent-specific handlers
    
    async def _handle_research_request(self, message: A2AMessage):
        """Handle research request messages."""
        self.logger.debug("Handling research request",
                        message_id=message.message_id,
                        receiver=message.receiver_id)
    
    async def _handle_status_update(self, message: A2AMessage):
        """Handle status update messages."""
        self.logger.debug("Handling status update",
                        message_id=message.message_id,
                        receiver=message.receiver_id)
    
    async def _handle_default_message(self, message: A2AMessage):
        """Default message handler."""
        self.logger.debug("Handling message with default handler",
                        message_id=message.message_id,
                        message_type=message.message_type.value,
                        receiver=message.receiver_id)
    
    async def get_agent_messages(self, agent_id: str, count: int = 10) -> List[A2AMessage]:
        """
        Get pending messages for agent.
        
        Args:
            agent_id: Agent identifier
            count: Maximum number of messages to retrieve
            
        Returns:
            List of pending messages
        """
        if agent_id not in self.agent_queues:
            return []
        
        queue_name = self.agent_queues[agent_id]
        queue = await self.queue_manager.get_queue(queue_name)
        
        if not queue:
            return []
        
        messages = []
        for _ in range(count):
            message = await queue.dequeue(timeout=0.1)
            if message is None:
                break
            messages.append(message)
        
        return messages
    
    def get_registered_agents(self) -> List[str]:
        """Get list of registered agent IDs."""
        return list(self.registered_agents.keys())
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get information about registered agent."""
        return self.registered_agents.get(agent_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get communication hub statistics."""
        router_stats = self.router.get_stats()
        queue_stats = self.queue_manager.get_stats()
        
        return {
            "hub": self.stats,
            "router": router_stats,
            "queues": queue_stats,
            "registered_agents": len(self.registered_agents),
            "is_running": self.is_running
        }
    
    async def flush_all_messages(self):
        """Process all pending messages immediately."""
        await self.router.flush_queues()
        
        # Also flush all agent queues
        for queue_name in self.agent_queues.values():
            queue = await self.queue_manager.get_queue(queue_name)
            if queue:
                # Process any remaining messages in queue
                while not queue.is_empty():
                    message = await queue.dequeue(timeout=0.1)
                    if message is None:
                        break


# Global communication hub instance
_global_comm_hub: Optional[AgentCommunicationHub] = None


def get_global_communication_hub() -> AgentCommunicationHub:
    """Get or create global communication hub."""
    global _global_comm_hub
    if _global_comm_hub is None:
        _global_comm_hub = AgentCommunicationHub("global_comm_hub")
    return _global_comm_hub


async def initialize_global_communication():
    """Initialize global communication system."""
    hub = get_global_communication_hub()
    if not hub.is_running:
        await hub.start()
    return hub


async def shutdown_global_communication():
    """Shutdown global communication system."""
    global _global_comm_hub
    if _global_comm_hub and _global_comm_hub.is_running:
        await _global_comm_hub.stop()
        _global_comm_hub = None
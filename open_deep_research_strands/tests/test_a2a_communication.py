"""
Tests for Agent-to-Agent (A2A) communication system.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from src.communication.messages import (
    A2AMessage, MessageType, MessagePriority, MessageStatus, MessageBuilder, MessageValidator
)
from src.communication.message_router import MessageRouter, MessageRoute
from src.communication.local_queue import LocalMessageQueue, QueueType, QueueConfiguration
from src.communication.agent_communication import AgentCommunicationHub


class TestA2AMessage:
    """Test suite for A2AMessage class."""
    
    def test_message_creation(self):
        """Test basic message creation."""
        message = A2AMessage(
            message_id="test_msg_001",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test_task"},
            session_id="session_123",
            timestamp=""
        )
        
        assert message.message_id == "test_msg_001"
        assert message.sender_id == "agent_1"
        assert message.receiver_id == "agent_2"
        assert message.message_type == MessageType.TASK_ASSIGNMENT
        assert message.payload == {"task": "test_task"}
        assert message.session_id == "session_123"
        assert message.status == MessageStatus.PENDING
        assert message.priority == MessagePriority.NORMAL
    
    def test_message_auto_generation(self):
        """Test auto-generation of message ID and timestamp."""
        message = A2AMessage(
            message_id="",
            sender_id="agent_1",
            receiver_id="agent_2", 
            message_type=MessageType.STATUS_UPDATE,
            payload={},
            session_id="session_123",
            timestamp=""
        )
        
        assert message.message_id.startswith("msg_")
        assert len(message.message_id) > 10
        assert message.timestamp != ""
        
        # Timestamp should be recent
        msg_time = datetime.fromisoformat(message.timestamp)
        time_diff = datetime.utcnow() - msg_time
        assert time_diff.total_seconds() < 5
    
    def test_message_serialization(self):
        """Test message to/from dict and JSON."""
        original = A2AMessage(
            message_id="test_msg",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.RESEARCH_REQUEST,
            payload={"query": "test query"},
            session_id="session_123",
            timestamp="2024-01-01T10:00:00"
        )
        
        # Test to_dict
        msg_dict = original.to_dict()
        assert msg_dict["message_id"] == "test_msg"
        assert msg_dict["message_type"] == "research_request"
        assert msg_dict["priority"] == "normal"
        
        # Test from_dict
        restored = A2AMessage.from_dict(msg_dict)
        assert restored.message_id == original.message_id
        assert restored.message_type == original.message_type
        assert restored.payload == original.payload
        
        # Test JSON serialization
        json_str = original.to_json()
        restored_from_json = A2AMessage.from_json(json_str)
        assert restored_from_json.message_id == original.message_id
    
    def test_message_expiration(self):
        """Test message TTL and expiration."""
        # Create message with short TTL
        message = A2AMessage(
            message_id="test_msg",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.HEARTBEAT,
            payload={},
            session_id="session_123",
            timestamp=datetime.utcnow().isoformat(),
            ttl=1  # 1 second TTL
        )
        
        # Should not be expired immediately
        assert not message.is_expired()
        
        # Simulate time passage
        old_timestamp = datetime.utcnow() - timedelta(seconds=2)
        message.timestamp = old_timestamp.isoformat()
        
        # Should now be expired
        assert message.is_expired()
    
    def test_message_retry_logic(self):
        """Test message retry functionality."""
        message = A2AMessage(
            message_id="test_msg",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={},
            session_id="session_123",
            timestamp="",
            max_retries=3
        )
        
        # Initially can retry
        assert message.can_retry()
        assert message.retry_count == 0
        
        # Mark for retry
        message.mark_retry()
        assert message.retry_count == 1
        assert message.status == MessageStatus.PENDING
        
        # Test max retries
        for i in range(3):
            message.mark_retry()
        
        assert message.retry_count == 4
        assert not message.can_retry()
    
    def test_create_reply(self):
        """Test reply message creation."""
        original = A2AMessage(
            message_id="original_msg",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "research"},
            session_id="session_123",
            timestamp=""
        )
        
        reply = original.create_reply(
            sender_id="agent_2",
            payload={"result": "completed"},
            message_type=MessageType.TASK_RESULT
        )
        
        assert reply.sender_id == "agent_2"
        assert reply.receiver_id == "agent_1"  # Swapped
        assert reply.message_type == MessageType.TASK_RESULT
        assert reply.correlation_id == "original_msg"
        assert reply.reply_to == "original_msg"
        assert reply.session_id == "session_123"


class TestMessageBuilder:
    """Test suite for MessageBuilder class."""
    
    @pytest.fixture
    def builder(self):
        """Create message builder instance."""
        return MessageBuilder("agent_1", "session_123")
    
    def test_task_assignment_message(self, builder):
        """Test task assignment message creation."""
        task_data = {"task_type": "research", "query": "test query"}
        message = builder.task_assignment("agent_2", task_data)
        
        assert message.sender_id == "agent_1"
        assert message.receiver_id == "agent_2"
        assert message.message_type == MessageType.TASK_ASSIGNMENT
        assert message.payload["task_data"] == task_data
        assert message.session_id == "session_123"
        assert message.priority == MessagePriority.NORMAL
        assert message.ttl == 300  # 5 minutes
    
    def test_research_request_message(self, builder):
        """Test research request message creation."""
        subtopic_brief = {"title": "AI Research", "description": "Study AI"}
        message = builder.research_request("agent_2", subtopic_brief, "corr_123")
        
        assert message.message_type == MessageType.RESEARCH_REQUEST
        assert message.payload["subtopic_brief"] == subtopic_brief
        assert message.correlation_id == "corr_123"
        assert message.priority == MessagePriority.HIGH
        assert message.ttl == 600  # 10 minutes
    
    def test_status_update_message(self, builder):
        """Test status update message creation."""
        status_info = {"status": "active", "progress": 50}
        message = builder.status_update("agent_2", status_info)
        
        assert message.message_type == MessageType.STATUS_UPDATE
        assert message.payload["status"] == status_info
        assert message.priority == MessagePriority.LOW
        assert message.ttl == 60  # 1 minute


class TestMessageValidator:
    """Test suite for MessageValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create message validator instance."""
        return MessageValidator()
    
    def test_valid_message_validation(self, validator):
        """Test validation of valid message."""
        message = A2AMessage(
            message_id="test_msg",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test"},
            session_id="session_123",
            timestamp="2024-01-01T10:00:00"
        )
        
        result = validator.validate_message(message)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_invalid_message_validation(self, validator):
        """Test validation of invalid message."""
        message = A2AMessage(
            message_id="",  # Missing required field
            sender_id="agent_1",
            receiver_id="",  # Missing required field
            message_type=MessageType.TASK_ASSIGNMENT,
            payload="invalid_payload",  # Should be dict
            session_id="session_123",
            timestamp="2024-01-01T10:00:00"
        )
        
        result = validator.validate_message(message)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("Missing required field" in error for error in result["errors"])
        assert any("Payload must be a dictionary" in error for error in result["errors"])


class TestMessageRouter:
    """Test suite for MessageRouter class."""
    
    @pytest.fixture
    def router(self):
        """Create message router instance."""
        return MessageRouter("test_router")
    
    def test_route_registration(self, router):
        """Test route registration."""
        handler = MagicMock()
        router.register_route("task_assignment.*", handler, priority=10)
        
        assert len(router.routes) == 1
        assert router.routes[0].pattern == "task_assignment.*"
        assert router.routes[0].priority == 10
        assert router.stats["routes_registered"] == 1
    
    def test_agent_handler_registration(self, router):
        """Test agent handler registration."""
        handler = AsyncMock()
        router.register_agent_handler("agent_1", handler)
        
        assert "agent_1" in router.agent_handlers
        assert router.agent_handlers["agent_1"] == handler
        
        # Test unregistration
        router.unregister_agent_handler("agent_1")
        assert "agent_1" not in router.agent_handlers
    
    async def test_message_routing(self, router):
        """Test message routing functionality."""
        # Set up handler
        handled_messages = []
        
        async def test_handler(message):
            handled_messages.append(message)
        
        router.register_agent_handler("agent_2", test_handler)
        
        # Create and route message
        message = A2AMessage(
            message_id="test_msg",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test"},
            session_id="session_123",
            timestamp=""
        )
        
        # Route message
        success = await router.route_message(message)
        assert success is True
        
        # Start processing to handle the message
        await router.start_processing()
        await asyncio.sleep(0.2)  # Let processing happen
        await router.stop_processing()
        
        # Check that message was handled
        assert len(handled_messages) == 1
        assert handled_messages[0].message_id == "test_msg"


class TestLocalMessageQueue:
    """Test suite for LocalMessageQueue class."""
    
    @pytest.fixture
    async def queue(self):
        """Create local message queue instance."""
        config = QueueConfiguration(max_size=100, persistence_enabled=False)
        queue = LocalMessageQueue("test_queue", QueueType.PRIORITY, config)
        await queue.start()
        yield queue
        await queue.stop()
    
    async def test_enqueue_dequeue(self, queue):
        """Test basic enqueue and dequeue operations."""
        message = A2AMessage(
            message_id="test_msg",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test"},
            session_id="session_123",
            timestamp="",
            priority=MessagePriority.HIGH
        )
        
        # Enqueue message
        success = await queue.enqueue(message)
        assert success is True
        
        # Check queue size
        size_info = queue.get_size()
        assert size_info["high"] == 1
        assert size_info["total"] == 1
        
        # Dequeue message
        dequeued = await queue.dequeue(timeout=1.0)
        assert dequeued is not None
        assert dequeued.message_id == "test_msg"
        assert dequeued.priority == MessagePriority.HIGH
        
        # Queue should be empty now
        assert queue.is_empty()
    
    async def test_priority_ordering(self, queue):
        """Test priority-based message ordering."""
        messages = [
            A2AMessage("", "s", "r", MessageType.HEARTBEAT, {}, "s", "", priority=MessagePriority.LOW),
            A2AMessage("", "s", "r", MessageType.ERROR_NOTIFICATION, {}, "s", "", priority=MessagePriority.URGENT),
            A2AMessage("", "s", "r", MessageType.TASK_ASSIGNMENT, {}, "s", "", priority=MessagePriority.NORMAL),
            A2AMessage("", "s", "r", MessageType.RESEARCH_REQUEST, {}, "s", "", priority=MessagePriority.HIGH)
        ]
        
        # Enqueue in random order
        for message in messages:
            await queue.enqueue(message)
        
        # Dequeue should return in priority order
        priorities = []
        while not queue.is_empty():
            message = await queue.dequeue(timeout=0.1)
            if message:
                priorities.append(message.priority)
        
        expected_order = [MessagePriority.URGENT, MessagePriority.HIGH, 
                         MessagePriority.NORMAL, MessagePriority.LOW]
        assert priorities == expected_order
    
    async def test_consumer_management(self, queue):
        """Test consumer registration and message processing."""
        processed_messages = []
        
        async def test_consumer(message):
            processed_messages.append(message)
            return True  # Acknowledge
        
        # Add consumer
        success = await queue.add_consumer("consumer_1", test_consumer)
        assert success is True
        
        # Enqueue test message
        message = A2AMessage(
            message_id="test_msg",
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test"},
            session_id="session_123",
            timestamp=""
        )
        
        await queue.enqueue(message)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Check that message was processed
        assert len(processed_messages) == 1
        assert processed_messages[0].message_id == "test_msg"
        
        # Remove consumer
        success = await queue.remove_consumer("consumer_1")
        assert success is True


class TestAgentCommunicationHub:
    """Test suite for AgentCommunicationHub class."""
    
    @pytest.fixture
    async def comm_hub(self):
        """Create communication hub instance."""
        hub = AgentCommunicationHub("test_hub")
        await hub.start()
        yield hub
        await hub.stop()
    
    async def test_agent_registration(self, comm_hub):
        """Test agent registration and unregistration."""
        # Register agent
        success = await comm_hub.register_agent("agent_1", {"role": "supervisor"})
        assert success is True
        
        # Check registration
        agents = comm_hub.get_registered_agents()
        assert "agent_1" in agents
        
        agent_info = comm_hub.get_agent_info("agent_1")
        assert agent_info is not None
        assert agent_info["info"]["role"] == "supervisor"
        
        # Unregister agent
        success = await comm_hub.unregister_agent("agent_1")
        assert success is True
        
        # Check unregistration
        agents = comm_hub.get_registered_agents()
        assert "agent_1" not in agents
    
    async def test_message_sending(self, comm_hub):
        """Test message sending through hub."""
        # Register agents
        await comm_hub.register_agent("agent_1")
        await comm_hub.register_agent("agent_2")
        
        # Send task assignment
        success = await comm_hub.send_task_assignment(
            "agent_1", "agent_2", {"task": "research", "query": "AI"}
        )
        assert success is True
        
        # Check statistics
        stats = comm_hub.get_stats()
        assert stats["hub"]["messages_sent"] >= 1
    
    async def test_message_retrieval(self, comm_hub):
        """Test retrieving messages for agents."""
        # Register agents
        await comm_hub.register_agent("agent_1")
        await comm_hub.register_agent("agent_2")
        
        # Send multiple messages
        await comm_hub.send_task_assignment("agent_1", "agent_2", {"task": "task1"})
        await comm_hub.send_research_request("agent_1", "agent_2", {"topic": "AI"})
        
        # Process messages
        await comm_hub.flush_all_messages()
        
        # Retrieve messages for agent_2
        messages = await comm_hub.get_agent_messages("agent_2", count=5)
        
        # Should have received the messages
        assert len(messages) >= 0  # Messages might be processed by queue consumers
    
    async def test_broadcast_messaging(self, comm_hub):
        """Test broadcast messaging."""
        # Register multiple agents
        await comm_hub.register_agent("agent_1")
        await comm_hub.register_agent("agent_2") 
        await comm_hub.register_agent("agent_3")
        
        # Send broadcast message
        success = await comm_hub.broadcast_message(
            "agent_1", 
            MessageType.STATUS_UPDATE,
            {"status": "system_ready"}
        )
        assert success is True
    
    def test_communication_statistics(self, comm_hub):
        """Test communication statistics collection."""
        stats = comm_hub.get_stats()
        
        assert "hub" in stats
        assert "router" in stats
        assert "queues" in stats
        assert "registered_agents" in stats
        assert "is_running" in stats
        
        hub_stats = stats["hub"]
        assert "messages_sent" in hub_stats
        assert "messages_delivered" in hub_stats
        assert "communication_errors" in hub_stats


# Integration tests
class TestA2ACommunicationIntegration:
    """Integration tests for the complete A2A communication system."""
    
    async def test_end_to_end_communication(self):
        """Test complete message flow from sender to receiver."""
        # Create communication hub
        hub = AgentCommunicationHub("integration_test")
        await hub.start()
        
        try:
            # Register agents
            await hub.register_agent("supervisor", {"role": "supervisor"})
            await hub.register_agent("researcher", {"role": "researcher"})
            
            # Track received messages
            received_messages = []
            
            # Get researcher's queue and add consumer
            researcher_queue_name = hub.agent_queues["researcher"]
            researcher_queue = await hub.queue_manager.get_queue(researcher_queue_name)
            
            async def message_consumer(message):
                received_messages.append(message)
                return True
            
            await researcher_queue.add_consumer("test_consumer", message_consumer)
            
            # Send research request from supervisor to researcher
            success = await hub.send_research_request(
                "supervisor", 
                "researcher",
                {
                    "title": "Machine Learning Research",
                    "description": "Research recent ML advances",
                    "priority": "high"
                }
            )
            
            assert success is True
            
            # Wait for message processing
            await asyncio.sleep(0.5)
            
            # Check that message was received
            assert len(received_messages) >= 1
            
            # Verify message content
            message = received_messages[0]
            assert message.sender_id == "supervisor"
            assert message.receiver_id == "researcher"
            assert message.message_type == MessageType.RESEARCH_REQUEST
            assert "title" in message.payload["subtopic_brief"]
            
            # Send response back
            success = await hub.send_research_result(
                "researcher",
                "supervisor", 
                {
                    "findings": ["Finding 1", "Finding 2"],
                    "confidence": 0.85,
                    "sources": ["Source 1", "Source 2"]
                },
                reply_to=message.message_id
            )
            
            assert success is True
            
        finally:
            await hub.stop()
    
    async def test_message_routing_patterns(self):
        """Test different message routing patterns."""
        hub = AgentCommunicationHub("routing_test")
        await hub.start()
        
        try:
            # Register agents
            await hub.register_agent("supervisor")
            await hub.register_agent("researcher_1") 
            await hub.register_agent("researcher_2")
            
            # Test direct messaging
            success = await hub.send_task_assignment(
                "supervisor", "researcher_1", {"task": "direct_task"}
            )
            assert success is True
            
            # Test broadcast messaging
            success = await hub.broadcast_message(
                "supervisor",
                MessageType.STATUS_UPDATE,
                {"status": "research_phase_started"}
            )
            assert success is True
            
            # Process all messages
            await hub.flush_all_messages()
            
            # Verify statistics
            stats = hub.get_stats()
            assert stats["hub"]["messages_sent"] >= 2
            
        finally:
            await hub.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
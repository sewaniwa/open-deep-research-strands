"""
Agent-to-Agent (A2A) message system for communication between research agents.
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

from ..config.logging_config import LoggerMixin


class MessageType(Enum):
    """Types of messages that can be exchanged between agents."""
    
    # Task management
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    TASK_STATUS_UPDATE = "task_status_update"
    TASK_CANCELLATION = "task_cancellation"
    
    # Research workflow
    RESEARCH_REQUEST = "research_request"
    RESEARCH_RESULT = "research_result"
    RESEARCH_PROGRESS = "research_progress"
    
    # Quality control
    QUALITY_FEEDBACK = "quality_feedback"
    QUALITY_ASSESSMENT = "quality_assessment"
    REVISION_REQUEST = "revision_request"
    
    # Coordination
    STATUS_UPDATE = "status_update"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_ALLOCATION = "resource_allocation"
    
    # Session management
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    AGENT_REGISTRATION = "agent_registration"
    AGENT_DEREGISTRATION = "agent_deregistration"
    
    # Error handling
    ERROR_NOTIFICATION = "error_notification"
    RETRY_REQUEST = "retry_request"
    
    # System
    HEARTBEAT = "heartbeat"
    SHUTDOWN_SIGNAL = "shutdown_signal"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class A2AMessage:
    """
    Core message structure for agent-to-agent communication.
    """
    # Core identification
    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType
    
    # Content and metadata
    payload: Dict[str, Any]
    session_id: str
    timestamp: str
    
    # Optional fields
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    ttl: Optional[int] = None  # Time-to-live in seconds
    
    # Status tracking
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    
    # Routing and delivery
    routing_key: Optional[str] = None
    delivery_metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.message_id:
            self.message_id = f"msg_{uuid.uuid4().hex[:16]}"
        
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        
        if isinstance(self.message_type, str):
            self.message_type = MessageType(self.message_type)
        
        if isinstance(self.priority, str):
            self.priority = MessagePriority(self.priority)
        
        if isinstance(self.status, str):
            self.status = MessageStatus(self.status)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        data = asdict(self)
        # Convert enums to string values
        data["message_type"] = self.message_type.value
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """Create message from dictionary."""
        # Handle enum fields
        if "message_type" in data and isinstance(data["message_type"], str):
            data["message_type"] = MessageType(data["message_type"])
        if "priority" in data and isinstance(data["priority"], str):
            data["priority"] = MessagePriority(data["priority"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = MessageStatus(data["status"])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'A2AMessage':
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        if not self.ttl:
            return False
        
        try:
            message_time = datetime.fromisoformat(self.timestamp)
            current_time = datetime.utcnow()
            elapsed_seconds = (current_time - message_time).total_seconds()
            return elapsed_seconds > self.ttl
        except ValueError:
            return False
    
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retry_count < self.max_retries and not self.is_expired()
    
    def mark_retry(self) -> 'A2AMessage':
        """Mark message for retry and increment retry count."""
        self.retry_count += 1
        self.status = MessageStatus.PENDING
        return self
    
    def create_reply(self, sender_id: str, payload: Dict[str, Any],
                    message_type: MessageType = None) -> 'A2AMessage':
        """Create a reply message to this message."""
        reply_type = message_type or MessageType.TASK_RESULT
        
        return A2AMessage(
            message_id="",  # Will be auto-generated
            sender_id=sender_id,
            receiver_id=self.sender_id,  # Reply to original sender
            message_type=reply_type,
            payload=payload,
            session_id=self.session_id,
            timestamp="",  # Will be auto-generated
            correlation_id=self.message_id,  # Link to original message
            reply_to=self.message_id,
            priority=self.priority
        )
    
    def get_routing_key(self) -> str:
        """Get routing key for message routing."""
        if self.routing_key:
            return self.routing_key
        
        # Generate default routing key
        return f"{self.message_type.value}.{self.receiver_id}"
    
    def add_delivery_metadata(self, key: str, value: Any):
        """Add delivery metadata."""
        if not self.delivery_metadata:
            self.delivery_metadata = {}
        self.delivery_metadata[key] = value
    
    def get_age_seconds(self) -> float:
        """Get message age in seconds."""
        try:
            message_time = datetime.fromisoformat(self.timestamp)
            return (datetime.utcnow() - message_time).total_seconds()
        except ValueError:
            return 0.0


class MessageBuilder:
    """Builder class for creating A2A messages with common patterns."""
    
    def __init__(self, sender_id: str, session_id: str):
        """Initialize message builder."""
        self.sender_id = sender_id
        self.session_id = session_id
    
    def task_assignment(self, receiver_id: str, task_data: Dict[str, Any],
                       priority: MessagePriority = MessagePriority.NORMAL) -> A2AMessage:
        """Create a task assignment message."""
        return A2AMessage(
            message_id="",
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task_data": task_data},
            session_id=self.session_id,
            timestamp="",
            priority=priority,
            ttl=300  # 5 minutes default TTL
        )
    
    def research_request(self, receiver_id: str, subtopic_brief: Dict[str, Any],
                        correlation_id: str = None) -> A2AMessage:
        """Create a research request message."""
        return A2AMessage(
            message_id="",
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.RESEARCH_REQUEST,
            payload={"subtopic_brief": subtopic_brief},
            session_id=self.session_id,
            timestamp="",
            correlation_id=correlation_id,
            priority=MessagePriority.HIGH,
            ttl=600  # 10 minutes for research requests
        )
    
    def research_result(self, receiver_id: str, research_findings: Dict[str, Any],
                       reply_to: str = None) -> A2AMessage:
        """Create a research result message."""
        return A2AMessage(
            message_id="",
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.RESEARCH_RESULT,
            payload={"research_findings": research_findings},
            session_id=self.session_id,
            timestamp="",
            reply_to=reply_to,
            priority=MessagePriority.HIGH
        )
    
    def quality_feedback(self, receiver_id: str, assessment: Dict[str, Any],
                        suggestions: List[str] = None) -> A2AMessage:
        """Create a quality feedback message."""
        payload = {"assessment": assessment}
        if suggestions:
            payload["suggestions"] = suggestions
        
        return A2AMessage(
            message_id="",
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.QUALITY_FEEDBACK,
            payload=payload,
            session_id=self.session_id,
            timestamp="",
            priority=MessagePriority.NORMAL
        )
    
    def status_update(self, receiver_id: str, status_info: Dict[str, Any]) -> A2AMessage:
        """Create a status update message."""
        return A2AMessage(
            message_id="",
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.STATUS_UPDATE,
            payload={"status": status_info},
            session_id=self.session_id,
            timestamp="",
            priority=MessagePriority.LOW,
            ttl=60  # Status updates expire quickly
        )
    
    def error_notification(self, receiver_id: str, error_info: Dict[str, Any],
                          correlation_id: str = None) -> A2AMessage:
        """Create an error notification message."""
        return A2AMessage(
            message_id="",
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.ERROR_NOTIFICATION,
            payload={"error": error_info},
            session_id=self.session_id,
            timestamp="",
            correlation_id=correlation_id,
            priority=MessagePriority.URGENT,
            ttl=120  # 2 minutes for error notifications
        )
    
    def heartbeat(self, receiver_id: str = "broadcast") -> A2AMessage:
        """Create a heartbeat message."""
        return A2AMessage(
            message_id="",
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.HEARTBEAT,
            payload={"timestamp": datetime.utcnow().isoformat()},
            session_id=self.session_id,
            timestamp="",
            priority=MessagePriority.LOW,
            ttl=30  # Heartbeats expire quickly
        )


class MessageValidator(LoggerMixin):
    """Validator for A2A messages."""
    
    def validate_message(self, message: A2AMessage) -> Dict[str, Any]:
        """
        Validate message structure and content.
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Required field validation
        required_fields = [
            "message_id", "sender_id", "receiver_id", 
            "message_type", "payload", "session_id", "timestamp"
        ]
        
        for field in required_fields:
            if not getattr(message, field, None):
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
        
        # Type validation
        if not isinstance(message.payload, dict):
            validation_result["errors"].append("Payload must be a dictionary")
            validation_result["valid"] = False
        
        # Message type validation
        if not isinstance(message.message_type, MessageType):
            validation_result["errors"].append("Invalid message type")
            validation_result["valid"] = False
        
        # TTL validation
        if message.ttl is not None and message.ttl <= 0:
            validation_result["warnings"].append("TTL should be positive")
        
        # Expiration check
        if message.is_expired():
            validation_result["warnings"].append("Message has expired")
        
        # Retry validation
        if message.retry_count > message.max_retries:
            validation_result["warnings"].append("Message has exceeded max retries")
        
        # Payload size check (warn if large)
        payload_size = len(json.dumps(message.payload))
        if payload_size > 1024 * 1024:  # 1MB
            validation_result["warnings"].append("Large payload size detected")
        
        return validation_result
    
    def validate_message_chain(self, messages: List[A2AMessage]) -> Dict[str, Any]:
        """
        Validate a chain of related messages.
        
        Returns:
            Dictionary with chain validation results
        """
        chain_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "chain_length": len(messages),
            "correlation_groups": {}
        }
        
        if not messages:
            chain_result["errors"].append("Empty message chain")
            chain_result["valid"] = False
            return chain_result
        
        # Group by correlation ID
        for message in messages:
            correlation_id = message.correlation_id or "no_correlation"
            if correlation_id not in chain_result["correlation_groups"]:
                chain_result["correlation_groups"][correlation_id] = []
            chain_result["correlation_groups"][correlation_id].append(message.message_id)
        
        # Validate individual messages
        invalid_count = 0
        for message in messages:
            msg_validation = self.validate_message(message)
            if not msg_validation["valid"]:
                invalid_count += 1
        
        if invalid_count > 0:
            chain_result["warnings"].append(f"{invalid_count} invalid messages in chain")
        
        # Check for orphaned replies
        reply_messages = [m for m in messages if m.reply_to]
        for reply_msg in reply_messages:
            original_found = any(m.message_id == reply_msg.reply_to for m in messages)
            if not original_found:
                chain_result["warnings"].append(f"Orphaned reply message: {reply_msg.message_id}")
        
        return chain_result


# Convenience functions for creating common message types
def create_task_assignment(sender_id: str, receiver_id: str, session_id: str,
                          task_data: Dict[str, Any]) -> A2AMessage:
    """Create a task assignment message."""
    builder = MessageBuilder(sender_id, session_id)
    return builder.task_assignment(receiver_id, task_data)


def create_research_request(sender_id: str, receiver_id: str, session_id: str,
                           subtopic_brief: Dict[str, Any]) -> A2AMessage:
    """Create a research request message."""
    builder = MessageBuilder(sender_id, session_id)
    return builder.research_request(receiver_id, subtopic_brief)


def create_research_result(sender_id: str, receiver_id: str, session_id: str,
                          research_findings: Dict[str, Any], reply_to: str = None) -> A2AMessage:
    """Create a research result message."""
    builder = MessageBuilder(sender_id, session_id)
    return builder.research_result(receiver_id, research_findings, reply_to)


def create_status_update(sender_id: str, receiver_id: str, session_id: str,
                        status_info: Dict[str, Any]) -> A2AMessage:
    """Create a status update message."""
    builder = MessageBuilder(sender_id, session_id)
    return builder.status_update(receiver_id, status_info)
"""
Custom exceptions for Open Deep Research Strands.
"""
from typing import Optional, Dict, Any


class OpenDeepResearchError(Exception):
    """Base exception for all Open Deep Research Strands errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class AgentError(OpenDeepResearchError):
    """Base exception for agent-related errors."""
    pass


class AgentInitializationError(AgentError):
    """Raised when agent initialization fails."""
    pass


class AgentTaskError(AgentError):
    """Raised when agent task execution fails."""
    pass


class AgentCommunicationError(AgentError):
    """Raised when agent communication fails."""
    pass


class ConfigurationError(OpenDeepResearchError):
    """Raised when configuration is invalid or missing."""
    pass


class SDKError(OpenDeepResearchError):
    """Raised when Strands SDK operations fail."""
    pass


class LLMError(OpenDeepResearchError):
    """Base exception for LLM-related errors."""
    pass


class LLMProviderError(LLMError):
    """Raised when LLM provider operations fail."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limits are exceeded."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when LLM authentication fails."""
    pass


class MessageRoutingError(OpenDeepResearchError):
    """Raised when message routing fails."""
    pass


class MessageValidationError(OpenDeepResearchError):
    """Raised when message validation fails."""
    pass


class TimeoutError(OpenDeepResearchError):
    """Raised when operations timeout."""
    pass


class SecurityError(OpenDeepResearchError):
    """Raised for security-related issues."""
    pass


class MemorySystemError(OpenDeepResearchError):
    """Raised when memory system operations fail."""
    pass


class ToolError(OpenDeepResearchError):
    """Base exception for tool-related errors."""
    pass


class ToolTimeoutError(ToolError):
    """Raised when tool operations timeout."""
    pass


class ToolAuthenticationError(ToolError):
    """Raised when tool authentication fails."""
    pass


class ValidationError(OpenDeepResearchError):
    """Raised when data validation fails."""
    pass


class AgentValidationError(AgentError):
    """Raised when agent input validation fails."""
    pass
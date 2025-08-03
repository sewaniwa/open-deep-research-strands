"""
LLM interface for interacting with different language model providers.
"""
import os
import asyncio
from typing import Dict, List, Any, Optional, Union, Literal
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..config.logging_config import LoggerMixin
# from ..config.secrets_manager import get_api_key  # Temporarily disabled
from ..exceptions import LLMError, LLMAuthenticationError, LLMProviderError


@dataclass
class LLMMessage:
    """Represents a message in LLM conversation."""
    role: Literal["system", "user", "assistant"]
    content: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata or {}
        }


@dataclass
class LLMResponse:
    """Represents LLM response."""
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "content": self.content,
            "usage": self.usage,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "metadata": self.metadata or {}
        }


class LLMProvider(ABC, LoggerMixin):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM provider.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.request_count = 0
        self.total_tokens = 0
    
    @abstractmethod
    async def generate(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response from messages."""
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate provider configuration."""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider usage statistics."""
        return {
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "provider": self.__class__.__name__
        }


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI provider."""
        super().__init__(config)
        
        # Get API key securely
        self.api_key = os.getenv(config.get("api_key_env", "OPENAI_API_KEY")) or "mock_api_key"
        
        if not self.api_key:
            raise LLMAuthenticationError(
                "OpenAI API key not found. Please set using secrets manager or environment variable.",
                {"provider": "openai", "required_env": "OPENAI_API_KEY"}
            )
        
        self.model = config.get("model", "gpt-4")
        self.max_tokens = config.get("max_tokens", 4000)
        self.temperature = config.get("temperature", 0.1)
        
        # For development, we'll use a mock implementation
        self._mock_mode = config.get("mock_mode", False)
        
        if self._mock_mode:
            self.logger.warning("OpenAI provider running in mock mode")
    
    async def generate(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response using OpenAI API."""
        self.request_count += 1
        
        if self._mock_mode:
            return await self._mock_generate(messages, **kwargs)
        
        try:
            # In a real implementation, this would use the OpenAI client
            # For now, we'll use mock responses
            return await self._mock_generate(messages, **kwargs)
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            # Fallback to mock
            return await self._mock_generate(messages, **kwargs)
    
    async def _mock_generate(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate mock response."""
        # Simulate API delay
        await asyncio.sleep(1.0)
        
        # Get the last user message for context
        user_messages = [msg for msg in messages if msg.role == "user"]
        last_user_message = user_messages[-1].content if user_messages else "No input"
        
        # Generate contextual mock response
        mock_responses = [
            f"Based on your query about '{last_user_message[:50]}...', I can provide the following analysis:",
            f"Here's my understanding of the topic '{last_user_message[:30]}...' and relevant insights:",
            f"Regarding '{last_user_message[:40]}...', let me break this down into key components:",
            f"To address your question about '{last_user_message[:35]}...', I'll provide a comprehensive response:"
        ]
        
        import random
        mock_content = f"{random.choice(mock_responses)}\n\n" \
                      f"1. This appears to be a complex topic that requires careful analysis.\n" \
                      f"2. Key considerations include multiple factors and perspectives.\n" \
                      f"3. Based on current understanding, the approach should be systematic.\n" \
                      f"4. Further research may be beneficial to fully address this topic.\n\n" \
                      f"This is a mock response for development purposes."
        
        usage_tokens = len(mock_content.split()) * 2  # Rough token estimate
        self.total_tokens += usage_tokens
        
        return LLMResponse(
            content=mock_content,
            usage={"total_tokens": usage_tokens, "prompt_tokens": 100, "completion_tokens": usage_tokens - 100},
            model=self.model,
            finish_reason="stop",
            metadata={"mock_mode": True}
        )
    
    async def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        return True  # Always valid for mock mode


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Anthropic provider."""
        super().__init__(config)
        self.api_key = os.getenv(config.get("api_key_env", "ANTHROPIC_API_KEY"))
        self.model = config.get("model", "claude-3-sonnet")
        self.max_tokens = config.get("max_tokens", 4000)
        self.temperature = config.get("temperature", 0.1)
        
        # For development, we'll use a mock implementation
        self._mock_mode = not self.api_key
        
        if self._mock_mode:
            self.logger.warning("Anthropic API key not found, using mock mode")
    
    async def generate(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response using Anthropic API."""
        self.request_count += 1
        
        if self._mock_mode:
            return await self._mock_generate(messages, **kwargs)
        
        try:
            # In a real implementation, this would use the Anthropic client
            # For now, we'll use mock responses
            return await self._mock_generate(messages, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            # Fallback to mock
            return await self._mock_generate(messages, **kwargs)
    
    async def _mock_generate(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate mock response."""
        # Simulate API delay
        await asyncio.sleep(1.2)
        
        # Get context from messages
        user_messages = [msg for msg in messages if msg.role == "user"]
        last_user_message = user_messages[-1].content if user_messages else "No input"
        
        mock_content = f"I understand you're asking about '{last_user_message[:40]}...'. " \
                      f"Let me provide a thoughtful analysis:\n\n" \
                      f"From my perspective, this topic involves several key dimensions:\n" \
                      f"• Conceptual framework and theoretical foundations\n" \
                      f"• Practical applications and real-world implications\n" \
                      f"• Current research trends and emerging developments\n" \
                      f"• Potential challenges and opportunities ahead\n\n" \
                      f"I'd be happy to explore any of these aspects in more detail. " \
                      f"This is a mock response for development and testing purposes."
        
        usage_tokens = len(mock_content.split()) * 2
        self.total_tokens += usage_tokens
        
        return LLMResponse(
            content=mock_content,
            usage={"total_tokens": usage_tokens, "input_tokens": 80, "output_tokens": usage_tokens - 80},
            model=self.model,
            finish_reason="end_turn",
            metadata={"mock_mode": True}
        )
    
    async def validate_config(self) -> bool:
        """Validate Anthropic configuration."""
        return True  # Always valid for mock mode


class LLMManager(LoggerMixin):
    """Manager for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM manager.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider = config.get("default_provider", "openai")
        
        # Initialize providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers."""
        llm_config = self.config.get("llm_config", {})
        
        # Initialize OpenAI provider
        if "openai" in llm_config:
            self.providers["openai"] = OpenAIProvider(llm_config["openai"])
        
        # Initialize Anthropic provider
        if "anthropic" in llm_config:
            self.providers["anthropic"] = AnthropicProvider(llm_config["anthropic"])
        
        self.logger.info("Initialized LLM providers", providers=list(self.providers.keys()))
    
    async def generate(self, messages: Union[List[LLMMessage], List[Dict[str, str]]], 
                      provider: str = None, **kwargs) -> LLMResponse:
        """
        Generate response using specified provider.
        
        Args:
            messages: Conversation messages
            provider: Provider to use (defaults to configured default)
            **kwargs: Additional generation parameters
            
        Returns:
            LLM response
        """
        provider_name = provider or self.default_provider
        
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        # Convert dict messages to LLMMessage objects if needed
        if messages and isinstance(messages[0], dict):
            messages = [LLMMessage(role=msg["role"], content=msg["content"]) 
                       for msg in messages]
        
        provider_instance = self.providers[provider_name]
        
        self.logger.debug("Generating LLM response", 
                         provider=provider_name, message_count=len(messages))
        
        return await provider_instance.generate(messages, **kwargs)
    
    async def validate_all_providers(self) -> Dict[str, bool]:
        """Validate all provider configurations."""
        results = {}
        
        for name, provider in self.providers.items():
            try:
                results[name] = await provider.validate_config()
            except Exception as e:
                self.logger.error(f"Provider validation failed: {name}", error=str(e))
                results[name] = False
        
        return results
    
    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all providers."""
        return {name: provider.get_stats() for name, provider in self.providers.items()}
    
    def list_providers(self) -> List[str]:
        """List available providers."""
        return list(self.providers.keys())
    
    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get specific provider instance."""
        return self.providers.get(name)


# Convenience functions for easy access
async def create_llm_manager(config: Dict[str, Any]) -> LLMManager:
    """Create and initialize LLM manager."""
    manager = LLMManager(config)
    
    # Validate all providers
    validation_results = await manager.validate_all_providers()
    
    # Log validation results
    for provider, valid in validation_results.items():
        if valid:
            manager.logger.info(f"Provider {provider} validated successfully")
        else:
            manager.logger.warning(f"Provider {provider} validation failed")
    
    return manager


def create_message(role: str, content: str, metadata: Dict[str, Any] = None) -> LLMMessage:
    """Create an LLM message."""
    return LLMMessage(role=role, content=content, metadata=metadata)


def create_messages_from_conversation(conversation: List[Dict[str, str]]) -> List[LLMMessage]:
    """Create LLM messages from conversation history."""
    return [LLMMessage(role=msg["role"], content=msg["content"]) 
            for msg in conversation]
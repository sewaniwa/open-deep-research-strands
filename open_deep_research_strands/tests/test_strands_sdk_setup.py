"""
Integration tests for Strands SDK setup and local development environment.
"""
import pytest
import asyncio
import tempfile
from pathlib import Path

from src.config.strands_config import (
    StrandsSDKManager, 
    StrandsRuntimeConfig, 
    StrandsMemoryConfig,
    initialize_strands_sdk,
    get_sdk_manager
)
from src.tools.local_memory import LocalMemorySystem
from src.tools.mock_tools import MockWebSearchTool, MockMCPServer
from src.tools.llm_interface import LLMManager, create_message


class TestStrandsSDKSetup:
    """Test suite for Strands SDK setup."""
    
    @pytest.fixture
    async def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sdk_config(self, temp_storage):
        """Create test SDK configuration."""
        return {
            "storage_path": temp_storage,
            "debug_mode": True,
            "max_concurrent_agents": 3
        }
    
    @pytest.fixture
    async def sdk_manager(self, sdk_config):
        """Create and initialize SDK manager."""
        manager = StrandsSDKManager(sdk_config)
        await manager.initialize_sdk()
        return manager
    
    async def test_sdk_manager_initialization(self, sdk_config):
        """Test SDK manager initialization."""
        manager = StrandsSDKManager(sdk_config)
        
        # Check initial state
        assert not manager.is_initialized()
        
        # Initialize
        result = await manager.initialize_sdk()
        assert result is True
        assert manager.is_initialized()
        
        # Check components
        runtime = manager.get_runtime()
        assert runtime is not None
        
        memory_system = manager.get_memory_system()
        assert memory_system is not None
        assert isinstance(memory_system, LocalMemorySystem)
    
    async def test_config_overrides(self, temp_storage):
        """Test configuration overrides."""
        overrides = {
            "max_concurrent_agents": 10,
            "debug_mode": False,
            "storage_path": temp_storage
        }
        
        manager = StrandsSDKManager(overrides)
        assert manager.agent_config.max_concurrent_agents == 10
        assert manager.runtime_config.debug_mode is False
        assert manager.memory_config.storage_path == temp_storage
    
    async def test_runtime_session_management(self, sdk_manager):
        """Test runtime session management."""
        runtime = sdk_manager.get_runtime()
        
        # Create session
        session_id = await runtime.create_session("test_agent", ["search", "analyze"])
        assert session_id is not None
        assert session_id in runtime.sessions
        
        # Check session data
        session_data = runtime.sessions[session_id]
        assert session_data["agent_id"] == "test_agent"
        assert session_data["capabilities"] == ["search", "analyze"]
        assert session_data["status"] == "active"
        
        # Terminate session
        await runtime.terminate_session(session_id)
        assert runtime.sessions[session_id]["status"] == "terminated"
    
    async def test_memory_system_operations(self, sdk_manager):
        """Test memory system operations."""
        memory_system = sdk_manager.get_memory_system()
        
        # Create namespace
        namespace = await memory_system.create_namespace("test_session")
        assert namespace == "test_session"
        
        # Store and retrieve data
        test_data = {"query": "test query", "results": ["result1", "result2"]}
        entry_id = await memory_system.store(namespace, "test_key", test_data)
        assert entry_id is not None
        
        retrieved_data = await memory_system.retrieve(namespace, "test_key")
        assert retrieved_data == test_data
        
        # List entries
        entries = await memory_system.list_entries(namespace)
        assert "test_key" in entries
        
        # Search functionality
        search_results = await memory_system.search(namespace, "test")
        assert len(search_results) > 0
        assert search_results[0]["key"] == "test_key"
    
    async def test_global_sdk_manager(self):
        """Test global SDK manager access."""
        # Test singleton behavior
        manager1 = get_sdk_manager()
        manager2 = get_sdk_manager()
        assert manager1 is manager2
        
        # Test initialization function
        result = await initialize_strands_sdk({"debug_mode": True})
        assert result is True
        
        manager = get_sdk_manager()
        assert manager.is_initialized()


class TestLocalMemorySystem:
    """Test suite for local memory system."""
    
    @pytest.fixture
    async def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def memory_config(self, temp_storage):
        """Create memory configuration."""
        class MockConfig:
            def __init__(self, storage_path):
                self.storage_path = storage_path
        
        return MockConfig(temp_storage)
    
    @pytest.fixture
    async def memory_system(self, memory_config):
        """Create memory system instance."""
        return LocalMemorySystem(memory_config)
    
    async def test_namespace_creation(self, memory_system):
        """Test namespace creation and management."""
        namespace = await memory_system.create_namespace("research_session_1")
        assert namespace == "research_session_1"
        
        # Test namespace metadata
        stats = await memory_system.get_namespace_stats("research_session_1")
        assert stats["exists"] is True
        assert stats["total_entries"] == 0
    
    async def test_data_storage_and_retrieval(self, memory_system):
        """Test data storage and retrieval."""
        namespace = "test_namespace"
        await memory_system.create_namespace(namespace)
        
        # Store complex data
        test_data = {
            "research_results": [
                {"title": "Paper 1", "score": 0.85},
                {"title": "Paper 2", "score": 0.92}
            ],
            "metadata": {"query": "AI research", "timestamp": "2024-01-01"}
        }
        
        entry_id = await memory_system.store(namespace, "research_data", test_data)
        assert entry_id is not None
        
        # Retrieve data
        retrieved = await memory_system.retrieve(namespace, "research_data")
        assert retrieved == test_data
        
        # Test non-existent key
        not_found = await memory_system.retrieve(namespace, "non_existent")
        assert not_found is None
    
    async def test_ttl_functionality(self, memory_system):
        """Test time-to-live functionality."""
        namespace = "ttl_test"
        await memory_system.create_namespace(namespace)
        
        # Store data with short TTL
        await memory_system.store(namespace, "temp_data", "temporary", ttl=1)
        
        # Immediate retrieval should work
        data = await memory_system.retrieve(namespace, "temp_data")
        assert data == "temporary"
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Should be expired
        expired_data = await memory_system.retrieve(namespace, "temp_data")
        assert expired_data is None
    
    async def test_search_functionality(self, memory_system):
        """Test search functionality."""
        namespace = "search_test"
        await memory_system.create_namespace(namespace)
        
        # Store searchable content
        await memory_system.store(namespace, "doc1", "artificial intelligence research")
        await memory_system.store(namespace, "doc2", "machine learning algorithms")
        await memory_system.store(namespace, "doc3", "natural language processing")
        
        # Search for content
        results = await memory_system.search(namespace, "intelligence")
        assert len(results) == 1
        assert results[0]["key"] == "doc1"
        
        results = await memory_system.search(namespace, "learning")
        assert len(results) == 1
        assert results[0]["key"] == "doc2"
        
        # Search with multiple matches
        results = await memory_system.search(namespace, "language")
        assert len(results) == 1


class TestMockTools:
    """Test suite for mock tools."""
    
    @pytest.fixture
    def web_search_tool(self):
        """Create web search tool instance."""
        return MockWebSearchTool()
    
    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance."""
        return MockMCPServer()
    
    async def test_web_search_functionality(self, web_search_tool):
        """Test web search mock functionality."""
        # Basic search
        results = await web_search_tool.search("artificial intelligence", max_results=5)
        
        assert "query" in results
        assert "results" in results
        assert results["query"] == "artificial intelligence"
        assert len(results["results"]) <= 5
        
        # Check result structure
        for result in results["results"]:
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert "domain" in result
            assert "relevance_score" in result
        
        # Test with domain filter
        filtered_results = await web_search_tool.search(
            "machine learning", 
            domain_filter=["arxiv.org", "github.com"]
        )
        
        for result in filtered_results["results"]:
            assert result["domain"] in ["arxiv.org", "github.com"]
    
    async def test_mcp_server_functionality(self, mcp_server):
        """Test MCP server functionality."""
        # List available tools
        tools = await mcp_server.list_tools()
        assert "web_search" in tools
        assert "document_analyzer" in tools
        assert "citation_manager" in tools
        
        # Test web search tool
        search_result = await mcp_server.call_tool(
            "web_search", 
            query="test query", 
            max_results=3
        )
        assert "results" in search_result
        
        # Test document analyzer
        analysis_result = await mcp_server.call_tool(
            "document_analyzer",
            content="This is a test document about artificial intelligence.",
            analysis_type="summary"
        )
        assert "summary" in analysis_result
        
        # Test citation manager
        citation_result = await mcp_server.call_tool(
            "citation_manager",
            action="add",
            title="Test Paper",
            authors=["Author 1", "Author 2"],
            url="https://example.com"
        )
        assert "citation_id" in citation_result
    
    async def test_tool_statistics(self, web_search_tool, mcp_server):
        """Test tool usage statistics."""
        # Use tools
        await web_search_tool.search("test query 1")
        await web_search_tool.search("test query 2")
        
        stats = await web_search_tool.get_search_stats()
        assert stats["total_searches"] == 2
        assert stats["mock_mode"] is True
        
        # Use MCP server
        await mcp_server.call_tool("web_search", query="test")
        await mcp_server.call_tool("document_analyzer", content="test", analysis_type="summary")
        
        tool_info = await mcp_server.get_tool_info("web_search")
        assert tool_info["call_count"] == 1


class TestLLMInterface:
    """Test suite for LLM interface."""
    
    @pytest.fixture
    def llm_config(self):
        """Create LLM configuration."""
        return {
            "default_provider": "openai",
            "llm_config": {
                "openai": {
                    "model": "gpt-4",
                    "api_key_env": "OPENAI_API_KEY",
                    "max_tokens": 1000
                },
                "anthropic": {
                    "model": "claude-3-sonnet",
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "max_tokens": 1000
                }
            }
        }
    
    @pytest.fixture
    async def llm_manager(self, llm_config):
        """Create LLM manager instance."""
        return LLMManager(llm_config)
    
    async def test_llm_manager_initialization(self, llm_manager):
        """Test LLM manager initialization."""
        providers = llm_manager.list_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        
        # Test provider validation
        validation_results = await llm_manager.validate_all_providers()
        assert all(validation_results.values())
    
    async def test_message_generation(self, llm_manager):
        """Test message generation."""
        messages = [
            create_message("system", "You are a helpful research assistant."),
            create_message("user", "What is artificial intelligence?")
        ]
        
        # Test with default provider
        response = await llm_manager.generate(messages)
        assert response.content is not None
        assert len(response.content) > 0
        assert response.model is not None
        assert response.usage["total_tokens"] > 0
        
        # Test with specific provider
        response = await llm_manager.generate(messages, provider="anthropic")
        assert response.content is not None
        assert response.metadata.get("mock_mode") is True
    
    async def test_provider_statistics(self, llm_manager):
        """Test provider statistics."""
        # Generate some responses
        messages = [create_message("user", "Test message")]
        
        await llm_manager.generate(messages, provider="openai")
        await llm_manager.generate(messages, provider="anthropic")
        
        stats = llm_manager.get_provider_stats()
        assert "openai" in stats
        assert "anthropic" in stats
        
        assert stats["openai"]["request_count"] >= 1
        assert stats["anthropic"]["request_count"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
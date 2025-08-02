"""
Integration tests for Phase 1 local development environment.
"""
import sys
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.strands_config import initialize_strands_sdk, get_sdk_manager
from src.agents.supervisor_agent import SupervisorAgent
from src.agents.research_sub_agent import ResearchSubAgent
from src.agents.scoping_agent import ScopingAgent
from src.agents.base_agent import create_task_data
from src.communication.agent_communication import (
    AgentCommunicationHub, initialize_global_communication
)
from src.communication.messages import MessageType
from src.tools.mock_tools import MockWebSearchTool, MockMCPServer
from src.tools.llm_interface import LLMManager, create_message


class TestPhase1Integration:
    """Integration tests for Phase 1 complete system."""
    
    @pytest.fixture
    async def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    async def sdk_setup(self, temp_storage):
        """Set up SDK with temporary storage."""
        config_override = {
            "storage_path": temp_storage,
            "debug_mode": True,
            "max_concurrent_agents": 3
        }
        
        success = await initialize_strands_sdk(config_override)
        assert success is True
        
        yield get_sdk_manager()
        
        # Cleanup
        sdk_manager = get_sdk_manager()
        if sdk_manager.is_initialized():
            # Clean shutdown
            pass
    
    @pytest.fixture
    async def communication_hub(self):
        """Set up communication hub."""
        hub = await initialize_global_communication()
        yield hub
        await hub.stop()
    
    async def test_agent_creation_and_initialization(self, sdk_setup):
        """Test that all agent types can be created and initialized."""
        # Test SupervisorAgent
        supervisor = SupervisorAgent()
        assert supervisor.name == "supervisor"
        assert supervisor.role == "research_orchestrator"
        
        init_success = await supervisor.initialize()
        assert init_success is True
        assert supervisor.is_active is True
        assert supervisor.session_id is not None
        
        await supervisor.shutdown()
        
        # Test ResearchSubAgent
        research_agent = ResearchSubAgent("machine learning", "ml_001")
        assert research_agent.subtopic == "machine learning"
        assert research_agent.role == "specialized_researcher"
        
        init_success = await research_agent.initialize()
        assert init_success is True
        
        await research_agent.shutdown()
        
        # Test ScopingAgent
        scoping_agent = ScopingAgent()
        assert scoping_agent.role == "requirement_clarifier"
        
        init_success = await scoping_agent.initialize()
        assert init_success is True
        
        await scoping_agent.shutdown()
    
    async def test_a2a_communication_flow(self, sdk_setup, communication_hub):
        """Test complete A2A communication flow between agents."""
        # Register agents
        await communication_hub.register_agent("supervisor", {"role": "supervisor"})
        await communication_hub.register_agent("researcher", {"role": "researcher"})
        
        # Track messages received
        received_messages = []
        
        # Set up message consumer for researcher
        researcher_queue_name = communication_hub.agent_queues["researcher"]
        researcher_queue = await communication_hub.queue_manager.get_queue(researcher_queue_name)
        
        async def message_consumer(message):
            received_messages.append(message)
            return True
        
        await researcher_queue.add_consumer("test_consumer", message_consumer)
        
        # Send task assignment
        success = await communication_hub.send_task_assignment(
            "supervisor", 
            "researcher",
            {
                "task_type": "research",
                "query": "artificial intelligence trends",
                "priority": "high"
            }
        )
        assert success is True
        
        # Wait for message processing
        await asyncio.sleep(0.5)
        
        # Verify message was received
        assert len(received_messages) >= 1
        task_message = received_messages[0]
        assert task_message.sender_id == "supervisor"
        assert task_message.receiver_id == "researcher"
        assert task_message.message_type == MessageType.TASK_ASSIGNMENT
        
        # Send response back
        success = await communication_hub.send_research_result(
            "researcher",
            "supervisor",
            {
                "findings": ["AI is evolving rapidly", "Key trends include LLMs"],
                "confidence": 0.9,
                "sources": ["Source 1", "Source 2"]
            },
            reply_to=task_message.message_id
        )
        assert success is True
        
        # Verify communication statistics
        stats = communication_hub.get_stats()
        assert stats["hub"]["messages_sent"] >= 2
    
    async def test_mock_tools_integration(self, sdk_setup):
        """Test integration with mock tools."""
        # Test MockWebSearchTool
        web_search = MockWebSearchTool()
        
        search_results = await web_search.search("machine learning", max_results=5)
        assert "results" in search_results
        assert len(search_results["results"]) <= 5
        assert search_results["query"] == "machine learning"
        
        # Verify search statistics
        stats = await web_search.get_search_stats()
        assert stats["total_searches"] >= 1
        assert stats["mock_mode"] is True
        
        # Test MockMCPServer
        mcp_server = MockMCPServer()
        
        tools = await mcp_server.list_tools()
        assert "web_search" in tools
        assert "document_analyzer" in tools
        assert "citation_manager" in tools
        
        # Test tool execution
        search_result = await mcp_server.call_tool(
            "web_search",
            query="AI research",
            max_results=3
        )
        assert "results" in search_result
        
        analysis_result = await mcp_server.call_tool(
            "document_analyzer",
            content="This is test content about AI research.",
            analysis_type="summary"
        )
        assert "summary" in analysis_result
    
    async def test_memory_system_integration(self, sdk_setup):
        """Test memory system integration."""
        sdk_manager = get_sdk_manager()
        memory_system = sdk_manager.get_memory_system()
        
        # Test namespace creation
        namespace = await memory_system.create_namespace("test_integration")
        assert namespace == "test_integration"
        
        # Test data storage and retrieval
        test_data = {
            "research_query": "machine learning",
            "results": [
                {"title": "ML Paper 1", "score": 0.9},
                {"title": "ML Paper 2", "score": 0.85}
            ],
            "timestamp": "2024-01-01T10:00:00"
        }
        
        entry_id = await memory_system.store(namespace, "research_session_1", test_data)
        assert entry_id is not None
        
        retrieved_data = await memory_system.retrieve(namespace, "research_session_1")
        assert retrieved_data == test_data
        
        # Test search functionality
        search_results = await memory_system.search(namespace, "machine learning")
        assert len(search_results) >= 1
        assert search_results[0]["key"] == "research_session_1"
        
        # Test namespace statistics
        stats = await memory_system.get_namespace_stats(namespace)
        assert stats["exists"] is True
        assert stats["total_entries"] >= 1
    
    async def test_llm_interface_integration(self, sdk_setup):
        """Test LLM interface integration."""
        from src.configs.local_config import get_config
        
        config = get_config()
        llm_manager = LLMManager(config)
        
        # Test provider validation
        validation_results = await llm_manager.validate_all_providers()
        assert len(validation_results) > 0
        
        # Test message generation
        messages = [
            create_message("system", "You are a helpful research assistant."),
            create_message("user", "What is machine learning?")
        ]
        
        response = await llm_manager.generate(messages)
        assert response.content is not None
        assert len(response.content) > 0
        assert response.usage["total_tokens"] > 0
        
        # Test provider statistics
        stats = llm_manager.get_provider_stats()
        assert len(stats) > 0


class TestSupervisorAgentIntegration:
    """Integration tests for SupervisorAgent with all components."""
    
    @pytest.fixture
    async def integrated_supervisor(self, temp_storage):
        """Create fully integrated supervisor agent."""
        # Initialize SDK
        config_override = {
            "storage_path": temp_storage,
            "debug_mode": True
        }
        await initialize_strands_sdk(config_override)
        
        # Create and initialize supervisor
        supervisor = SupervisorAgent()
        await supervisor.initialize()
        
        yield supervisor
        
        await supervisor.shutdown()
    
    async def test_supervisor_control_loop_execution(self, integrated_supervisor):
        """Test supervisor's 3-phase control loop."""
        supervisor = integrated_supervisor
        
        # Execute control loop with test query
        test_query = "What are the latest developments in artificial intelligence?"
        
        try:
            result = await supervisor.execute_control_loop(test_query)
            
            # Verify result structure
            assert "session_id" in result
            assert "user_query" in result
            assert "research_brief" in result
            assert "research_results" in result
            assert "final_report" in result
            assert "status" in result
            
            assert result["user_query"] == test_query
            assert result["status"] == "completed"
            assert result["phases_completed"] == ["scoping", "research", "report"]
            
            # Verify research brief
            research_brief = result["research_brief"]
            assert "original_query" in research_brief
            assert "research_objective" in research_brief
            assert "required_topics" in research_brief
            assert len(research_brief["required_topics"]) >= 3
            
            # Verify research results
            research_results = result["research_results"]
            assert "subtopic_results" in research_results
            assert "quality_assessment" in research_results
            
            # Verify final report
            final_report = result["final_report"]
            assert "title" in final_report
            assert "executive_summary" in final_report
            assert "key_findings" in final_report
            assert "detailed_findings" in final_report
            
        except Exception as e:
            pytest.fail(f"Control loop execution failed: {str(e)}")
    
    async def test_supervisor_session_management(self, integrated_supervisor):
        """Test supervisor session management."""
        supervisor = integrated_supervisor
        
        # Check initial session status
        status = supervisor.get_session_status()
        assert "active_sessions" in status
        assert "current_phase" in status
        
        # Initialize research session
        session_id = "test_session_001"
        user_query = "Test research query"
        
        session_state = await supervisor.initialize_research_session(
            session_id, user_query, {"test": "param"}
        )
        
        assert session_state["session_id"] == session_id
        assert session_state["user_query"] == user_query
        assert session_id in supervisor.research_session_state
        
        # Check updated session status
        updated_status = supervisor.get_session_status()
        assert session_id in updated_status["active_sessions"]
        
        # Cleanup session
        await supervisor.cleanup_research_session(session_id)
        assert session_id not in supervisor.research_session_state


class TestResearchSubAgentIntegration:
    """Integration tests for ResearchSubAgent with tools."""
    
    @pytest.fixture
    async def integrated_research_agent(self, temp_storage):
        """Create fully integrated research agent."""
        # Initialize SDK
        config_override = {
            "storage_path": temp_storage,
            "debug_mode": True
        }
        await initialize_strands_sdk(config_override)
        
        # Create and initialize research agent
        research_agent = ResearchSubAgent("machine learning applications", "ml_app_001")
        await research_agent.initialize()
        
        yield research_agent
        
        await research_agent.shutdown()
    
    async def test_research_agent_execution(self, integrated_research_agent):
        """Test research agent task execution."""
        research_agent = integrated_research_agent
        
        # Create research task
        subtopic_brief = {
            "title": "Machine Learning Applications in Healthcare",
            "description": "Research current applications of ML in healthcare sector",
            "context": "Medical AI research",
            "priority": "high"
        }
        
        task_data = create_task_data(
            "research_subtopic",
            {"subtopic_brief": subtopic_brief}
        )
        
        # Execute task
        result = await research_agent.execute_task(task_data)
        
        assert result.success is True
        assert result.agent_id == research_agent.agent_id
        assert result.task_id == task_data.task_id
        
        # Verify research findings
        research_findings = result.result
        assert "subtopic" in research_findings
        assert "research_summary" in research_findings
        assert "key_insights" in research_findings
        assert "total_sources" in research_findings
        assert "confidence_score" in research_findings
        
        assert research_findings["subtopic"] == research_agent.subtopic
        assert research_findings["success"] is True
        assert len(research_findings["key_insights"]) > 0
    
    async def test_research_agent_iterative_process(self, integrated_research_agent):
        """Test research agent's iterative research process."""
        research_agent = integrated_research_agent
        
        # Monitor research status
        initial_status = research_agent.get_research_status()
        assert initial_status["current_iteration"] == 0
        assert initial_status["queries_used"] == 0
        
        # Execute research
        subtopic_brief = {
            "title": "AI Ethics",
            "description": "Research ethical considerations in AI development"
        }
        
        research_result = await research_agent.conduct_research(subtopic_brief)
        
        # Verify iterative process occurred
        final_status = research_agent.get_research_status()
        assert final_status["current_iteration"] > initial_status["current_iteration"]
        assert final_status["queries_used"] > 0
        assert final_status["sources_collected"] > 0
        
        # Verify research quality
        assert research_result["confidence_score"] > 0
        assert research_result["research_iterations"] > 0
        assert len(research_result["key_insights"]) > 0


class TestScopingAgentIntegration:
    """Integration tests for ScopingAgent with dialogue management."""
    
    @pytest.fixture
    async def integrated_scoping_agent(self, temp_storage):
        """Create fully integrated scoping agent."""
        # Initialize SDK
        config_override = {
            "storage_path": temp_storage,
            "debug_mode": True
        }
        await initialize_strands_sdk(config_override)
        
        # Create and initialize scoping agent
        scoping_agent = ScopingAgent()
        await scoping_agent.initialize()
        
        yield scoping_agent
        
        await scoping_agent.shutdown()
    
    async def test_scoping_agent_ai_analysis_mode(self, integrated_scoping_agent):
        """Test scoping agent in AI analysis mode."""
        scoping_agent = integrated_scoping_agent
        
        # Test AI-only analysis
        initial_query = "I want to research machine learning applications in finance"
        
        dialogue_context = await scoping_agent.analyze_query_requirements(initial_query)
        
        assert dialogue_context["initial_query"] == initial_query
        assert dialogue_context["mode"] == "ai_analysis"
        assert "current_understanding" in dialogue_context
        assert dialogue_context["confidence_score"] > 0
        
        # Verify understanding extraction
        understanding = dialogue_context["current_understanding"]
        assert len(understanding) > 0  # Should have extracted some requirements
    
    async def test_scoping_agent_research_brief_generation(self, integrated_scoping_agent):
        """Test research brief generation."""
        scoping_agent = integrated_scoping_agent
        
        # Create dialogue context
        dialogue_context = {
            "initial_query": "Research blockchain technology for supply chain management",
            "current_understanding": {
                "scope": "Blockchain applications in supply chain",
                "depth": "Comprehensive analysis with practical examples",
                "context": "Business and technical perspective",
                "constraints": "Focus on recent developments"
            },
            "confidence_score": 0.85,
            "rounds_completed": 1
        }
        
        # Generate research brief
        research_brief = await scoping_agent.generate_research_brief(dialogue_context)
        
        # Verify brief structure
        assert "original_query" in research_brief
        assert "research_objective" in research_brief
        assert "scope_boundaries" in research_brief
        assert "required_topics" in research_brief
        assert "success_criteria" in research_brief
        assert "estimated_complexity" in research_brief
        
        # Verify subtopics
        subtopics = research_brief["required_topics"]
        assert len(subtopics) >= 3
        assert len(subtopics) <= 5
        
        for subtopic in subtopics:
            assert "id" in subtopic
            assert "title" in subtopic
            assert "description" in subtopic
            assert "priority" in subtopic


class TestEndToEndScenarios:
    """End-to-end integration test scenarios."""
    
    @pytest.fixture
    async def full_system_setup(self, temp_storage):
        """Set up complete system for end-to-end testing."""
        # Initialize SDK
        config_override = {
            "storage_path": temp_storage,
            "debug_mode": True,
            "max_concurrent_agents": 5
        }
        await initialize_strands_sdk(config_override)
        
        # Initialize communication
        comm_hub = await initialize_global_communication()
        
        # Create agents
        supervisor = SupervisorAgent()
        await supervisor.initialize()
        
        research_agent = ResearchSubAgent("AI research", "ai_001")
        await research_agent.initialize()
        
        scoping_agent = ScopingAgent()
        await scoping_agent.initialize()
        
        # Register agents for communication
        await comm_hub.register_agent(supervisor.agent_id, {"role": "supervisor"})
        await comm_hub.register_agent(research_agent.agent_id, {"role": "researcher"})
        await comm_hub.register_agent(scoping_agent.agent_id, {"role": "scoping"})
        
        yield {
            "supervisor": supervisor,
            "research_agent": research_agent,
            "scoping_agent": scoping_agent,
            "comm_hub": comm_hub,
            "sdk_manager": get_sdk_manager()
        }
        
        # Cleanup
        await supervisor.shutdown()
        await research_agent.shutdown()
        await scoping_agent.shutdown()
        await comm_hub.stop()
    
    async def test_complete_research_workflow(self, full_system_setup):
        """Test complete research workflow from query to report."""
        system = full_system_setup
        supervisor = system["supervisor"]
        comm_hub = system["comm_hub"]
        
        # Execute complete workflow
        research_query = "What are the emerging trends in artificial intelligence for 2024?"
        
        # This would normally involve inter-agent communication
        # For this integration test, we'll test the supervisor's complete flow
        try:
            result = await supervisor.execute_control_loop(research_query)
            
            # Verify complete workflow execution
            assert result["status"] == "completed"
            assert len(result["phases_completed"]) == 3
            
            # Verify each phase produced results
            assert result["research_brief"] is not None
            assert result["research_results"] is not None
            assert result["final_report"] is not None
            
            # Verify data quality
            brief = result["research_brief"]
            assert len(brief["required_topics"]) >= 3
            
            research_results = result["research_results"]
            assert len(research_results["subtopic_results"]) >= 3
            
            final_report = result["final_report"]
            assert len(final_report["key_findings"]) > 0
            assert final_report["total_sources"] > 0
            
            print(f"✅ Complete workflow test passed:")
            print(f"   - Query: {research_query}")
            print(f"   - Subtopics researched: {len(research_results['subtopic_results'])}")
            print(f"   - Key findings: {len(final_report['key_findings'])}")
            print(f"   - Total sources: {final_report['total_sources']}")
            print(f"   - Execution time: {result['total_execution_time']:.2f}s")
            
        except Exception as e:
            pytest.fail(f"Complete workflow test failed: {str(e)}")
    
    async def test_system_error_handling(self, full_system_setup):
        """Test system error handling and recovery."""
        system = full_system_setup
        supervisor = system["supervisor"]
        
        # Test with invalid/problematic query
        problematic_query = ""  # Empty query
        
        try:
            # This should handle the error gracefully
            result = await supervisor.execute_control_loop(problematic_query)
            # The system should still produce some result, even if minimal
            assert "status" in result
            
        except Exception as e:
            # Error handling should prevent system crash
            assert "empty" in str(e).lower() or "invalid" in str(e).lower()
    
    async def test_system_performance_metrics(self, full_system_setup):
        """Test system performance and metrics collection."""
        system = full_system_setup
        supervisor = system["supervisor"]
        comm_hub = system["comm_hub"]
        sdk_manager = system["sdk_manager"]
        
        # Execute multiple operations to generate metrics
        test_query = "Brief overview of machine learning"
        
        # Record initial metrics
        initial_supervisor_metrics = supervisor.get_performance_metrics()
        initial_comm_stats = comm_hub.get_stats()
        
        # Execute research
        result = await supervisor.execute_control_loop(test_query)
        
        # Check final metrics
        final_supervisor_metrics = supervisor.get_performance_metrics()
        final_comm_stats = comm_hub.get_stats()
        
        # Verify metrics were updated
        assert final_supervisor_metrics["task_count"] > initial_supervisor_metrics["task_count"]
        assert final_supervisor_metrics["total_execution_time"] > initial_supervisor_metrics["total_execution_time"]
        
        # Verify communication metrics (if any messages were sent)
        # Note: In this test, the supervisor works internally without A2A communication
        
        # Verify system health
        assert supervisor.is_active
        assert comm_hub.is_running
        assert sdk_manager.is_initialized()
        
        print(f"✅ Performance metrics test passed:")
        print(f"   - Tasks executed: {final_supervisor_metrics['task_count']}")
        print(f"   - Total execution time: {final_supervisor_metrics['total_execution_time']:.2f}s")
        print(f"   - Average task time: {final_supervisor_metrics['average_execution_time']:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
"""
Tests for basic agent classes.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.agents.base_agent import BaseResearchAgent, TaskData, AgentResult, create_task_data
from src.agents.supervisor_agent import SupervisorAgent
from src.agents.research_sub_agent import ResearchSubAgent
from src.agents.scoping_agent import ScopingAgent


class TestBaseResearchAgent:
    """Test suite for BaseResearchAgent."""
    
    class MockAgent(BaseResearchAgent):
        """Mock implementation for testing."""
        
        async def execute_task(self, task_data: TaskData) -> AgentResult:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task_data.task_id,
                success=True,
                result={"mock": "result"}
            )
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock agent instance."""
        return self.MockAgent("test_agent", "test_role", ["test_capability"])
    
    def test_agent_initialization(self, mock_agent):
        """Test agent initialization."""
        assert mock_agent.name == "test_agent"
        assert mock_agent.role == "test_role"
        assert mock_agent.capabilities == ["test_capability"]
        assert mock_agent.agent_id.startswith("test_agent_")
        assert not mock_agent.is_active
        assert mock_agent.session_id is None
    
    async def test_agent_sdk_initialization(self, mock_agent):
        """Test agent SDK initialization."""
        # Mock SDK manager
        mock_sdk_manager = MagicMock()
        mock_sdk_manager.is_initialized.return_value = True
        mock_sdk_manager.get_runtime.return_value = AsyncMock()
        mock_sdk_manager.get_memory_system.return_value = AsyncMock()
        
        mock_runtime = AsyncMock()
        mock_runtime.create_session.return_value = "test_session_123"
        mock_sdk_manager.get_runtime.return_value = mock_runtime
        
        mock_memory = AsyncMock()
        mock_memory.create_namespace.return_value = "test_namespace"
        mock_sdk_manager.get_memory_system.return_value = mock_memory
        
        mock_agent.sdk_manager = mock_sdk_manager
        
        # Test initialization
        result = await mock_agent.initialize()
        assert result is True
        assert mock_agent.is_active
        assert mock_agent.session_id == "test_session_123"
    
    async def test_task_execution_with_timing(self, mock_agent):
        """Test task execution with timing."""
        # Mock initialization
        mock_agent.is_active = True
        
        task_data = create_task_data("test_task", {"test": "data"})
        result = await mock_agent._execute_with_timing(task_data)
        
        assert result.success
        assert result.agent_id == mock_agent.agent_id
        assert result.task_id == task_data.task_id
        assert result.execution_time is not None
        assert result.execution_time >= 0
    
    def test_status_and_metrics(self, mock_agent):
        """Test status and performance metrics."""
        status = mock_agent.get_status()
        assert status["agent_id"] == mock_agent.agent_id
        assert status["name"] == "test_agent"
        assert status["role"] == "test_role"
        assert status["is_active"] is False
        
        metrics = mock_agent.get_performance_metrics()
        assert metrics["task_count"] == 0
        assert metrics["total_execution_time"] == 0.0
        assert metrics["average_execution_time"] == 0.0


class TestSupervisorAgent:
    """Test suite for SupervisorAgent."""
    
    @pytest.fixture
    def supervisor_agent(self):
        """Create supervisor agent instance."""
        return SupervisorAgent()
    
    def test_supervisor_initialization(self, supervisor_agent):
        """Test supervisor agent initialization."""
        assert supervisor_agent.name == "supervisor"
        assert supervisor_agent.role == "research_orchestrator"
        assert "workflow_control" in supervisor_agent.capabilities
        assert "quality_assessment" in supervisor_agent.capabilities
        assert supervisor_agent.max_concurrent_agents == 5
    
    async def test_execute_task_validation(self, supervisor_agent):
        """Test task execution validation."""
        # Mock initialization
        supervisor_agent.is_active = True
        
        # Test with missing required field
        invalid_task = create_task_data("research", {"invalid": "data"})
        result = await supervisor_agent.execute_task(invalid_task)
        
        assert not result.success
        assert "Missing required field: user_query" in result.error
    
    async def test_control_loop_phases(self, supervisor_agent):
        """Test control loop phase execution."""
        # Mock SDK components
        supervisor_agent.memory_system = AsyncMock()
        supervisor_agent.memory_system.create_namespace.return_value = "test_namespace"
        supervisor_agent.memory_system.store.return_value = "test_entry_id"
        
        supervisor_agent.llm_manager = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Mock LLM response for research scoping and analysis"
        supervisor_agent.llm_manager.generate.return_value = mock_response
        
        # Test control loop execution
        result = await supervisor_agent.execute_control_loop(
            "What is artificial intelligence?",
            {"test": "parameter"}
        )
        
        assert result["status"] == "completed"
        assert "research_brief" in result
        assert "research_results" in result
        assert "final_report" in result
        assert result["phases_completed"] == ["scoping", "research", "report"]
    
    async def test_session_management(self, supervisor_agent):
        """Test research session management."""
        session_id = "test_session_123"
        user_query = "Test research query"
        
        # Mock memory system
        supervisor_agent.memory_system = AsyncMock()
        supervisor_agent.memory_system.create_namespace.return_value = session_id
        
        session_state = await supervisor_agent.initialize_research_session(
            session_id, user_query, {"test": "param"}
        )
        
        assert session_state["session_id"] == session_id
        assert session_state["user_query"] == user_query
        assert session_state["parameters"] == {"test": "param"}
        assert session_id in supervisor_agent.research_session_state
    
    def test_session_status(self, supervisor_agent):
        """Test session status reporting."""
        # Add mock session
        supervisor_agent.research_session_state["test_session"] = {
            "session_id": "test_session",
            "status": "active"
        }
        
        status = supervisor_agent.get_session_status()
        assert "test_session" in status["active_sessions"]
        assert status["total_sessions"] == 1
        
        specific_status = supervisor_agent.get_session_status("test_session")
        assert specific_status["session_id"] == "test_session"


class TestResearchSubAgent:
    """Test suite for ResearchSubAgent."""
    
    @pytest.fixture
    def research_agent(self):
        """Create research sub-agent instance."""
        return ResearchSubAgent("artificial intelligence", "ai_001")
    
    def test_research_agent_initialization(self, research_agent):
        """Test research agent initialization."""
        assert research_agent.subtopic == "artificial intelligence"
        assert research_agent.role == "specialized_researcher"
        assert "web_search" in research_agent.capabilities
        assert research_agent.max_iterations == 5
        assert research_agent.min_sources == 3
    
    async def test_task_execution_validation(self, research_agent):
        """Test research task validation."""
        # Mock initialization
        research_agent.is_active = True
        
        # Test with missing required field
        invalid_task = create_task_data("research", {"invalid": "data"})
        result = await research_agent.execute_task(invalid_task)
        
        assert not result.success
        assert "Missing required fields" in result.error
    
    async def test_search_query_generation(self, research_agent):
        """Test search query generation."""
        # Mock LLM manager
        research_agent.llm_manager = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "1. AI machine learning algorithms\n2. artificial intelligence applications\n3. AI research trends"
        research_agent.llm_manager.generate.return_value = mock_response
        
        subtopic_brief = {
            "title": "Artificial Intelligence",
            "description": "Study of AI technologies"
        }
        
        queries = await research_agent.generate_search_queries(subtopic_brief, 1)
        
        assert len(queries) > 0
        assert len(queries) <= 3
        for query in queries:
            assert len(query) > 5
    
    async def test_search_execution(self, research_agent):
        """Test search execution."""
        queries = ["AI research", "machine learning"]
        
        # Mock web search tool
        research_agent.web_search_tool = AsyncMock()
        mock_search_result = {
            "results": [
                {
                    "title": "Test Paper",
                    "url": "https://example.com",
                    "snippet": "Test snippet",
                    "domain": "example.com",
                    "relevance_score": 0.9
                }
            ]
        }
        research_agent.web_search_tool.search.return_value = mock_search_result
        
        results = await research_agent.execute_searches(queries)
        
        assert len(results["queries_executed"]) == 2
        assert results["total_results"] == 2
        assert len(results["unique_sources"]) == 2
    
    async def test_research_sufficiency_check(self, research_agent):
        """Test research sufficiency assessment."""
        # Mock memory system
        research_agent.memory_system = AsyncMock()
        research_agent.memory_system.store.return_value = "test_entry"
        
        # Test with sufficient data
        analysis = {
            "confidence": 0.8,
            "source_quality": 0.9,
            "key_insights": ["insight1", "insight2", "insight3"]
        }
        research_agent.sources_collected = [{"url": f"https://example{i}.com"} for i in range(5)]
        
        is_sufficient = await research_agent.is_research_sufficient(analysis)
        assert is_sufficient is True
        
        # Test with insufficient data
        analysis_insufficient = {
            "confidence": 0.5,
            "source_quality": 0.6,
            "key_insights": ["insight1"]
        }
        research_agent.sources_collected = [{"url": "https://example.com"}]
        
        is_sufficient = await research_agent.is_research_sufficient(analysis_insufficient)
        assert is_sufficient is False
    
    def test_research_status(self, research_agent):
        """Test research status reporting."""
        research_agent.current_iteration = 2
        research_agent.search_queries_used = ["query1", "query2"]
        research_agent.sources_collected = [{"url": "test1"}, {"url": "test2"}]
        
        status = research_agent.get_research_status()
        
        assert status["subtopic"] == "artificial intelligence"
        assert status["current_iteration"] == 2
        assert status["queries_used"] == 2
        assert status["sources_collected"] == 2


class TestScopingAgent:
    """Test suite for ScopingAgent."""
    
    @pytest.fixture
    def scoping_agent(self):
        """Create scoping agent instance."""
        return ScopingAgent()
    
    def test_scoping_agent_initialization(self, scoping_agent):
        """Test scoping agent initialization."""
        assert scoping_agent.name == "scoping_agent"
        assert scoping_agent.role == "requirement_clarifier"
        assert "dialogue_management" in scoping_agent.capabilities
        assert scoping_agent.max_clarification_rounds == 5
        assert scoping_agent.min_confidence_threshold == 0.8
    
    async def test_task_execution_validation(self, scoping_agent):
        """Test scoping task validation."""
        # Mock initialization
        scoping_agent.is_active = True
        
        # Test with missing required field
        invalid_task = create_task_data("scoping", {"invalid": "data"})
        result = await scoping_agent.execute_task(invalid_task)
        
        assert not result.success
        assert "Missing required field: initial_query" in result.error
    
    async def test_ai_analysis_mode(self, scoping_agent):
        """Test AI-only analysis mode."""
        # Mock LLM manager
        scoping_agent.llm_manager = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "This query requires comprehensive analysis of scope, depth, and practical applications."
        scoping_agent.llm_manager.generate.return_value = mock_response
        
        initial_query = "What is machine learning?"
        
        dialogue_context = await scoping_agent.analyze_query_requirements(initial_query)
        
        assert dialogue_context["initial_query"] == initial_query
        assert dialogue_context["mode"] == "ai_analysis"
        assert dialogue_context["confidence_score"] == 0.75
        assert "current_understanding" in dialogue_context
    
    async def test_clarification_question_generation(self, scoping_agent):
        """Test clarification question generation."""
        # Mock LLM manager
        scoping_agent.llm_manager = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "What specific aspects of machine learning are you most interested in?\nAre you looking for theoretical knowledge or practical applications?"
        scoping_agent.llm_manager.generate.return_value = mock_response
        
        dialogue_context = {
            "current_understanding": {},
            "clarifications": [],
            "rounds_completed": 0
        }
        
        questions = await scoping_agent.generate_clarification_questions(
            "machine learning", dialogue_context
        )
        
        assert len(questions) <= 2
        for question in questions:
            assert "?" in question
            assert len(question) > 10
    
    async def test_understanding_update(self, scoping_agent):
        """Test understanding update from user responses."""
        # Mock LLM manager
        scoping_agent.llm_manager = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "User wants detailed technical analysis for practical implementation"
        scoping_agent.llm_manager.generate.return_value = mock_response
        
        current_understanding = {}
        question = "What level of detail do you need?"
        user_response = "I need detailed technical information for implementation"
        
        updated = await scoping_agent.update_understanding(
            current_understanding, question, user_response
        )
        
        assert "depth" in updated
        assert updated["depth"] == user_response
    
    async def test_subtopic_decomposition(self, scoping_agent):
        """Test subtopic decomposition."""
        # Mock LLM manager
        scoping_agent.llm_manager = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "1. Core ML algorithms and concepts\n2. Data preprocessing and feature engineering\n3. Model training and evaluation\n4. Practical applications and deployment"
        scoping_agent.llm_manager.generate.return_value = mock_response
        
        understanding = {
            "scope": "comprehensive ML study",
            "depth": "detailed technical",
            "context": "practical implementation"
        }
        
        subtopics = await scoping_agent.decompose_into_subtopics(
            "machine learning research", understanding
        )
        
        assert len(subtopics) >= 3
        assert len(subtopics) <= 5
        
        for subtopic in subtopics:
            assert "id" in subtopic
            assert "title" in subtopic
            assert "description" in subtopic
            assert "priority" in subtopic
    
    async def test_research_brief_generation(self, scoping_agent):
        """Test research brief generation."""
        # Mock memory system
        scoping_agent.memory_system = AsyncMock()
        scoping_agent.memory_system.store.return_value = "brief_entry"
        
        # Mock LLM manager for subtopic generation
        scoping_agent.llm_manager = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "1. Machine learning fundamentals\n2. Algorithms and techniques\n3. Practical applications"
        scoping_agent.llm_manager.generate.return_value = mock_response
        
        dialogue_context = {
            "initial_query": "machine learning research",
            "current_understanding": {
                "scope": "comprehensive study",
                "depth": "detailed analysis",
                "context": "academic research"
            },
            "confidence_score": 0.85,
            "rounds_completed": 2
        }
        
        brief = await scoping_agent.generate_research_brief(dialogue_context)
        
        assert brief["original_query"] == "machine learning research"
        assert "research_objective" in brief
        assert "scope_boundaries" in brief
        assert "required_topics" in brief
        assert "success_criteria" in brief
        assert brief["clarification_metadata"]["confidence_score"] == 0.85
    
    def test_complexity_assessment(self, scoping_agent):
        """Test research complexity assessment."""
        # Test high complexity
        high_query = "comprehensive technical analysis of advanced machine learning"
        high_subtopics = [{"id": f"t{i}"} for i in range(5)]
        complexity = scoping_agent._assess_complexity(high_query, high_subtopics)
        assert complexity == "high"
        
        # Test low complexity
        low_query = "basic introduction to machine learning"
        low_subtopics = [{"id": "t1"}]
        complexity = scoping_agent._assess_complexity(low_query, low_subtopics)
        assert complexity == "low"
        
        # Test medium complexity
        medium_query = "machine learning research overview"
        medium_subtopics = [{"id": f"t{i}"} for i in range(3)]
        complexity = scoping_agent._assess_complexity(medium_query, medium_subtopics)
        assert complexity == "medium"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
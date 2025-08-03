"""
Supervisor Agent for orchestrating the research process.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseResearchAgent, TaskData, AgentResult, AgentCapabilityMixin
from ..tools.llm_interface import create_message
from ..configs.agent_settings import get_agent_settings


class SupervisorAgent(BaseResearchAgent, AgentCapabilityMixin):
    """
    Supervisor Agent that orchestrates the entire research process.
    
    Responsibilities:
    - Execute 3-phase control loop (Scoping -> Research -> Report)
    - Manage sub-agents lifecycle
    - Quality control and feedback
    - Resource allocation
    """
    
    def __init__(self):
        """Initialize Supervisor Agent."""
        super().__init__(
            name="supervisor",
            role="research_orchestrator",
            capabilities=[
                "workflow_control", 
                "quality_assessment", 
                "resource_management",
                "agent_coordination",
                "session_management"
            ]
        )
        
        # Control loop state
        self.current_phase = None
        self.research_session_state = {}
        self.active_sub_agents = {}
        
        # Quality control - load from settings
        self.agent_settings = get_agent_settings()
        self.quality_thresholds = self.agent_settings.get_quality_thresholds()
        
        # Resource management - load from settings
        concurrency_settings = self.agent_settings.get_concurrency_settings()
        timeout_settings = self.agent_settings.get_timeouts()
        self.max_concurrent_agents = concurrency_settings.get("max_sub_agents", 5)
        self.agent_timeout = timeout_settings.get("task_execution", 300)
    
    async def execute_task(self, task_data: TaskData) -> AgentResult:
        """
        Execute supervisor task - typically the main control loop.
        
        Args:
            task_data: Task containing user query and parameters
            
        Returns:
            Final research result
        """
        if not await self.validate_task_data(task_data, ["user_query"]):
            return self.create_result(
                task_data.task_id, 
                False, 
                error="Missing required field: user_query"
            )
        
        user_query = task_data.content["user_query"]
        parameters = task_data.content.get("parameters", {})
        
        try:
            # Execute the 3-phase control loop
            result = await self.execute_control_loop(user_query, parameters)
            
            return self.create_result(
                task_data.task_id,
                True,
                result=result,
                metadata={
                    "phases_completed": ["scoping", "research", "report"],
                    "sub_agents_used": len(self.active_sub_agents),
                    "total_execution_time": result.get("total_execution_time", 0)
                }
            )
            
        except Exception as e:
            return self.create_result(
                task_data.task_id,
                False,
                error=f"Control loop execution failed: {str(e)}"
            )
    
    async def execute_control_loop(self, user_query: str, 
                                 parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the 3-phase research control loop.
        
        Args:
            user_query: User's research query
            parameters: Optional execution parameters
            
        Returns:
            Complete research results
        """
        start_time = datetime.utcnow()
        session_id = f"research_session_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        await self.log_task_progress(session_id, "control_loop_start", {
            "query": user_query,
            "parameters": parameters or {}
        })
        
        try:
            # Initialize research session
            session_state = await self.initialize_research_session(
                session_id, user_query, parameters
            )
            
            # Phase 1: Scoping
            self.current_phase = "scoping"
            await self.log_task_progress(session_id, "phase_1_scoping_started")
            
            research_brief = await self.execute_scoping_phase(
                user_query, session_state
            )
            session_state["research_brief"] = research_brief
            
            await self.log_task_progress(session_id, "phase_1_scoping_completed", {
                "subtopics_identified": len(research_brief.get("required_topics", []))
            })
            
            # Phase 2: Research
            self.current_phase = "research"
            await self.log_task_progress(session_id, "phase_2_research_started")
            
            research_results = await self.execute_research_phase(
                research_brief, session_state
            )
            session_state["research_results"] = research_results
            
            await self.log_task_progress(session_id, "phase_2_research_completed", {
                "results_collected": len(research_results.get("subtopic_results", {}))
            })
            
            # Phase 3: Report Generation
            self.current_phase = "report"
            await self.log_task_progress(session_id, "phase_3_report_started")
            
            final_report = await self.execute_report_phase(
                research_results, research_brief, session_state
            )
            
            await self.log_task_progress(session_id, "phase_3_report_completed")
            
            # Calculate total execution time
            end_time = datetime.utcnow()
            total_time = (end_time - start_time).total_seconds()
            
            # Store session results
            await self.store_memory(
                f"session_{session_id}",
                {
                    "query": user_query,
                    "research_brief": research_brief,
                    "research_results": research_results,
                    "final_report": final_report,
                    "execution_time": total_time,
                    "completed_at": end_time.isoformat()
                }
            )
            
            return {
                "session_id": session_id,
                "user_query": user_query,
                "research_brief": research_brief,
                "research_results": research_results,
                "final_report": final_report,
                "total_execution_time": total_time,
                "phases_completed": ["scoping", "research", "report"],
                "status": "completed"
            }
            
        except Exception as e:
            await self.log_task_progress(session_id, "control_loop_failed", {
                "error": str(e),
                "current_phase": self.current_phase
            })
            raise
        
        finally:
            # Cleanup
            self.current_phase = None
            await self.cleanup_research_session(session_id)
    
    async def initialize_research_session(self, session_id: str, 
                                        user_query: str,
                                        parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initialize a new research session.
        
        Args:
            session_id: Session identifier
            user_query: User's research query
            parameters: Optional parameters
            
        Returns:
            Session state dictionary
        """
        session_state = {
            "session_id": session_id,
            "user_query": user_query,
            "parameters": parameters or {},
            "created_at": datetime.utcnow().isoformat(),
            "phase_results": {},
            "active_agents": {},
            "quality_scores": {}
        }
        
        self.research_session_state[session_id] = session_state
        
        # Create session memory namespace
        await self.memory_system.create_namespace(
            f"session_{session_id}",
            retention_policy="30_days"
        )
        
        return session_state
    
    async def execute_scoping_phase(self, user_query: str, 
                                  session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the scoping phase to clarify research requirements.
        
        Args:
            user_query: User's research query
            session_state: Current session state
            
        Returns:
            Research brief with clarified requirements
        """
        # For Phase 1, we'll implement a basic scoping without sub-agents
        # This will be enhanced in later phases when ScopingAgent is implemented
        
        messages = [
            create_message("system", 
                          "You are a research scoping specialist. Your job is to analyze "
                          "research queries and create comprehensive research briefs."),
            create_message("user", 
                          f"Please analyze this research query and create a research brief: {user_query}")
        ]
        
        scoping_response = await self.process_message(messages, {
            "task": "research_scoping",
            "query": user_query
        })
        
        # Extract key components (simplified for Phase 1)
        research_brief = {
            "original_query": user_query,
            "research_objective": f"Comprehensive research on: {user_query}",
            "scope_boundaries": {
                "temporal": "Recent developments and established knowledge",
                "depth": "Comprehensive analysis with practical insights",
                "sources": "Academic papers, authoritative sources, recent publications"
            },
            "required_topics": await self._identify_subtopics(user_query),
            "success_criteria": [
                "Comprehensive coverage of the topic",
                "High-quality sources and citations",
                "Clear and actionable insights",
                "Well-structured presentation"
            ],
            "estimated_complexity": "medium",
            "scoping_completed_at": datetime.utcnow().isoformat()
        }
        
        return research_brief
    
    async def _identify_subtopics(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Identify subtopics for research based on the query.
        
        Args:
            user_query: User's research query
            
        Returns:
            List of subtopic dictionaries
        """
        messages = [
            create_message("system",
                          "You are a research planning expert. Break down research queries "
                          "into 3-5 specific subtopics that need to be investigated."),
            create_message("user",
                          f"Break down this research query into specific subtopics: {user_query}")
        ]
        
        response = await self.process_message(messages)
        
        # For Phase 1, create basic subtopics
        # This will be enhanced with better parsing in later phases
        subtopics = [
            {
                "id": f"subtopic_1",
                "title": f"Core concepts and definitions related to {user_query}",
                "description": f"Fundamental understanding of {user_query}",
                "priority": "high",
                "estimated_effort": "medium"
            },
            {
                "id": f"subtopic_2", 
                "title": f"Current research and developments in {user_query}",
                "description": f"Recent advances and ongoing research in {user_query}",
                "priority": "high",
                "estimated_effort": "high"
            },
            {
                "id": f"subtopic_3",
                "title": f"Practical applications and implications of {user_query}",
                "description": f"Real-world uses and impact of {user_query}",
                "priority": "medium",
                "estimated_effort": "medium"
            }
        ]
        
        return subtopics
    
    async def execute_research_phase(self, research_brief: Dict[str, Any],
                                   session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the research phase with parallel sub-agent coordination.
        
        Args:
            research_brief: Research brief from scoping phase
            session_state: Current session state
            
        Returns:
            Compiled research results
        """
        subtopics = research_brief.get("required_topics", [])
        research_results = {
            "subtopic_results": {},
            "quality_assessment": {},
            "iteration_count": 1,
            "research_completed_at": datetime.utcnow().isoformat()
        }
        
        # For Phase 1, we'll simulate research results
        # This will be enhanced with actual sub-agents in Phase 2
        for subtopic in subtopics:
            subtopic_id = subtopic["id"]
            
            # Simulate research for this subtopic
            subtopic_result = await self._simulate_subtopic_research(
                subtopic, research_brief["original_query"]
            )
            
            research_results["subtopic_results"][subtopic_id] = subtopic_result
        
        # Assess overall quality
        quality_assessment = await self._assess_research_quality(research_results)
        research_results["quality_assessment"] = quality_assessment
        
        return research_results
    
    async def _simulate_subtopic_research(self, subtopic: Dict[str, Any], 
                                        original_query: str) -> Dict[str, Any]:
        """
        Simulate research results for a subtopic (Phase 1 implementation).
        
        Args:
            subtopic: Subtopic information
            original_query: Original research query
            
        Returns:
            Simulated research results
        """
        messages = [
            create_message("system",
                          "You are a research analyst. Provide detailed analysis "
                          "on the given subtopic."),
            create_message("user",
                          f"Research this subtopic: {subtopic['title']}\n"
                          f"In context of: {original_query}\n"
                          f"Description: {subtopic['description']}")
        ]
        
        analysis = await self.process_message(messages)
        
        return {
            "subtopic_id": subtopic["id"],
            "title": subtopic["title"],
            "analysis": analysis,
            "sources": [
                {"title": "Academic Source 1", "url": "https://example.com/source1", "relevance": 0.9},
                {"title": "Research Paper 2", "url": "https://example.com/source2", "relevance": 0.85},
                {"title": "Industry Report 3", "url": "https://example.com/source3", "relevance": 0.8}
            ],
            "key_findings": [
                f"Key insight 1 related to {subtopic['title']}",
                f"Important finding 2 about {subtopic['title']}",
                f"Significant observation 3 regarding {subtopic['title']}"
            ],
            "confidence_score": 0.85,
            "research_time": 45.0,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    async def _assess_research_quality(self, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the quality of research results.
        
        Args:
            research_results: Research results to assess
            
        Returns:
            Quality assessment
        """
        subtopic_results = research_results.get("subtopic_results", {})
        
        if not subtopic_results:
            return {"overall_score": 0.0, "meets_threshold": False}
        
        # Calculate average confidence scores
        confidence_scores = [
            result.get("confidence_score", 0.0) 
            for result in subtopic_results.values()
        ]
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        quality_assessment = {
            "overall_score": avg_confidence,
            "accuracy": avg_confidence,
            "depth": 0.8,  # Simulated
            "completeness": 0.85,  # Simulated
            "source_quality": 0.9,  # Simulated
            "meets_threshold": avg_confidence >= self.quality_thresholds["accuracy"],
            "subtopic_scores": {
                subtopic_id: result.get("confidence_score", 0.0)
                for subtopic_id, result in subtopic_results.items()
            }
        }
        
        return quality_assessment
    
    async def execute_report_phase(self, research_results: Dict[str, Any],
                                 research_brief: Dict[str, Any],
                                 session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the report generation phase.
        
        Args:
            research_results: Results from research phase
            research_brief: Research brief from scoping phase
            session_state: Current session state
            
        Returns:
            Final research report
        """
        # Compile all findings
        subtopic_results = research_results.get("subtopic_results", {})
        
        # Generate executive summary
        summary_content = []
        key_findings = []
        
        for subtopic_id, result in subtopic_results.items():
            summary_content.append(f"**{result['title']}**\n{result['analysis'][:200]}...")
            key_findings.extend(result.get("key_findings", []))
        
        messages = [
            create_message("system",
                          "You are a research report writer. Create a comprehensive "
                          "final report based on the research findings."),
            create_message("user",
                          f"Create a final research report for: {research_brief['original_query']}\n"
                          f"Key findings: {key_findings[:5]}\n"  # Limit for token efficiency
                          f"Research objective: {research_brief['research_objective']}")
        ]
        
        final_report_content = await self.process_message(messages)
        
        final_report = {
            "title": f"Research Report: {research_brief['original_query']}",
            "executive_summary": final_report_content,
            "research_objective": research_brief["research_objective"],
            "methodology": "Multi-agent parallel research with quality feedback loops",
            "key_findings": key_findings,
            "detailed_findings": {
                subtopic_id: {
                    "title": result["title"],
                    "analysis": result["analysis"],
                    "sources": result["sources"]
                }
                for subtopic_id, result in subtopic_results.items()
            },
            "quality_metrics": research_results.get("quality_assessment", {}),
            "recommendations": [
                "Further research may be beneficial in specific areas",
                "Consider practical implementation of key findings",
                "Regular updates recommended as field evolves"
            ],
            "generated_at": datetime.utcnow().isoformat(),
            "total_sources": sum(
                len(result.get("sources", [])) 
                for result in subtopic_results.values()
            )
        }
        
        return final_report
    
    async def cleanup_research_session(self, session_id: str):
        """
        Clean up resources for a completed research session.
        
        Args:
            session_id: Session to clean up
        """
        # Terminate any active sub-agents
        if session_id in self.research_session_state:
            session_state = self.research_session_state[session_id]
            
            for agent_id in session_state.get("active_agents", {}):
                if agent_id in self.active_sub_agents:
                    try:
                        await self.active_sub_agents[agent_id].shutdown()
                        del self.active_sub_agents[agent_id]
                    except Exception as e:
                        self.logger.warning(f"Failed to cleanup agent {agent_id}: {e}")
            
            # Remove from active sessions (keep in memory storage)
            del self.research_session_state[session_id]
        
        self.logger.info("Research session cleaned up", session_id=session_id)
    
    def get_session_status(self, session_id: str = None) -> Dict[str, Any]:
        """
        Get status of research sessions.
        
        Args:
            session_id: Optional specific session ID
            
        Returns:
            Session status information
        """
        if session_id:
            if session_id in self.research_session_state:
                return self.research_session_state[session_id]
            else:
                return {"error": f"Session {session_id} not found"}
        else:
            return {
                "active_sessions": list(self.research_session_state.keys()),
                "total_sessions": len(self.research_session_state),
                "current_phase": self.current_phase,
                "active_sub_agents": len(self.active_sub_agents)
            }
"""
Scoping Agent for requirement clarification and research brief generation.
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .base_agent import BaseResearchAgent, TaskData, AgentResult, AgentCapabilityMixin
from ..tools.llm_interface import create_message


class ScopingAgent(BaseResearchAgent, AgentCapabilityMixin):
    """
    Scoping Agent that handles requirement clarification through interactive dialogue.
    
    Responsibilities:
    - Conduct clarification dialogue with users
    - Extract context and requirements from conversations
    - Generate comprehensive research briefs
    - Decompose complex queries into specific subtopics
    """
    
    def __init__(self):
        """Initialize Scoping Agent."""
        super().__init__(
            name="scoping_agent",
            role="requirement_clarifier",
            capabilities=[
                "dialogue_management",
                "context_extraction",
                "brief_generation",
                "requirement_analysis",
                "subtopic_decomposition"
            ]
        )
        
        # Dialogue management
        self.max_clarification_rounds = 5
        self.min_confidence_threshold = 0.8
        self.current_dialogue_context = {}
        
        # Question generation templates
        self.clarification_templates = {
            "scope": [
                "What specific aspects of {topic} are you most interested in?",
                "Are you looking for theoretical knowledge or practical applications of {topic}?",
                "What is the intended use or purpose of this research on {topic}?"
            ],
            "depth": [
                "How detailed should the analysis of {topic} be?",
                "Are you looking for a broad overview or deep technical details about {topic}?",
                "What level of expertise should this research assume about {topic}?"
            ],
            "context": [
                "What is the background or context for this research on {topic}?",
                "Are there specific industries, domains, or applications you're focusing on for {topic}?",
                "What prompted your interest in researching {topic}?"
            ],
            "constraints": [
                "Are there any time periods, geographic regions, or other constraints for {topic}?",
                "Are there specific sources or types of information you prefer for {topic}?",
                "Are there any aspects of {topic} you want to exclude from the research?"
            ]
        }
    
    async def execute_task(self, task_data: TaskData) -> AgentResult:
        """
        Execute scoping task to clarify research requirements.
        
        Args:
            task_data: Task containing initial query and optional user interaction callback
            
        Returns:
            Research brief with clarified requirements
        """
        required_fields = ["initial_query"]
        if not await self.validate_task_data(task_data, required_fields):
            return self.create_result(
                task_data.task_id,
                False,
                error=f"Missing required field: initial_query"
            )
        
        initial_query = task_data.content["initial_query"]
        user_callback = task_data.content.get("user_callback")  # Optional interactive callback
        
        try:
            # Conduct clarification dialogue
            if user_callback:
                dialogue_context = await self.conduct_clarification_dialogue(
                    initial_query, user_callback
                )
            else:
                # Non-interactive mode - use AI analysis only
                dialogue_context = await self.analyze_query_requirements(initial_query)
            
            # Generate research brief
            research_brief = await self.generate_research_brief(dialogue_context)
            
            return self.create_result(
                task_data.task_id,
                True,
                result=research_brief,
                metadata={
                    "clarification_rounds": dialogue_context.get("rounds_completed", 0),
                    "confidence_score": dialogue_context.get("confidence_score", 0.0),
                    "interactive_mode": user_callback is not None
                }
            )
            
        except Exception as e:
            return self.create_result(
                task_data.task_id,
                False,
                error=f"Scoping failed: {str(e)}"
            )
    
    async def conduct_clarification_dialogue(self, initial_query: str,
                                           user_callback: Callable[[str], str]) -> Dict[str, Any]:
        """
        Conduct interactive clarification dialogue with user.
        
        Args:
            initial_query: User's initial research query
            user_callback: Function to ask questions to user
            
        Returns:
            Dialogue context with clarified requirements
        """
        dialogue_context = {
            "initial_query": initial_query,
            "clarifications": [],
            "user_responses": [],
            "current_understanding": {},
            "rounds_completed": 0,
            "confidence_score": 0.0
        }
        
        await self.log_task_progress("dialogue_start", "beginning_clarification", {
            "initial_query": initial_query
        })
        
        # Store initial context
        await self.store_memory("dialogue_context", dialogue_context)
        
        for round_num in range(1, self.max_clarification_rounds + 1):
            dialogue_context["rounds_completed"] = round_num
            
            # Generate clarification questions
            questions = await self.generate_clarification_questions(
                initial_query, dialogue_context
            )
            
            if not questions:
                break  # No more questions needed
            
            # Ask user questions
            for question in questions:
                try:
                    user_response = user_callback(question)
                    
                    dialogue_context["clarifications"].append(question)
                    dialogue_context["user_responses"].append(user_response)
                    
                    # Update understanding based on response
                    dialogue_context["current_understanding"] = await self.update_understanding(
                        dialogue_context["current_understanding"],
                        question,
                        user_response
                    )
                    
                    await self.log_task_progress("dialogue_round", f"round_{round_num}", {
                        "question": question,
                        "response_length": len(user_response)
                    })
                    
                except Exception as e:
                    self.logger.warning(f"User interaction failed: {e}")
                    break
            
            # Check if clarification is sufficient
            confidence_score = await self.assess_clarification_confidence(dialogue_context)
            dialogue_context["confidence_score"] = confidence_score
            
            if confidence_score >= self.min_confidence_threshold:
                await self.log_task_progress("dialogue_complete", "sufficient_clarity_achieved")
                break
        
        # Store final dialogue context
        await self.store_memory("final_dialogue_context", dialogue_context)
        
        return dialogue_context
    
    async def analyze_query_requirements(self, initial_query: str) -> Dict[str, Any]:
        """
        Analyze query requirements without user interaction (AI-only mode).
        
        Args:
            initial_query: User's initial research query
            
        Returns:
            Analyzed requirements context
        """
        messages = [
            create_message("system",
                          "You are a research requirements analyst. Analyze research queries "
                          "to extract scope, depth, context, and constraints."),
            create_message("user",
                          f"Analyze this research query and identify the requirements:\n"
                          f"Query: {initial_query}\n\n"
                          f"Extract:\n"
                          f"- Research scope and focus areas\n"
                          f"- Required depth and detail level\n"
                          f"- Context and background\n"
                          f"- Any implicit constraints or preferences")
        ]
        
        analysis_response = await self.process_message(messages)
        
        # Parse analysis into structured format
        dialogue_context = {
            "initial_query": initial_query,
            "clarifications": ["AI analysis of query requirements"],
            "user_responses": [analysis_response],
            "current_understanding": await self.extract_requirements_from_analysis(
                initial_query, analysis_response
            ),
            "rounds_completed": 1,
            "confidence_score": 0.75,  # Moderate confidence for AI-only analysis
            "mode": "ai_analysis"
        }
        
        return dialogue_context
    
    async def generate_clarification_questions(self, initial_query: str,
                                             dialogue_context: Dict[str, Any]) -> List[str]:
        """
        Generate clarification questions based on current understanding.
        
        Args:
            initial_query: Original query
            dialogue_context: Current dialogue state
            
        Returns:
            List of clarification questions
        """
        current_understanding = dialogue_context.get("current_understanding", {})
        previous_questions = dialogue_context.get("clarifications", [])
        round_num = dialogue_context.get("rounds_completed", 0)
        
        # Determine what aspects need clarification
        missing_aspects = []
        if not current_understanding.get("scope"):
            missing_aspects.append("scope")
        if not current_understanding.get("depth"):
            missing_aspects.append("depth")
        if not current_understanding.get("context"):
            missing_aspects.append("context")
        if not current_understanding.get("constraints"):
            missing_aspects.append("constraints")
        
        if not missing_aspects:
            return []  # No clarification needed
        
        # Generate questions for missing aspects
        questions = []
        
        # Focus on one aspect per round
        aspect = missing_aspects[0]
        templates = self.clarification_templates.get(aspect, [])
        
        if templates:
            # Use LLM to generate contextual questions
            messages = [
                create_message("system",
                              "You are a research clarification specialist. Generate specific, "
                              "helpful questions to clarify research requirements."),
                create_message("user",
                              f"Generate 1-2 clarification questions about the {aspect} of this research query:\n"
                              f"Query: {initial_query}\n"
                              f"Focus: {aspect}\n"
                              f"Previous questions asked: {previous_questions}\n"
                              f"Make questions specific and actionable.")
            ]
            
            response = await self.process_message(messages)
            
            # Extract questions from response
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if '?' in line and len(line) > 20:
                    # Clean up question format
                    question = line.replace('-', '').replace('*', '').replace('1.', '').replace('2.', '').strip()
                    if question and question not in previous_questions:
                        questions.append(question)
        
        # Limit to 2 questions per round
        return questions[:2]
    
    async def update_understanding(self, current_understanding: Dict[str, Any],
                                 question: str, user_response: str) -> Dict[str, Any]:
        """
        Update understanding based on user response.
        
        Args:
            current_understanding: Current understanding state
            question: Question that was asked
            user_response: User's response
            
        Returns:
            Updated understanding
        """
        messages = [
            create_message("system",
                          "You are a requirement extraction specialist. Extract structured "
                          "information from user responses to research clarification questions."),
            create_message("user",
                          f"Question asked: {question}\n"
                          f"User response: {user_response}\n\n"
                          f"Extract information about:\n"
                          f"- Research scope and focus\n"
                          f"- Required depth and detail\n"
                          f"- Context and background\n"
                          f"- Constraints and preferences\n"
                          f"Current understanding: {current_understanding}")
        ]
        
        extraction_response = await self.process_message(messages)
        
        # Update understanding structure
        updated_understanding = current_understanding.copy()
        
        # Simple keyword-based extraction for Phase 1
        response_lower = user_response.lower()
        
        # Update scope
        if any(word in response_lower for word in ["focus", "specific", "particular", "mainly"]):
            updated_understanding["scope"] = user_response
        
        # Update depth
        if any(word in response_lower for word in ["detailed", "overview", "deep", "technical", "basic"]):
            updated_understanding["depth"] = user_response
        
        # Update context
        if any(word in response_lower for word in ["because", "context", "background", "purpose", "use"]):
            updated_understanding["context"] = user_response
        
        # Update constraints
        if any(word in response_lower for word in ["constraint", "limit", "exclude", "only", "recent"]):
            updated_understanding["constraints"] = user_response
        
        return updated_understanding
    
    async def extract_requirements_from_analysis(self, query: str,
                                               analysis: str) -> Dict[str, Any]:
        """
        Extract structured requirements from AI analysis.
        
        Args:
            query: Original query
            analysis: AI analysis response
            
        Returns:
            Structured requirements
        """
        # Simple extraction based on analysis content
        analysis_lower = analysis.lower()
        
        requirements = {}
        
        # Extract scope information
        if "scope" in analysis_lower or "focus" in analysis_lower:
            requirements["scope"] = f"Research focus on key aspects of {query}"
        
        # Extract depth information  
        if "detailed" in analysis_lower or "comprehensive" in analysis_lower:
            requirements["depth"] = "Comprehensive analysis with detailed insights"
        elif "overview" in analysis_lower or "broad" in analysis_lower:
            requirements["depth"] = "Broad overview with key highlights"
        
        # Extract context
        if "practical" in analysis_lower or "application" in analysis_lower:
            requirements["context"] = "Focus on practical applications and real-world use"
        
        # Default values
        if not requirements.get("scope"):
            requirements["scope"] = f"Comprehensive research on {query}"
        if not requirements.get("depth"):
            requirements["depth"] = "Balanced depth with key insights and practical information"
        if not requirements.get("context"):
            requirements["context"] = "General research for understanding and knowledge"
        
        return requirements
    
    async def assess_clarification_confidence(self, dialogue_context: Dict[str, Any]) -> float:
        """
        Assess confidence in current understanding.
        
        Args:
            dialogue_context: Current dialogue state
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        current_understanding = dialogue_context.get("current_understanding", {})
        user_responses = dialogue_context.get("user_responses", [])
        
        # Calculate confidence based on information completeness
        aspects_covered = 0
        total_aspects = 4  # scope, depth, context, constraints
        
        if current_understanding.get("scope"):
            aspects_covered += 1
        if current_understanding.get("depth"):
            aspects_covered += 1
        if current_understanding.get("context"):
            aspects_covered += 1
        if current_understanding.get("constraints"):
            aspects_covered += 0.5  # Constraints are optional
        
        completeness_score = min(1.0, aspects_covered / total_aspects)
        
        # Factor in response quality (length and detail)
        avg_response_length = sum(len(resp) for resp in user_responses) / len(user_responses) if user_responses else 0
        response_quality = min(1.0, avg_response_length / 100)  # Normalize to 100 chars
        
        # Combined confidence score
        confidence = (completeness_score * 0.7) + (response_quality * 0.3)
        
        return min(1.0, confidence)
    
    async def generate_research_brief(self, dialogue_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive research brief from dialogue context.
        
        Args:
            dialogue_context: Completed dialogue context
            
        Returns:
            Structured research brief
        """
        initial_query = dialogue_context["initial_query"]
        current_understanding = dialogue_context.get("current_understanding", {})
        confidence_score = dialogue_context.get("confidence_score", 0.0)
        
        # Extract key information
        scope = current_understanding.get("scope", f"Comprehensive research on {initial_query}")
        depth = current_understanding.get("depth", "Balanced analysis with practical insights")
        context = current_understanding.get("context", "General research and knowledge building")
        constraints = current_understanding.get("constraints", "No specific constraints identified")
        
        # Generate subtopics
        subtopics = await self.decompose_into_subtopics(initial_query, current_understanding)
        
        # Create research brief
        research_brief = {
            "original_query": initial_query,
            "research_objective": scope,
            "scope_boundaries": {
                "focus_areas": scope,
                "depth_level": depth,
                "context": context,
                "constraints": constraints,
                "temporal_scope": "Current and recent developments",
                "source_types": "Academic papers, industry reports, authoritative sources"
            },
            "required_topics": subtopics,
            "success_criteria": [
                "Comprehensive coverage of identified subtopics",
                "High-quality sources and citations",
                "Clear analysis and actionable insights",
                "Structured presentation of findings"
            ],
            "quality_requirements": {
                "minimum_sources_per_topic": 3,
                "source_quality_threshold": 0.7,
                "analysis_depth": "detailed" if "detailed" in depth.lower() else "comprehensive"
            },
            "estimated_complexity": self._assess_complexity(initial_query, subtopics),
            "clarification_metadata": {
                "interactive_rounds": dialogue_context.get("rounds_completed", 0),
                "confidence_score": confidence_score,
                "clarification_mode": dialogue_context.get("mode", "interactive")
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Store research brief
        await self.store_memory("research_brief", research_brief)
        
        return research_brief
    
    async def decompose_into_subtopics(self, research_objective: str,
                                     understanding: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Decompose research objective into specific subtopics.
        
        Args:
            research_objective: Main research objective
            understanding: Clarified understanding context
            
        Returns:
            List of subtopic specifications
        """
        scope = understanding.get("scope", research_objective)
        depth = understanding.get("depth", "comprehensive")
        context = understanding.get("context", "general")
        
        messages = [
            create_message("system",
                          "You are a research planning expert. Break down research objectives "
                          "into 3-5 specific, actionable subtopics."),
            create_message("user",
                          f"Break down this research objective into subtopics:\n"
                          f"Objective: {research_objective}\n"
                          f"Scope: {scope}\n"
                          f"Depth: {depth}\n"
                          f"Context: {context}\n\n"
                          f"Create 3-5 specific subtopics that together provide comprehensive coverage.")
        ]
        
        response = await self.process_message(messages)
        
        # Parse subtopics from response
        subtopics = []
        lines = response.split('\n')
        
        topic_count = 0
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or line.startswith(str(topic_count + 1))):
                # Clean up the line
                topic_title = line.replace('-', '').replace('*', '').replace(f'{topic_count + 1}.', '').strip()
                
                if topic_title and len(topic_title) > 10:
                    subtopic = {
                        "id": f"subtopic_{topic_count + 1}",
                        "title": topic_title,
                        "description": f"Research and analysis of {topic_title.lower()}",
                        "priority": "high" if topic_count < 2 else "medium",
                        "estimated_effort": "medium",
                        "success_criteria": [
                            f"Comprehensive understanding of {topic_title.lower()}",
                            "Multiple high-quality sources identified",
                            "Key insights and findings documented"
                        ]
                    }
                    subtopics.append(subtopic)
                    topic_count += 1
                    
                    if topic_count >= 5:  # Limit to 5 subtopics
                        break
        
        # Fallback if parsing failed
        if not subtopics:
            subtopics = [
                {
                    "id": "subtopic_1",
                    "title": f"Core concepts and fundamentals of {research_objective}",
                    "description": f"Understanding the basic principles and concepts",
                    "priority": "high",
                    "estimated_effort": "medium"
                },
                {
                    "id": "subtopic_2",
                    "title": f"Current state and recent developments in {research_objective}",
                    "description": f"Latest research and industry developments",
                    "priority": "high", 
                    "estimated_effort": "high"
                },
                {
                    "id": "subtopic_3",
                    "title": f"Applications and implications of {research_objective}",
                    "description": f"Practical uses and broader impact",
                    "priority": "medium",
                    "estimated_effort": "medium"
                }
            ]
        
        return subtopics
    
    def _assess_complexity(self, query: str, subtopics: List[Dict[str, Any]]) -> str:
        """
        Assess research complexity based on query and subtopics.
        
        Args:
            query: Research query
            subtopics: List of subtopics
            
        Returns:
            Complexity assessment ("low", "medium", "high")
        """
        complexity_indicators = {
            "high": ["complex", "advanced", "technical", "comprehensive", "detailed"],
            "medium": ["analysis", "research", "study", "review", "comparison"],
            "low": ["overview", "introduction", "basic", "simple", "summary"]
        }
        
        query_lower = query.lower()
        
        # Check for high complexity indicators
        for indicator in complexity_indicators["high"]:
            if indicator in query_lower:
                return "high"
        
        # Check for low complexity indicators
        for indicator in complexity_indicators["low"]:
            if indicator in query_lower:
                return "low"
        
        # Consider number of subtopics
        if len(subtopics) >= 5:
            return "high"
        elif len(subtopics) <= 2:
            return "low"
        
        return "medium"
    
    def get_dialogue_status(self) -> Dict[str, Any]:
        """Get current dialogue status."""
        return {
            "agent_id": self.agent_id,
            "current_dialogue": self.current_dialogue_context,
            "max_rounds": self.max_clarification_rounds,
            "confidence_threshold": self.min_confidence_threshold,
            "is_active": self.is_active
        }
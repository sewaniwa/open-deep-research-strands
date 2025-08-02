"""
Research Sub-Agent for specialized research tasks.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseResearchAgent, TaskData, AgentResult, AgentCapabilityMixin
from ..tools.llm_interface import create_message
from ..tools.mock_tools import MockWebSearchTool


class ResearchSubAgent(BaseResearchAgent, AgentCapabilityMixin):
    """
    Research Sub-Agent that performs specialized research on specific subtopics.
    
    Responsibilities:
    - Conduct focused research on assigned subtopics
    - Execute iterative search and analysis cycles
    - Manage citations and source quality
    - Determine research completion criteria
    """
    
    def __init__(self, subtopic: str, agent_id: str = None):
        """
        Initialize Research Sub-Agent.
        
        Args:
            subtopic: The subtopic this agent will research
            agent_id: Optional specific agent ID
        """
        if agent_id:
            name = f"research_sub_{agent_id}"
        else:
            name = f"research_sub_{subtopic.replace(' ', '_')[:20]}"
        
        super().__init__(
            name=name,
            role="specialized_researcher",
            capabilities=[
                "web_search",
                "content_analysis", 
                "citation_management",
                "source_evaluation",
                "iterative_research"
            ]
        )
        
        # Research configuration
        self.subtopic = subtopic
        self.research_findings = []
        self.max_iterations = 5
        self.current_iteration = 0
        self.min_sources = 3
        self.quality_threshold = 0.7
        
        # Research state
        self.search_queries_used = []
        self.sources_collected = []
        self.analysis_results = []
        
        # Tools
        self.web_search_tool = MockWebSearchTool()
    
    async def execute_task(self, task_data: TaskData) -> AgentResult:
        """
        Execute research task for assigned subtopic.
        
        Args:
            task_data: Task containing subtopic research brief
            
        Returns:
            Research results for the subtopic
        """
        required_fields = ["subtopic_brief"]
        if not await self.validate_task_data(task_data, required_fields):
            return self.create_result(
                task_data.task_id,
                False,
                error=f"Missing required fields: {required_fields}"
            )
        
        subtopic_brief = task_data.content["subtopic_brief"]
        
        try:
            # Conduct comprehensive research
            research_result = await self.conduct_research(subtopic_brief)
            
            return self.create_result(
                task_data.task_id,
                True,
                result=research_result,
                metadata={
                    "iterations_used": self.current_iteration,
                    "sources_found": len(self.sources_collected),
                    "queries_executed": len(self.search_queries_used)
                }
            )
            
        except Exception as e:
            return self.create_result(
                task_data.task_id,
                False,
                error=f"Research failed: {str(e)}"
            )
    
    async def conduct_research(self, subtopic_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct iterative research on the assigned subtopic.
        
        Args:
            subtopic_brief: Brief containing research requirements
            
        Returns:
            Comprehensive research findings
        """
        subtopic_title = subtopic_brief.get("title", self.subtopic)
        subtopic_description = subtopic_brief.get("description", "")
        research_context = subtopic_brief.get("context", "")
        
        await self.log_task_progress("research_start", "beginning_research", {
            "subtopic": subtopic_title,
            "max_iterations": self.max_iterations
        })
        
        # Reset research state
        self.current_iteration = 0
        self.research_findings = []
        self.search_queries_used = []
        self.sources_collected = []
        self.analysis_results = []
        
        # Store research brief
        await self.store_memory("subtopic_brief", subtopic_brief)
        
        # Iterative research loop
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            
            await self.log_task_progress("research_iteration", f"iteration_{self.current_iteration}")
            
            # Generate search queries for this iteration
            search_queries = await self.generate_search_queries(
                subtopic_brief, self.current_iteration
            )
            
            # Execute web searches
            search_results = await self.execute_searches(search_queries)
            
            # Analyze and integrate results
            analyzed_results = await self.analyze_search_results(
                search_results, subtopic_brief
            )
            
            # Update research findings
            self.analysis_results.append(analyzed_results)
            
            # Check if research is sufficient
            if await self.is_research_sufficient(analyzed_results):
                await self.log_task_progress("research_complete", "sufficient_data_collected")
                break
            
            # Add delay between iterations to avoid rate limiting
            await asyncio.sleep(1.0)
        
        # Compile and return final findings
        final_findings = await self.compile_final_findings()
        
        # Store final results
        await self.store_memory("final_research_results", final_findings)
        
        return final_findings
    
    async def generate_search_queries(self, subtopic_brief: Dict[str, Any], 
                                    iteration: int) -> List[str]:
        """
        Generate search queries for the current research iteration.
        
        Args:
            subtopic_brief: Research brief for the subtopic
            iteration: Current iteration number
            
        Returns:
            List of search queries
        """
        subtopic_title = subtopic_brief.get("title", self.subtopic)
        subtopic_description = subtopic_brief.get("description", "")
        
        # Context from previous iterations
        previous_queries = ", ".join(self.search_queries_used[-5:])  # Last 5 queries
        
        messages = [
            create_message("system",
                          "You are a research query specialist. Generate effective search queries "
                          "for academic and professional research."),
            create_message("user",
                          f"Generate 2-3 search queries for iteration #{iteration} of research on:\n"
                          f"Topic: {subtopic_title}\n"
                          f"Description: {subtopic_description}\n"
                          f"Previous queries used: {previous_queries}\n"
                          f"Focus on finding new angles and comprehensive coverage.")
        ]
        
        response = await self.process_message(messages)
        
        # Extract queries from response (simplified parsing)
        queries = []
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 10 and not line.startswith('#'):
                # Clean up the query
                query = line.replace('-', '').replace('*', '').replace('1.', '').replace('2.', '').replace('3.', '').strip()
                if query and len(query) > 5:
                    queries.append(query)
        
        # Fallback queries if parsing failed
        if not queries:
            queries = [
                f"{subtopic_title} research",
                f"{subtopic_title} analysis study",
                f"recent developments {subtopic_title}"
            ]
        
        # Limit to 3 queries per iteration
        queries = queries[:3]
        self.search_queries_used.extend(queries)
        
        return queries
    
    async def execute_searches(self, search_queries: List[str]) -> Dict[str, Any]:
        """
        Execute web searches for the given queries.
        
        Args:
            search_queries: List of search queries to execute
            
        Returns:
            Aggregated search results
        """
        all_results = {
            "queries_executed": [],
            "total_results": 0,
            "results_by_query": {},
            "unique_sources": []
        }
        
        for query in search_queries:
            try:
                # Execute search using mock tool
                search_result = await self.web_search_tool.search(
                    query, 
                    max_results=10
                )
                
                all_results["queries_executed"].append(query)
                all_results["results_by_query"][query] = search_result
                all_results["total_results"] += len(search_result.get("results", []))
                
                # Collect unique sources
                for result in search_result.get("results", []):
                    source_info = {
                        "title": result["title"],
                        "url": result["url"],
                        "snippet": result["snippet"],
                        "domain": result["domain"],
                        "relevance_score": result.get("relevance_score", 0.0),
                        "query_used": query
                    }
                    
                    # Check for duplicates by URL
                    if not any(src["url"] == source_info["url"] for src in all_results["unique_sources"]):
                        all_results["unique_sources"].append(source_info)
                        self.sources_collected.append(source_info)
                
                await self.log_task_progress("search_executed", f"query_completed", {
                    "query": query,
                    "results_count": len(search_result.get("results", []))
                })
                
            except Exception as e:
                self.logger.error(f"Search failed for query: {query}", error=str(e))
        
        return all_results
    
    async def analyze_search_results(self, search_results: Dict[str, Any],
                                   subtopic_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze and synthesize search results.
        
        Args:
            search_results: Raw search results
            subtopic_brief: Research brief for context
            
        Returns:
            Analyzed and synthesized results
        """
        unique_sources = search_results.get("unique_sources", [])
        subtopic_title = subtopic_brief.get("title", self.subtopic)
        
        if not unique_sources:
            return {
                "analysis": "No sources found for analysis",
                "key_insights": [],
                "source_quality": 0.0,
                "confidence": 0.0
            }
        
        # Analyze top sources
        top_sources = sorted(
            unique_sources, 
            key=lambda x: x.get("relevance_score", 0.0), 
            reverse=True
        )[:5]
        
        # Create analysis context
        source_summaries = []
        for source in top_sources:
            summary = f"- {source['title']}: {source['snippet'][:100]}..."
            source_summaries.append(summary)
        
        messages = [
            create_message("system",
                          "You are a research analyst. Synthesize information from multiple sources "
                          "to provide comprehensive insights on the research topic."),
            create_message("user",
                          f"Analyze these sources for research on: {subtopic_title}\n\n"
                          f"Sources:\n" + "\n".join(source_summaries) + "\n\n"
                          f"Provide key insights, patterns, and important findings.")
        ]
        
        analysis_response = await self.process_message(messages)
        
        # Extract key insights (simplified)
        key_insights = []
        lines = analysis_response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('*') or 'key' in line.lower() or 'important' in line.lower():
                insight = line.replace('-', '').replace('*', '').strip()
                if insight and len(insight) > 20:
                    key_insights.append(insight)
        
        # Calculate source quality metrics
        avg_relevance = sum(src.get("relevance_score", 0.0) for src in top_sources) / len(top_sources)
        domain_diversity = len(set(src["domain"] for src in top_sources))
        
        source_quality = min(1.0, (avg_relevance + domain_diversity * 0.1))
        confidence = min(1.0, source_quality * (len(unique_sources) / self.min_sources))
        
        analyzed_results = {
            "iteration": self.current_iteration,
            "analysis": analysis_response,
            "key_insights": key_insights[:10],  # Limit to top 10
            "sources_analyzed": len(top_sources),
            "total_sources_available": len(unique_sources),
            "source_quality": source_quality,
            "confidence": confidence,
            "top_sources": top_sources,
            "domain_diversity": domain_diversity,
            "average_relevance": avg_relevance
        }
        
        return analyzed_results
    
    async def is_research_sufficient(self, current_analysis: Dict[str, Any]) -> bool:
        """
        Determine if current research findings are sufficient.
        
        Args:
            current_analysis: Current iteration analysis results
            
        Returns:
            True if research is sufficient, False otherwise
        """
        # Check quality thresholds
        confidence = current_analysis.get("confidence", 0.0)
        source_quality = current_analysis.get("source_quality", 0.0)
        total_sources = len(self.sources_collected)
        
        # Minimum requirements
        has_min_sources = total_sources >= self.min_sources
        meets_quality = confidence >= self.quality_threshold
        has_insights = len(current_analysis.get("key_insights", [])) >= 3
        
        sufficiency_check = {
            "has_min_sources": has_min_sources,
            "meets_quality": meets_quality,
            "has_insights": has_insights,
            "confidence_score": confidence,
            "source_count": total_sources
        }
        
        await self.store_memory(f"sufficiency_check_iter_{self.current_iteration}", sufficiency_check)
        
        is_sufficient = has_min_sources and meets_quality and has_insights
        
        await self.log_task_progress("sufficiency_check", f"iteration_{self.current_iteration}", {
            "is_sufficient": is_sufficient,
            **sufficiency_check
        })
        
        return is_sufficient
    
    async def compile_final_findings(self) -> Dict[str, Any]:
        """
        Compile all research iterations into final findings.
        
        Returns:
            Comprehensive final research findings
        """
        if not self.analysis_results:
            return {
                "error": "No analysis results available",
                "subtopic": self.subtopic,
                "success": False
            }
        
        # Get the best analysis result
        best_analysis = max(
            self.analysis_results,
            key=lambda x: x.get("confidence", 0.0)
        )
        
        # Aggregate all insights
        all_insights = []
        for analysis in self.analysis_results:
            all_insights.extend(analysis.get("key_insights", []))
        
        # Remove duplicates while preserving order
        unique_insights = []
        seen = set()
        for insight in all_insights:
            if insight.lower() not in seen:
                unique_insights.append(insight)
                seen.add(insight.lower())
        
        # Aggregate all sources
        all_sources = []
        source_urls = set()
        for source in self.sources_collected:
            if source["url"] not in source_urls:
                all_sources.append(source)
                source_urls.add(source["url"])
        
        # Sort sources by relevance
        all_sources.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        
        # Create final synthesis
        messages = [
            create_message("system",
                          "You are a research synthesizer. Create a comprehensive summary "
                          "of research findings from multiple iterations."),
            create_message("user",
                          f"Create a final research summary for: {self.subtopic}\n"
                          f"Key insights found: {unique_insights[:10]}\n"
                          f"Based on {len(all_sources)} sources across {self.current_iteration} iterations.")
        ]
        
        final_synthesis = await self.process_message(messages)
        
        final_findings = {
            "subtopic": self.subtopic,
            "research_summary": final_synthesis,
            "key_insights": unique_insights[:15],  # Top 15 insights
            "total_sources": len(all_sources),
            "top_sources": all_sources[:10],  # Top 10 sources
            "research_iterations": self.current_iteration,
            "total_queries": len(self.search_queries_used),
            "confidence_score": best_analysis.get("confidence", 0.0),
            "source_quality_score": best_analysis.get("source_quality", 0.0),
            "domain_diversity": len(set(src["domain"] for src in all_sources)),
            "research_metrics": {
                "iterations_used": self.current_iteration,
                "queries_executed": len(self.search_queries_used),
                "sources_collected": len(all_sources),
                "unique_domains": len(set(src["domain"] for src in all_sources)),
                "average_relevance": sum(src.get("relevance_score", 0.0) for src in all_sources) / len(all_sources) if all_sources else 0.0
            },
            "completed_at": datetime.utcnow().isoformat(),
            "success": True
        }
        
        return final_findings
    
    def get_research_status(self) -> Dict[str, Any]:
        """Get current research status."""
        return {
            "agent_id": self.agent_id,
            "subtopic": self.subtopic,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "queries_used": len(self.search_queries_used),
            "sources_collected": len(self.sources_collected),
            "analysis_results": len(self.analysis_results),
            "is_active": self.is_active,
            "last_activity": self.last_activity
        }
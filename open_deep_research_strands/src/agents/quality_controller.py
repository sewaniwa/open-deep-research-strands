"""
Quality Controller for research quality assessment and control.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from .base_agent import BaseResearchAgent


class QualityDimension(Enum):
    """Quality assessment dimensions."""
    ACCURACY = "accuracy"
    DEPTH = "depth"
    COMPLETENESS = "completeness"
    SOURCE_QUALITY = "source_quality"
    REASONING_CLARITY = "reasoning_clarity"
    RELEVANCE = "relevance"


class QualityAssessment:
    """Quality assessment result."""
    
    def __init__(self, overall_score: float, dimension_scores: Dict[str, float],
                 meets_threshold: bool, gaps: List[str], recommendations: List[str]):
        self.overall_score = overall_score
        self.dimension_scores = dimension_scores
        self.meets_threshold = meets_threshold
        self.gaps = gaps
        self.recommendations = recommendations
        self.assessed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "meets_threshold": self.meets_threshold,
            "gaps": self.gaps,
            "recommendations": self.recommendations,
            "assessed_at": self.assessed_at.isoformat()
        }


class QualityController:
    """
    Controller for research quality assessment and improvement.
    
    Responsibilities:
    - Assess research quality across multiple dimensions
    - Identify gaps and areas for improvement
    - Recommend additional research when needed
    - Track quality metrics over time
    """
    
    def __init__(self, supervisor: BaseResearchAgent):
        """
        Initialize Quality Controller.
        
        Args:
            supervisor: Supervisor agent that owns this controller
        """
        self.supervisor = supervisor
        
        # Load quality thresholds from settings with fallback
        try:
            from configs.agent_settings import get_agent_settings
            settings = get_agent_settings()
            self.quality_thresholds = settings.get_quality_thresholds()
        except ImportError:
            # Fallback quality thresholds
            self.quality_thresholds = {
                "accuracy": 0.8,
                "depth": 0.7,
                "completeness": 0.8,
                "source_quality": 0.9,
                "reasoning_clarity": 0.75,
                "relevance": 0.8
            }
        
        # Quality tracking
        self.assessment_history: List[QualityAssessment] = []
        self.improvement_suggestions: Dict[str, List[str]] = {}
    
    async def assess_research_quality(self, research_results: Dict[str, Any],
                                    research_brief: Dict[str, Any]) -> QualityAssessment:
        """
        Perform comprehensive quality assessment of research results.
        
        Args:
            research_results: Results from research phase
            research_brief: Original research brief
            
        Returns:
            Quality assessment with scores and recommendations
        """
        dimension_scores = {}
        gaps = []
        recommendations = []
        
        # Assess each quality dimension
        dimension_scores[QualityDimension.ACCURACY.value] = await self._assess_accuracy(
            research_results, research_brief
        )
        
        dimension_scores[QualityDimension.DEPTH.value] = await self._assess_depth(
            research_results, research_brief
        )
        
        dimension_scores[QualityDimension.COMPLETENESS.value] = await self._assess_completeness(
            research_results, research_brief
        )
        
        dimension_scores[QualityDimension.SOURCE_QUALITY.value] = await self._assess_source_quality(
            research_results
        )
        
        dimension_scores[QualityDimension.REASONING_CLARITY.value] = await self._assess_reasoning_clarity(
            research_results
        )
        
        dimension_scores[QualityDimension.RELEVANCE.value] = await self._assess_relevance(
            research_results, research_brief
        )
        
        # Calculate overall score (weighted average)
        weights = {
            QualityDimension.ACCURACY.value: 0.25,
            QualityDimension.DEPTH.value: 0.20,
            QualityDimension.COMPLETENESS.value: 0.20,
            QualityDimension.SOURCE_QUALITY.value: 0.15,
            QualityDimension.REASONING_CLARITY.value: 0.10,
            QualityDimension.RELEVANCE.value: 0.10
        }
        
        overall_score = sum(
            dimension_scores[dim] * weights[dim]
            for dim in dimension_scores.keys()
        )
        
        # Check if meets minimum threshold
        meets_threshold = all(
            dimension_scores[dim] >= self.quality_thresholds.get(dim, 0.7)
            for dim in dimension_scores.keys()
        )
        
        # Identify gaps and generate recommendations
        gaps, recommendations = await self._identify_gaps_and_recommendations(
            dimension_scores, research_results, research_brief
        )
        
        assessment = QualityAssessment(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            meets_threshold=meets_threshold,
            gaps=gaps,
            recommendations=recommendations
        )
        
        # Store in history
        self.assessment_history.append(assessment)
        
        await self.supervisor.log_task_progress(
            self.supervisor.session_id or "unknown",
            "quality_assessment_completed",
            {
                "overall_score": overall_score,
                "meets_threshold": meets_threshold,
                "dimension_scores": dimension_scores,
                "gaps_count": len(gaps)
            }
        )
        
        return assessment
    
    async def _assess_accuracy(self, research_results: Dict[str, Any],
                              research_brief: Dict[str, Any]) -> float:
        """
        Assess the accuracy of research results.
        
        Args:
            research_results: Research results to assess
            research_brief: Original research brief
            
        Returns:
            Accuracy score (0.0 to 1.0)
        """
        subtopic_results = research_results.get("subtopic_results", {})
        
        if not subtopic_results:
            return 0.0
        
        # Calculate based on confidence scores and source quality
        confidence_scores = []
        source_scores = []
        
        for result in subtopic_results.values():
            confidence_scores.append(result.get("confidence_score", 0.0))
            
            # Assess source credibility
            sources = result.get("sources", [])
            if sources:
                avg_source_relevance = sum(s.get("relevance", 0.0) for s in sources) / len(sources)
                source_scores.append(avg_source_relevance)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        avg_source_quality = sum(source_scores) / len(source_scores) if source_scores else 0.0
        
        # Weighted combination
        accuracy_score = (avg_confidence * 0.7 + avg_source_quality * 0.3)
        
        return min(max(accuracy_score, 0.0), 1.0)
    
    async def _assess_depth(self, research_results: Dict[str, Any],
                           research_brief: Dict[str, Any]) -> float:
        """
        Assess the depth of research results.
        
        Args:
            research_results: Research results to assess
            research_brief: Original research brief
            
        Returns:
            Depth score (0.0 to 1.0)
        """
        subtopic_results = research_results.get("subtopic_results", {})
        
        if not subtopic_results:
            return 0.0
        
        depth_indicators = []
        
        for result in subtopic_results.values():
            analysis_length = len(result.get("analysis", ""))
            key_findings_count = len(result.get("key_findings", []))
            sources_count = len(result.get("sources", []))
            
            # Depth metrics
            analysis_depth = min(analysis_length / 1000.0, 1.0)  # Normalize to 1000 chars
            findings_depth = min(key_findings_count / 5.0, 1.0)  # Normalize to 5 findings
            source_depth = min(sources_count / 10.0, 1.0)  # Normalize to 10 sources
            
            depth_score = (analysis_depth * 0.5 + findings_depth * 0.3 + source_depth * 0.2)
            depth_indicators.append(depth_score)
        
        avg_depth = sum(depth_indicators) / len(depth_indicators) if depth_indicators else 0.0
        
        return min(max(avg_depth, 0.0), 1.0)
    
    async def _assess_completeness(self, research_results: Dict[str, Any],
                                  research_brief: Dict[str, Any]) -> float:
        """
        Assess the completeness of research results.
        
        Args:
            research_results: Research results to assess
            research_brief: Original research brief
            
        Returns:
            Completeness score (0.0 to 1.0)
        """
        required_topics = research_brief.get("required_topics", [])
        subtopic_results = research_results.get("subtopic_results", {})
        
        if not required_topics:
            return 0.8  # Default score if no specific topics required
        
        # Check coverage of required topics
        required_topic_ids = {topic.get("id") for topic in required_topics}
        covered_topic_ids = set(subtopic_results.keys())
        
        coverage_ratio = len(covered_topic_ids.intersection(required_topic_ids)) / len(required_topic_ids)
        
        # Assess thoroughness of covered topics
        thoroughness_scores = []
        for topic_id in covered_topic_ids:
            if topic_id in subtopic_results:
                result = subtopic_results[topic_id]
                # Check if result has all expected components
                has_analysis = bool(result.get("analysis"))
                has_findings = bool(result.get("key_findings"))
                has_sources = bool(result.get("sources"))
                
                thoroughness = (int(has_analysis) + int(has_findings) + int(has_sources)) / 3.0
                thoroughness_scores.append(thoroughness)
        
        avg_thoroughness = sum(thoroughness_scores) / len(thoroughness_scores) if thoroughness_scores else 0.0
        
        # Combined completeness score
        completeness_score = (coverage_ratio * 0.6 + avg_thoroughness * 0.4)
        
        return min(max(completeness_score, 0.0), 1.0)
    
    async def _assess_source_quality(self, research_results: Dict[str, Any]) -> float:
        """
        Assess the quality of sources used in research.
        
        Args:
            research_results: Research results to assess
            
        Returns:
            Source quality score (0.0 to 1.0)
        """
        subtopic_results = research_results.get("subtopic_results", {})
        
        if not subtopic_results:
            return 0.0
        
        source_quality_scores = []
        
        for result in subtopic_results.values():
            sources = result.get("sources", [])
            
            if not sources:
                source_quality_scores.append(0.0)
                continue
            
            # Assess individual source quality
            source_scores = []
            for source in sources:
                relevance = source.get("relevance", 0.0)
                
                # Additional quality indicators
                has_title = bool(source.get("title"))
                has_url = bool(source.get("url"))
                
                # URL quality heuristics (basic)
                url = source.get("url", "")
                url_quality = 0.5  # Default
                if "arxiv.org" in url or "doi.org" in url:
                    url_quality = 1.0  # Academic sources
                elif "wikipedia.org" in url:
                    url_quality = 0.7  # Wiki sources
                elif "example.com" in url:
                    url_quality = 0.1  # Mock sources
                
                source_score = (relevance * 0.5 + 
                               (int(has_title) + int(has_url)) * 0.1 + 
                               url_quality * 0.3)
                source_scores.append(source_score)
            
            avg_source_score = sum(source_scores) / len(source_scores)
            source_quality_scores.append(avg_source_score)
        
        overall_source_quality = sum(source_quality_scores) / len(source_quality_scores)
        
        return min(max(overall_source_quality, 0.0), 1.0)
    
    async def _assess_reasoning_clarity(self, research_results: Dict[str, Any]) -> float:
        """
        Assess the clarity of reasoning in research results.
        
        Args:
            research_results: Research results to assess
            
        Returns:
            Reasoning clarity score (0.0 to 1.0)
        """
        subtopic_results = research_results.get("subtopic_results", {})
        
        if not subtopic_results:
            return 0.0
        
        clarity_scores = []
        
        for result in subtopic_results.values():
            analysis = result.get("analysis", "")
            key_findings = result.get("key_findings", [])
            
            # Basic clarity metrics
            if not analysis:
                clarity_scores.append(0.0)
                continue
            
            # Analysis structure indicators
            has_clear_structure = (":" in analysis or "." in analysis)
            has_logical_flow = len(analysis.split(".")) > 2  # Multiple sentences
            findings_alignment = len(key_findings) > 0
            
            clarity_score = (int(has_clear_structure) * 0.4 + 
                           int(has_logical_flow) * 0.4 + 
                           int(findings_alignment) * 0.2)
            
            clarity_scores.append(clarity_score)
        
        avg_clarity = sum(clarity_scores) / len(clarity_scores)
        
        return min(max(avg_clarity, 0.0), 1.0)
    
    async def _assess_relevance(self, research_results: Dict[str, Any],
                               research_brief: Dict[str, Any]) -> float:
        """
        Assess the relevance of research results to the original query.
        
        Args:
            research_results: Research results to assess
            research_brief: Original research brief
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        original_query = research_brief.get("original_query", "")
        subtopic_results = research_results.get("subtopic_results", {})
        
        if not subtopic_results or not original_query:
            return 0.5  # Default moderate relevance
        
        relevance_scores = []
        
        for result in subtopic_results.values():
            # Simple keyword-based relevance (in a full implementation, 
            # this would use semantic similarity)
            analysis = result.get("analysis", "").lower()
            query_words = original_query.lower().split()
            
            # Count matching keywords
            matches = sum(1 for word in query_words if word in analysis)
            keyword_relevance = min(matches / len(query_words), 1.0) if query_words else 0.0
            
            # Consider subtopic title relevance
            title = result.get("title", "").lower()
            title_matches = sum(1 for word in query_words if word in title)
            title_relevance = min(title_matches / len(query_words), 1.0) if query_words else 0.0
            
            overall_relevance = (keyword_relevance * 0.7 + title_relevance * 0.3)
            relevance_scores.append(overall_relevance)
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        
        return min(max(avg_relevance, 0.0), 1.0)
    
    async def _identify_gaps_and_recommendations(self, dimension_scores: Dict[str, float],
                                               research_results: Dict[str, Any],
                                               research_brief: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Identify quality gaps and generate improvement recommendations.
        
        Args:
            dimension_scores: Quality scores by dimension
            research_results: Research results
            research_brief: Original research brief
            
        Returns:
            Tuple of (gaps, recommendations)
        """
        gaps = []
        recommendations = []
        
        # Check each dimension against thresholds
        for dimension, score in dimension_scores.items():
            threshold = self.quality_thresholds.get(dimension, 0.7)
            
            if score < threshold:
                gaps.append(f"{dimension}: {score:.2f} < {threshold:.2f}")
                
                # Generate specific recommendations
                if dimension == QualityDimension.ACCURACY.value:
                    recommendations.append("Verify facts with additional authoritative sources")
                    recommendations.append("Cross-reference findings across multiple sources")
                
                elif dimension == QualityDimension.DEPTH.value:
                    recommendations.append("Expand analysis with more detailed explanations")
                    recommendations.append("Include additional supporting evidence")
                
                elif dimension == QualityDimension.COMPLETENESS.value:
                    recommendations.append("Address all required subtopics")
                    recommendations.append("Ensure comprehensive coverage of the research query")
                
                elif dimension == QualityDimension.SOURCE_QUALITY.value:
                    recommendations.append("Include more academic and peer-reviewed sources")
                    recommendations.append("Verify source credibility and recency")
                
                elif dimension == QualityDimension.REASONING_CLARITY.value:
                    recommendations.append("Improve logical flow and structure of analysis")
                    recommendations.append("Add clear connections between findings")
                
                elif dimension == QualityDimension.RELEVANCE.value:
                    recommendations.append("Ensure all findings directly address the research query")
                    recommendations.append("Remove or refocus tangential information")
        
        # General recommendations based on overall quality
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        
        if overall_score < 0.6:
            recommendations.append("Consider significant revision or additional research")
        elif overall_score < 0.8:
            recommendations.append("Minor improvements recommended before finalization")
        
        return gaps, recommendations
    
    def get_quality_trends(self) -> Dict[str, Any]:
        """
        Get quality trends over assessment history.
        
        Returns:
            Quality trends analysis
        """
        if not self.assessment_history:
            return {"message": "No assessment history available"}
        
        # Calculate trends
        recent_assessments = self.assessment_history[-5:]  # Last 5 assessments
        
        dimension_trends = {}
        for dimension in QualityDimension:
            dim_name = dimension.value
            scores = [a.dimension_scores.get(dim_name, 0.0) for a in recent_assessments]
            
            if len(scores) > 1:
                trend = scores[-1] - scores[0]  # Simple trend calculation
                dimension_trends[dim_name] = {
                    "current_score": scores[-1],
                    "trend": trend,
                    "direction": "improving" if trend > 0 else "declining" if trend < 0 else "stable"
                }
        
        overall_scores = [a.overall_score for a in recent_assessments]
        
        return {
            "total_assessments": len(self.assessment_history),
            "current_overall_score": overall_scores[-1] if overall_scores else 0.0,
            "average_score": sum(overall_scores) / len(overall_scores) if overall_scores else 0.0,
            "dimension_trends": dimension_trends,
            "quality_improvement_rate": (overall_scores[-1] - overall_scores[0]) / len(overall_scores) if len(overall_scores) > 1 else 0.0
        }
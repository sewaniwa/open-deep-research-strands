"""
Report Agent for research result integration and report generation.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import json

from .base_agent import BaseResearchAgent, TaskData, AgentResult, AgentCapabilityMixin
from ..tools.llm_interface import create_message


class ReportFormat(Enum):
    """Report output format options."""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    PDF = "pdf"
    PLAIN_TEXT = "plain_text"


class ReportSection(Enum):
    """Report section types."""
    EXECUTIVE_SUMMARY = "executive_summary"
    INTRODUCTION = "introduction"
    METHODOLOGY = "methodology"
    FINDINGS = "findings"
    ANALYSIS = "analysis"
    CONCLUSIONS = "conclusions"
    RECOMMENDATIONS = "recommendations"
    REFERENCES = "references"
    APPENDICES = "appendices"


class ReportAgent(BaseResearchAgent, AgentCapabilityMixin):
    """
    Report Agent that integrates research results and generates comprehensive reports.
    
    Responsibilities:
    - Integrate research results from multiple sub-agents
    - Structure reports with proper formatting
    - Support multiple output formats
    - Implement quality assurance checks
    - Generate executive summaries and recommendations
    """
    
    def __init__(self):
        """Initialize Report Agent."""
        super().__init__(
            name="report_agent",
            role="research_reporter",
            capabilities=[
                "result_integration",
                "report_structuring",
                "format_conversion",
                "quality_assurance",
                "summary_generation",
                "recommendation_synthesis"
            ]
        )
        
        # Report configuration
        self.default_sections = [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.INTRODUCTION,
            ReportSection.METHODOLOGY,
            ReportSection.FINDINGS,
            ReportSection.ANALYSIS,
            ReportSection.CONCLUSIONS,
            ReportSection.RECOMMENDATIONS,
            ReportSection.REFERENCES
        ]
        
        # Quality thresholds for reports
        self.quality_thresholds = {
            "minimum_sections": 5,
            "minimum_findings": 3,
            "minimum_sources": 5,
            "minimum_word_count": 1000
        }
        
        # Template configurations
        self.section_templates = {
            ReportSection.EXECUTIVE_SUMMARY: {
                "max_length": 500,
                "focus": "key_findings_and_implications"
            },
            ReportSection.INTRODUCTION: {
                "max_length": 300,
                "focus": "background_and_objectives"
            },
            ReportSection.METHODOLOGY: {
                "max_length": 400,
                "focus": "research_approach_and_methods"
            },
            ReportSection.FINDINGS: {
                "max_length": 1500,
                "focus": "detailed_research_results"
            },
            ReportSection.ANALYSIS: {
                "max_length": 1000,
                "focus": "interpretation_and_insights"
            },
            ReportSection.CONCLUSIONS: {
                "max_length": 600,
                "focus": "summary_of_key_outcomes"
            },
            ReportSection.RECOMMENDATIONS: {
                "max_length": 500,
                "focus": "actionable_next_steps"
            }
        }
    
    async def execute_task(self, task_data: TaskData) -> AgentResult:
        """
        Execute report generation task.
        
        Args:
            task_data: Task containing research results and report specifications
            
        Returns:
            Generated report in requested format
        """
        required_fields = ["research_results", "research_brief"]
        if not await self.validate_task_data(task_data, required_fields):
            return self.create_result(
                task_data.task_id,
                False,
                error="Missing required fields: research_results, research_brief"
            )
        
        research_results = task_data.content["research_results"]
        research_brief = task_data.content["research_brief"]
        report_config = task_data.content.get("report_config", {})
        
        try:
            # Integrate research results
            integrated_data = await self.integrate_research_results(
                research_results, research_brief
            )
            
            # Generate report structure
            report_structure = await self.generate_report_structure(
                integrated_data, research_brief, report_config
            )
            
            # Generate content for each section
            report_content = await self.generate_report_content(
                report_structure, integrated_data, research_brief
            )
            
            # Perform quality assurance checks
            quality_check = await self.perform_quality_assurance(
                report_content, research_results, research_brief
            )
            
            # Format report in requested format(s)
            requested_formats = report_config.get("formats", [ReportFormat.MARKDOWN.value])
            formatted_reports = {}
            
            for format_type in requested_formats:
                formatted_report = await self.format_report(
                    report_content, ReportFormat(format_type)
                )
                formatted_reports[format_type] = formatted_report
            
            return self.create_result(
                task_data.task_id,
                True,
                result={
                    "report_content": report_content,
                    "formatted_reports": formatted_reports,
                    "quality_check": quality_check,
                    "metadata": {
                        "total_sections": len(report_content["sections"]),
                        "total_word_count": self._count_words(report_content),
                        "total_sources": len(integrated_data.get("all_sources", [])),
                        "formats_generated": list(formatted_reports.keys())
                    }
                },
                metadata={
                    "generation_time": report_content.get("generation_time", 0),
                    "quality_score": quality_check.get("overall_score", 0.0)
                }
            )
            
        except Exception as e:
            return self.create_result(
                task_data.task_id,
                False,
                error=f"Report generation failed: {str(e)}"
            )
    
    async def integrate_research_results(self, research_results: Dict[str, Any],
                                       research_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrate research results from multiple sources.
        
        Args:
            research_results: Raw research results from sub-agents
            research_brief: Original research brief
            
        Returns:
            Integrated research data
        """
        subtopic_results = research_results.get("subtopic_results", {})
        
        # Collect and integrate all findings
        all_findings = []
        all_sources = []
        subtopic_summaries = {}
        
        for subtopic_id, result in subtopic_results.items():
            if isinstance(result, dict):
                # Extract findings
                findings = result.get("key_findings", [])
                all_findings.extend(findings)
                
                # Extract sources
                sources = result.get("sources", [])
                for source in sources:
                    if source not in all_sources:
                        all_sources.append(source)
                
                # Create subtopic summary
                subtopic_summaries[subtopic_id] = {
                    "title": result.get("title", f"Subtopic {subtopic_id}"),
                    "analysis": result.get("analysis", ""),
                    "key_findings": findings,
                    "confidence_score": result.get("confidence_score", 0.0)
                }
        
        # Generate integrated insights
        integrated_insights = await self._generate_integrated_insights(
            subtopic_summaries, research_brief
        )
        
        # Identify cross-cutting themes
        themes = await self._identify_cross_cutting_themes(all_findings)
        
        integrated_data = {
            "original_query": research_brief.get("original_query", ""),
            "research_objective": research_brief.get("research_objective", ""),
            "subtopic_summaries": subtopic_summaries,
            "all_findings": all_findings,
            "all_sources": all_sources,
            "integrated_insights": integrated_insights,
            "cross_cutting_themes": themes,
            "coordination_summary": research_results.get("coordination_summary", {}),
            "integration_completed_at": datetime.utcnow().isoformat()
        }
        
        # Store integration results
        await self.store_memory("integrated_research_data", integrated_data)
        
        return integrated_data
    
    async def _generate_integrated_insights(self, subtopic_summaries: Dict[str, Any],
                                          research_brief: Dict[str, Any]) -> List[str]:
        """
        Generate insights by analyzing connections across subtopics.
        
        Args:
            subtopic_summaries: Summaries from all subtopics
            research_brief: Original research brief
            
        Returns:
            List of integrated insights
        """
        if not subtopic_summaries:
            return []
        
        # Prepare subtopic information for analysis
        subtopic_info = []
        for subtopic_id, summary in subtopic_summaries.items():
            subtopic_info.append(f"**{summary['title']}**: {summary['analysis'][:200]}...")
        
        messages = [
            create_message("system",
                          "You are a research analyst specializing in identifying connections "
                          "and insights across multiple research areas. Generate integrated "
                          "insights that connect findings from different subtopics."),
            create_message("user",
                          f"Research objective: {research_brief.get('research_objective', '')}\n\n"
                          f"Subtopic findings:\n{chr(10).join(subtopic_info)}\n\n"
                          f"Generate 3-5 integrated insights that connect findings across "
                          f"these subtopics and provide deeper understanding of the research objective.")
        ]
        
        response = await self.process_message(messages)
        
        # Parse insights from response
        insights = []
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or line[0].isdigit()):
                insight = line.replace('-', '').replace('*', '').strip()
                if len(insight) > 20:  # Filter out short lines
                    insights.append(insight)
        
        return insights[:5]  # Limit to 5 insights
    
    async def _identify_cross_cutting_themes(self, all_findings: List[str]) -> List[str]:
        """
        Identify themes that appear across multiple findings.
        
        Args:
            all_findings: All findings from research
            
        Returns:
            List of cross-cutting themes
        """
        if not all_findings:
            return []
        
        # Simple keyword-based theme identification
        # In a full implementation, this would use more sophisticated NLP
        
        findings_text = " ".join(all_findings).lower()
        
        # Common research themes to look for
        theme_keywords = {
            "technological_advancement": ["technology", "innovation", "advancement", "digital", "ai", "automation"],
            "sustainability": ["sustainable", "environment", "green", "renewable", "carbon", "climate"],
            "economic_impact": ["economic", "cost", "benefit", "financial", "market", "revenue"],
            "social_implications": ["social", "society", "community", "impact", "people", "human"],
            "efficiency_improvement": ["efficiency", "optimization", "improvement", "performance", "productivity"],
            "risk_management": ["risk", "security", "safety", "mitigation", "challenge", "concern"]
        }
        
        identified_themes = []
        for theme, keywords in theme_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in findings_text)
            if keyword_count >= 2:  # Theme must have at least 2 keyword matches
                identified_themes.append(theme.replace("_", " ").title())
        
        return identified_themes
    
    async def generate_report_structure(self, integrated_data: Dict[str, Any],
                                      research_brief: Dict[str, Any],
                                      report_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the structure for the research report.
        
        Args:
            integrated_data: Integrated research data
            research_brief: Original research brief
            report_config: Report configuration options
            
        Returns:
            Report structure specification
        """
        # Use default sections or custom sections from config
        sections = report_config.get("sections", [s.value for s in self.default_sections])
        
        # Generate section specifications
        section_specs = {}
        for section in sections:
            if section in [s.value for s in ReportSection]:
                section_enum = ReportSection(section)
                template = self.section_templates.get(section_enum, {})
                
                section_specs[section] = {
                    "title": section.replace("_", " ").title(),
                    "max_length": template.get("max_length", 500),
                    "focus": template.get("focus", "general_information"),
                    "required": section in ["executive_summary", "findings"],
                    "order": list(ReportSection).index(section_enum)
                }
        
        # Sort sections by order
        ordered_sections = sorted(section_specs.items(), key=lambda x: x[1]["order"])
        
        report_structure = {
            "title": f"Research Report: {research_brief.get('original_query', 'Unknown Topic')}",
            "sections": dict(ordered_sections),
            "estimated_length": sum(spec["max_length"] for spec in section_specs.values()),
            "total_sections": len(section_specs),
            "structure_generated_at": datetime.utcnow().isoformat()
        }
        
        return report_structure
    
    async def generate_report_content(self, report_structure: Dict[str, Any],
                                    integrated_data: Dict[str, Any],
                                    research_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate content for each section of the report.
        
        Args:
            report_structure: Report structure specification
            integrated_data: Integrated research data
            research_brief: Original research brief
            
        Returns:
            Complete report content
        """
        start_time = datetime.utcnow()
        
        sections_content = {}
        
        # Generate content for each section
        for section_name, section_spec in report_structure["sections"].items():
            section_content = await self._generate_section_content(
                section_name, section_spec, integrated_data, research_brief
            )
            sections_content[section_name] = section_content
        
        # Generate metadata
        generation_time = (datetime.utcnow() - start_time).total_seconds()
        
        report_content = {
            "title": report_structure["title"],
            "sections": sections_content,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "generation_time": generation_time,
                "total_sections": len(sections_content),
                "word_count": self._count_words({"sections": sections_content})
            },
            "research_metadata": {
                "original_query": integrated_data.get("original_query", ""),
                "total_sources": len(integrated_data.get("all_sources", [])),
                "total_findings": len(integrated_data.get("all_findings", [])),
                "subtopics_covered": len(integrated_data.get("subtopic_summaries", {}))
            }
        }
        
        return report_content
    
    async def _generate_section_content(self, section_name: str, section_spec: Dict[str, Any],
                                      integrated_data: Dict[str, Any],
                                      research_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate content for a specific report section.
        
        Args:
            section_name: Name of the section
            section_spec: Section specification
            integrated_data: Integrated research data
            research_brief: Original research brief
            
        Returns:
            Section content
        """
        if section_name == ReportSection.EXECUTIVE_SUMMARY.value:
            content = await self._generate_executive_summary(integrated_data, research_brief)
        
        elif section_name == ReportSection.INTRODUCTION.value:
            content = await self._generate_introduction(integrated_data, research_brief)
        
        elif section_name == ReportSection.METHODOLOGY.value:
            content = await self._generate_methodology(integrated_data, research_brief)
        
        elif section_name == ReportSection.FINDINGS.value:
            content = await self._generate_findings(integrated_data, research_brief)
        
        elif section_name == ReportSection.ANALYSIS.value:
            content = await self._generate_analysis(integrated_data, research_brief)
        
        elif section_name == ReportSection.CONCLUSIONS.value:
            content = await self._generate_conclusions(integrated_data, research_brief)
        
        elif section_name == ReportSection.RECOMMENDATIONS.value:
            content = await self._generate_recommendations(integrated_data, research_brief)
        
        elif section_name == ReportSection.REFERENCES.value:
            content = await self._generate_references(integrated_data)
        
        else:
            # Generic section generation
            content = await self._generate_generic_section(
                section_name, section_spec, integrated_data, research_brief
            )
        
        return {
            "title": section_spec["title"],
            "content": content,
            "word_count": len(content.split()) if isinstance(content, str) else 0,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def _generate_executive_summary(self, integrated_data: Dict[str, Any],
                                        research_brief: Dict[str, Any]) -> str:
        """Generate executive summary section."""
        key_findings = integrated_data.get("all_findings", [])[:5]  # Top 5 findings
        insights = integrated_data.get("integrated_insights", [])[:3]  # Top 3 insights
        
        messages = [
            create_message("system",
                          "You are a research report writer. Create a concise executive summary "
                          "that highlights the most important findings and insights."),
            create_message("user",
                          f"Research objective: {research_brief.get('research_objective', '')}\n\n"
                          f"Key findings:\n{chr(10).join(f'- {finding}' for finding in key_findings)}\n\n"
                          f"Key insights:\n{chr(10).join(f'- {insight}' for insight in insights)}\n\n"
                          f"Write a concise executive summary (max 500 words) that captures "
                          f"the essence of this research and its most important outcomes.")
        ]
        
        return await self.process_message(messages)
    
    async def _generate_introduction(self, integrated_data: Dict[str, Any],
                                   research_brief: Dict[str, Any]) -> str:
        """Generate introduction section."""
        messages = [
            create_message("system",
                          "You are a research report writer. Create an introduction that "
                          "provides background context and establishes the research objectives."),
            create_message("user",
                          f"Research query: {integrated_data.get('original_query', '')}\n"
                          f"Research objective: {research_brief.get('research_objective', '')}\n"
                          f"Scope: {research_brief.get('scope_boundaries', {})}\n\n"
                          f"Write an introduction (max 300 words) that provides background "
                          f"context and clearly establishes what this research aims to accomplish.")
        ]
        
        return await self.process_message(messages)
    
    async def _generate_methodology(self, integrated_data: Dict[str, Any],
                                  research_brief: Dict[str, Any]) -> str:
        """Generate methodology section."""
        coordination_summary = integrated_data.get("coordination_summary", {})
        
        methodology_text = f"""This research employed a multi-agent parallel research methodology to ensure comprehensive coverage of the topic.

**Research Approach:**
- Systematic decomposition of the research objective into specific subtopics
- Parallel investigation using specialized research agents
- Integration and synthesis of findings across all research areas

**Data Collection:**
- Total subtopics investigated: {len(integrated_data.get('subtopic_summaries', {}))}
- Sources collected: {len(integrated_data.get('all_sources', []))}
- Research method: {coordination_summary.get('research_method', 'Multi-agent coordination')}

**Quality Assurance:**
- Cross-validation of findings across multiple sources
- Confidence scoring for each research area
- Integration analysis to identify connections and themes

This methodology ensures both depth and breadth of coverage while maintaining research quality and reliability."""
        
        return methodology_text
    
    async def _generate_findings(self, integrated_data: Dict[str, Any],
                               research_brief: Dict[str, Any]) -> str:
        """Generate findings section."""
        subtopic_summaries = integrated_data.get("subtopic_summaries", {})
        
        findings_content = "## Detailed Research Findings\n\n"
        
        for subtopic_id, summary in subtopic_summaries.items():
            findings_content += f"### {summary['title']}\n\n"
            findings_content += f"{summary['analysis']}\n\n"
            
            if summary.get('key_findings'):
                findings_content += "**Key Findings:**\n"
                for finding in summary['key_findings']:
                    findings_content += f"- {finding}\n"
                findings_content += "\n"
        
        # Add cross-cutting themes
        themes = integrated_data.get("cross_cutting_themes", [])
        if themes:
            findings_content += "### Cross-Cutting Themes\n\n"
            findings_content += "The following themes emerged across multiple research areas:\n\n"
            for theme in themes:
                findings_content += f"- **{theme}**: Identified as a recurring element across research findings\n"
        
        return findings_content
    
    async def _generate_analysis(self, integrated_data: Dict[str, Any],
                               research_brief: Dict[str, Any]) -> str:
        """Generate analysis section."""
        insights = integrated_data.get("integrated_insights", [])
        
        messages = [
            create_message("system",
                          "You are a research analyst. Provide analytical interpretation "
                          "of the research findings, focusing on implications and significance."),
            create_message("user",
                          f"Research objective: {research_brief.get('research_objective', '')}\n\n"
                          f"Integrated insights:\n{chr(10).join(f'- {insight}' for insight in insights)}\n\n"
                          f"Provide analytical interpretation (max 1000 words) that explains "
                          f"the significance of these findings and their broader implications.")
        ]
        
        return await self.process_message(messages)
    
    async def _generate_conclusions(self, integrated_data: Dict[str, Any],
                                  research_brief: Dict[str, Any]) -> str:
        """Generate conclusions section."""
        key_findings = integrated_data.get("all_findings", [])[:3]  # Top 3 findings
        
        messages = [
            create_message("system",
                          "You are a research report writer. Summarize the key conclusions "
                          "that can be drawn from the research findings."),
            create_message("user",
                          f"Research objective: {research_brief.get('research_objective', '')}\n\n"
                          f"Key findings:\n{chr(10).join(f'- {finding}' for finding in key_findings)}\n\n"
                          f"Write clear conclusions (max 600 words) that summarize what "
                          f"can be definitively concluded from this research.")
        ]
        
        return await self.process_message(messages)
    
    async def _generate_recommendations(self, integrated_data: Dict[str, Any],
                                      research_brief: Dict[str, Any]) -> str:
        """Generate recommendations section."""
        insights = integrated_data.get("integrated_insights", [])
        
        messages = [
            create_message("system",
                          "You are a research consultant. Provide actionable recommendations "
                          "based on the research findings and insights."),
            create_message("user",
                          f"Research objective: {research_brief.get('research_objective', '')}\n\n"
                          f"Key insights:\n{chr(10).join(f'- {insight}' for insight in insights)}\n\n"
                          f"Provide actionable recommendations (max 500 words) for next steps, "
                          f"further research, or practical applications based on these findings.")
        ]
        
        return await self.process_message(messages)
    
    async def _generate_references(self, integrated_data: Dict[str, Any]) -> str:
        """Generate references section."""
        sources = integrated_data.get("all_sources", [])
        
        if not sources:
            return "No sources available."
        
        references_content = "## References\n\n"
        
        for i, source in enumerate(sources, 1):
            title = source.get("title", "Unknown Title")
            url = source.get("url", "No URL provided")
            relevance = source.get("relevance", 0.0)
            
            references_content += f"{i}. **{title}**\n"
            references_content += f"   - URL: {url}\n"
            references_content += f"   - Relevance Score: {relevance:.2f}\n\n"
        
        return references_content
    
    async def _generate_generic_section(self, section_name: str, section_spec: Dict[str, Any],
                                      integrated_data: Dict[str, Any],
                                      research_brief: Dict[str, Any]) -> str:
        """Generate content for generic/custom sections."""
        messages = [
            create_message("system",
                          f"You are a research report writer. Generate content for the "
                          f"'{section_spec['title']}' section of a research report."),
            create_message("user",
                          f"Section focus: {section_spec.get('focus', 'general information')}\n"
                          f"Research objective: {research_brief.get('research_objective', '')}\n"
                          f"Max length: {section_spec.get('max_length', 500)} words\n\n"
                          f"Generate appropriate content for this section based on the research findings.")
        ]
        
        return await self.process_message(messages)
    
    def _count_words(self, content: Dict[str, Any]) -> int:
        """Count total words in report content."""
        total_words = 0
        
        if "sections" in content:
            for section in content["sections"].values():
                if isinstance(section, dict) and "content" in section:
                    if isinstance(section["content"], str):
                        total_words += len(section["content"].split())
        
        return total_words
    
    async def perform_quality_assurance(self, report_content: Dict[str, Any],
                                      research_results: Dict[str, Any],
                                      research_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform quality assurance checks on the generated report.
        
        Args:
            report_content: Generated report content
            research_results: Original research results
            research_brief: Original research brief
            
        Returns:
            Quality assurance results
        """
        qa_results = {
            "checks_performed": [],
            "issues_found": [],
            "quality_score": 0.0,
            "recommendations": []
        }
        
        # Check 1: Section completeness
        required_sections = ["executive_summary", "findings"]
        sections = report_content.get("sections", {})
        
        qa_results["checks_performed"].append("section_completeness")
        missing_sections = [s for s in required_sections if s not in sections]
        if missing_sections:
            qa_results["issues_found"].append(f"Missing required sections: {missing_sections}")
        
        # Check 2: Content length
        word_count = self._count_words(report_content)
        qa_results["checks_performed"].append("content_length")
        
        if word_count < self.quality_thresholds["minimum_word_count"]:
            qa_results["issues_found"].append(
                f"Report too short: {word_count} words < {self.quality_thresholds['minimum_word_count']} minimum"
            )
        
        # Check 3: Source coverage
        total_sources = len(research_results.get("subtopic_results", {}).get("all_sources", []))
        qa_results["checks_performed"].append("source_coverage")
        
        if total_sources < self.quality_thresholds["minimum_sources"]:
            qa_results["issues_found"].append(
                f"Insufficient sources: {total_sources} < {self.quality_thresholds['minimum_sources']} minimum"
            )
        
        # Check 4: Finding integration
        all_findings = []
        for result in research_results.get("subtopic_results", {}).values():
            if isinstance(result, dict):
                all_findings.extend(result.get("key_findings", []))
        
        qa_results["checks_performed"].append("finding_integration")
        
        if len(all_findings) < self.quality_thresholds["minimum_findings"]:
            qa_results["issues_found"].append(
                f"Insufficient findings: {len(all_findings)} < {self.quality_thresholds['minimum_findings']} minimum"
            )
        
        # Calculate overall quality score
        total_checks = len(qa_results["checks_performed"])
        failed_checks = len(qa_results["issues_found"])
        qa_results["quality_score"] = max(0.0, (total_checks - failed_checks) / total_checks)
        
        # Generate recommendations
        if qa_results["issues_found"]:
            qa_results["recommendations"].append("Address identified quality issues before finalizing report")
        if qa_results["quality_score"] < 0.8:
            qa_results["recommendations"].append("Consider additional research or content expansion")
        if qa_results["quality_score"] >= 0.9:
            qa_results["recommendations"].append("Report meets high quality standards")
        
        qa_results["assessed_at"] = datetime.utcnow().isoformat()
        
        return qa_results
    
    async def format_report(self, report_content: Dict[str, Any],
                          format_type: ReportFormat) -> str:
        """
        Format report content into the specified output format.
        
        Args:
            report_content: Report content to format
            format_type: Target format
            
        Returns:
            Formatted report string
        """
        if format_type == ReportFormat.MARKDOWN:
            return await self._format_as_markdown(report_content)
        
        elif format_type == ReportFormat.HTML:
            return await self._format_as_html(report_content)
        
        elif format_type == ReportFormat.JSON:
            return await self._format_as_json(report_content)
        
        elif format_type == ReportFormat.PLAIN_TEXT:
            return await self._format_as_plain_text(report_content)
        
        else:
            # Default to markdown
            return await self._format_as_markdown(report_content)
    
    async def _format_as_markdown(self, report_content: Dict[str, Any]) -> str:
        """Format report as Markdown."""
        markdown_content = f"# {report_content['title']}\n\n"
        
        # Add metadata
        metadata = report_content.get("metadata", {})
        markdown_content += f"*Generated on: {metadata.get('generated_at', 'Unknown')}*\n\n"
        
        # Add sections
        sections = report_content.get("sections", {})
        for section_name, section_data in sections.items():
            markdown_content += f"## {section_data['title']}\n\n"
            markdown_content += f"{section_data['content']}\n\n"
        
        return markdown_content
    
    async def _format_as_html(self, report_content: Dict[str, Any]) -> str:
        """Format report as HTML."""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{report_content['title']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; }}
        .metadata {{ font-style: italic; color: #888; }}
    </style>
</head>
<body>
    <h1>{report_content['title']}</h1>
"""
        
        # Add metadata
        metadata = report_content.get("metadata", {})
        html_content += f"<p class='metadata'>Generated on: {metadata.get('generated_at', 'Unknown')}</p>\n"
        
        # Add sections
        sections = report_content.get("sections", {})
        for section_name, section_data in sections.items():
            html_content += f"<h2>{section_data['title']}</h2>\n"
            # Simple markdown to HTML conversion
            content = section_data['content'].replace('\n', '<br>')
            html_content += f"<p>{content}</p>\n"
        
        html_content += "</body>\n</html>"
        
        return html_content
    
    async def _format_as_json(self, report_content: Dict[str, Any]) -> str:
        """Format report as JSON."""
        return json.dumps(report_content, indent=2, ensure_ascii=False)
    
    async def _format_as_plain_text(self, report_content: Dict[str, Any]) -> str:
        """Format report as plain text."""
        text_content = f"{report_content['title']}\n"
        text_content += "=" * len(report_content['title']) + "\n\n"
        
        # Add metadata
        metadata = report_content.get("metadata", {})
        text_content += f"Generated on: {metadata.get('generated_at', 'Unknown')}\n\n"
        
        # Add sections
        sections = report_content.get("sections", {})
        for section_name, section_data in sections.items():
            text_content += f"{section_data['title']}\n"
            text_content += "-" * len(section_data['title']) + "\n\n"
            text_content += f"{section_data['content']}\n\n"
        
        return text_content
    
    def get_report_status(self) -> Dict[str, Any]:
        """Get current status of report generation."""
        return {
            "agent_id": self.agent_id,
            "supported_formats": [f.value for f in ReportFormat],
            "default_sections": [s.value for s in self.default_sections],
            "quality_thresholds": self.quality_thresholds,
            "is_active": self.is_active
        }
"""
Mock tools for local development and testing.
"""
import asyncio
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..config.logging_config import LoggerMixin


@dataclass
class SearchResult:
    """Represents a web search result."""
    title: str
    url: str
    snippet: str
    domain: str
    published_date: Optional[str] = None
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "domain": self.domain,
            "published_date": self.published_date,
            "relevance_score": self.relevance_score
        }


class MockWebSearchTool(LoggerMixin):
    """Mock web search tool for development and testing."""
    
    def __init__(self):
        """Initialize mock web search tool."""
        self.search_count = 0
        self._mock_domains = [
            "arxiv.org", "wikipedia.org", "github.com", "stackoverflow.com",
            "medium.com", "nature.com", "sciencedirect.com", "acm.org",
            "ieee.org", "springer.com", "mit.edu", "stanford.edu"
        ]
        
        self._mock_titles = [
            "Advanced Techniques in {topic}",
            "A Comprehensive Survey of {topic}",
            "Recent Developments in {topic}",
            "Understanding {topic}: A Deep Dive",
            "The Future of {topic}",
            "Practical Applications of {topic}",
            "State-of-the-Art {topic} Methods",
            "Introduction to {topic}",
            "{topic}: Best Practices and Guidelines",
            "Innovative Approaches to {topic}"
        ]
        
        self._mock_snippets = [
            "This paper presents a novel approach to {topic}, demonstrating significant improvements over existing methods...",
            "We review the current state of {topic} research, highlighting key challenges and opportunities for future work...",
            "Our study explores the practical applications of {topic}, with case studies from multiple domains...",
            "The authors provide a comprehensive overview of {topic}, including theoretical foundations and empirical results...",
            "This work introduces innovative techniques for {topic}, validated through extensive experimental evaluation...",
            "We present a systematic analysis of {topic}, offering insights for researchers and practitioners...",
            "The paper discusses recent advances in {topic}, with implications for future research directions...",
            "Our findings reveal important aspects of {topic} that were previously unexplored in the literature..."
        ]
    
    async def search(self, query: str, max_results: int = 10, 
                    domain_filter: List[str] = None) -> Dict[str, Any]:
        """
        Perform mock web search.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            domain_filter: Optional list of domains to filter by
            
        Returns:
            Search results dictionary
        """
        self.search_count += 1
        
        # Simulate search delay
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        self.logger.info("Performing mock web search", 
                        query=query, max_results=max_results)
        
        # Generate mock results
        results = []
        topic = query.replace(" ", "_").lower()
        
        for i in range(min(max_results, random.randint(5, 15))):
            domain = random.choice(self._mock_domains)
            
            # Apply domain filter if specified
            if domain_filter and domain not in domain_filter:
                continue
            
            title = random.choice(self._mock_titles).format(topic=query)
            snippet = random.choice(self._mock_snippets).format(topic=query)
            url = f"https://{domain}/paper/{topic}_{i+1}"
            
            result = SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                domain=domain,
                published_date=self._generate_random_date(),
                relevance_score=random.uniform(0.6, 0.95)
            )
            
            results.append(result.to_dict())
        
        # Sort by relevance score
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results,
            "search_time": random.uniform(0.1, 0.8),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_random_date(self) -> str:
        """Generate a random recent publication date."""
        import random
        from datetime import timedelta
        
        # Random date within last 3 years
        days_ago = random.randint(1, 1095)
        date = datetime.utcnow() - timedelta(days=days_ago)
        return date.strftime("%Y-%m-%d")
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        return {
            "total_searches": self.search_count,
            "available_domains": self._mock_domains,
            "mock_mode": True
        }


class MockMCPServer(LoggerMixin):
    """Mock MCP (Model Context Protocol) server for development."""
    
    def __init__(self):
        """Initialize mock MCP server."""
        self.tools = {
            "web_search": MockWebSearchTool(),
            "document_analyzer": MockDocumentAnalyzer(),
            "citation_manager": MockCitationManager()
        }
        self.call_count = {}
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a mock tool.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments
            
        Returns:
            Tool result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Track call count
        self.call_count[tool_name] = self.call_count.get(tool_name, 0) + 1
        
        tool = self.tools[tool_name]
        
        # Route to appropriate method based on tool
        if tool_name == "web_search":
            return await tool.search(**kwargs)
        elif tool_name == "document_analyzer":
            return await tool.analyze(**kwargs)
        elif tool_name == "citation_manager":
            return await tool.manage_citations(**kwargs)
        
        raise ValueError(f"No handler for tool: {tool_name}")
    
    async def list_tools(self) -> List[str]:
        """List available tools."""
        return list(self.tools.keys())
    
    async def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return {
            "name": tool_name,
            "description": f"Mock {tool_name} for development",
            "call_count": self.call_count.get(tool_name, 0),
            "available": True
        }


class MockDocumentAnalyzer(LoggerMixin):
    """Mock document analyzer for content analysis."""
    
    async def analyze(self, content: str, analysis_type: str = "summary") -> Dict[str, Any]:
        """
        Analyze document content.
        
        Args:
            content: Document content to analyze
            analysis_type: Type of analysis (summary, sentiment, keywords)
            
        Returns:
            Analysis results
        """
        # Simulate processing delay
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        self.logger.info("Analyzing document content", 
                        content_length=len(content), analysis_type=analysis_type)
        
        if analysis_type == "summary":
            return await self._generate_summary(content)
        elif analysis_type == "sentiment":
            return await self._analyze_sentiment(content)
        elif analysis_type == "keywords":
            return await self._extract_keywords(content)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
    
    async def _generate_summary(self, content: str) -> Dict[str, Any]:
        """Generate mock summary."""
        word_count = len(content.split())
        
        return {
            "summary": f"This document discusses key concepts related to the topic, "
                      f"presenting insights and analysis across {word_count} words. "
                      f"The content covers important aspects and provides valuable information "
                      f"for understanding the subject matter.",
            "key_points": [
                "Primary concept discussed in the document",
                "Secondary insights and analysis",
                "Practical applications and implications",
                "Future directions and recommendations"
            ],
            "word_count": word_count,
            "reading_time": max(1, word_count // 200)  # Minutes
        }
    
    async def _analyze_sentiment(self, content: str) -> Dict[str, Any]:
        """Analyze sentiment (mock)."""
        return {
            "sentiment": random.choice(["positive", "neutral", "negative"]),
            "confidence": random.uniform(0.7, 0.95),
            "emotions": {
                "joy": random.uniform(0.0, 0.5),
                "sadness": random.uniform(0.0, 0.3),
                "anger": random.uniform(0.0, 0.2),
                "fear": random.uniform(0.0, 0.2),
                "surprise": random.uniform(0.0, 0.4)
            }
        }
    
    async def _extract_keywords(self, content: str) -> Dict[str, Any]:
        """Extract keywords (mock)."""
        # Simple mock keyword extraction
        words = content.lower().split()
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        
        # Filter and count words
        word_freq = {}
        for word in words:
            word = word.strip(".,!?;:")
            if len(word) > 3 and word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "keywords": [{"word": word, "frequency": freq} for word, freq in top_keywords],
            "total_words": len(words),
            "unique_words": len(set(words))
        }


class MockCitationManager(LoggerMixin):
    """Mock citation manager for handling references."""
    
    def __init__(self):
        """Initialize citation manager."""
        self.citations = {}
        self.citation_count = 0
    
    async def manage_citations(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Manage citations.
        
        Args:
            action: Action to perform (add, format, validate)
            **kwargs: Action-specific arguments
            
        Returns:
            Action result
        """
        if action == "add":
            return await self._add_citation(**kwargs)
        elif action == "format":
            return await self._format_citations(**kwargs)
        elif action == "validate":
            return await self._validate_citations(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _add_citation(self, title: str, authors: List[str], 
                           url: str, publication_date: str = None) -> Dict[str, Any]:
        """Add a citation."""
        self.citation_count += 1
        citation_id = f"cite_{self.citation_count}"
        
        citation = {
            "id": citation_id,
            "title": title,
            "authors": authors,
            "url": url,
            "publication_date": publication_date,
            "added_at": datetime.utcnow().isoformat()
        }
        
        self.citations[citation_id] = citation
        
        return {
            "citation_id": citation_id,
            "status": "added",
            "citation": citation
        }
    
    async def _format_citations(self, style: str = "apa") -> Dict[str, Any]:
        """Format citations in specified style."""
        formatted = []
        
        for citation in self.citations.values():
            if style.lower() == "apa":
                authors_str = ", ".join(citation["authors"])
                formatted_citation = f"{authors_str} ({citation.get('publication_date', 'n.d.')}). {citation['title']}. Retrieved from {citation['url']}"
            else:
                formatted_citation = f"{citation['title']} - {', '.join(citation['authors'])}"
            
            formatted.append({
                "id": citation["id"],
                "formatted": formatted_citation
            })
        
        return {
            "style": style,
            "count": len(formatted),
            "citations": formatted
        }
    
    async def _validate_citations(self) -> Dict[str, Any]:
        """Validate all citations."""
        valid_count = 0
        issues = []
        
        for citation_id, citation in self.citations.items():
            is_valid = True
            citation_issues = []
            
            if not citation.get("title"):
                is_valid = False
                citation_issues.append("Missing title")
            
            if not citation.get("authors"):
                is_valid = False
                citation_issues.append("Missing authors")
            
            if not citation.get("url"):
                is_valid = False
                citation_issues.append("Missing URL")
            
            if is_valid:
                valid_count += 1
            else:
                issues.append({
                    "citation_id": citation_id,
                    "issues": citation_issues
                })
        
        return {
            "total_citations": len(self.citations),
            "valid_citations": valid_count,
            "invalid_citations": len(issues),
            "issues": issues
        }
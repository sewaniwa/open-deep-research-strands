#!/usr/bin/env python3
"""
Debug tools for Phase 1 local development environment.
"""
import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
import json

# Project root for relative operations
project_root = Path(__file__).parent.parent

from open_deep_research_strands.src.config.strands_config import initialize_strands_sdk, get_sdk_manager
from open_deep_research_strands.src.agents.supervisor_agent import SupervisorAgent
from open_deep_research_strands.src.agents.research_sub_agent import ResearchSubAgent
from open_deep_research_strands.src.agents.scoping_agent import ScopingAgent
from open_deep_research_strands.src.communication.agent_communication import initialize_global_communication
from open_deep_research_strands.src.tools.mock_tools import MockWebSearchTool, MockMCPServer


class DebugSession:
    """Debug session for testing system components."""
    
    def __init__(self):
        self.temp_dir = None
        self.sdk_manager = None
        self.comm_hub = None
        self.agents = {}
        
    async def initialize(self):
        """Initialize debug session."""
        print("🚀 Initializing debug session...")
        
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp())
        print(f"📁 Temporary directory: {self.temp_dir}")
        
        # Initialize SDK
        config_override = {
            "storage_path": self.temp_dir,
            "debug_mode": True,
            "max_concurrent_agents": 5
        }
        
        success = await initialize_strands_sdk(config_override)
        if not success:
            raise RuntimeError("Failed to initialize SDK")
        
        self.sdk_manager = get_sdk_manager()
        print("✅ SDK initialized successfully")
        
        # Initialize communication
        self.comm_hub = await initialize_global_communication()
        print("✅ Communication hub initialized")
        
        print("🎉 Debug session ready!\n")
    
    async def cleanup(self):
        """Clean up debug session."""
        print("\n🧹 Cleaning up debug session...")
        
        # Shutdown agents
        for agent_id, agent in self.agents.items():
            try:
                await agent.shutdown()
                print(f"✅ Agent {agent_id} shutdown")
            except Exception as e:
                print(f"⚠️ Failed to shutdown agent {agent_id}: {e}")
        
        # Stop communication
        if self.comm_hub:
            await self.comm_hub.stop()
            print("✅ Communication hub stopped")
        
        print("✅ Debug session cleaned up")
    
    async def create_supervisor(self):
        """Create and initialize supervisor agent."""
        print("👑 Creating supervisor agent...")
        
        supervisor = SupervisorAgent()
        success = await supervisor.initialize()
        
        if success:
            self.agents["supervisor"] = supervisor
            await self.comm_hub.register_agent(supervisor.agent_id, {"role": "supervisor"})
            print(f"✅ Supervisor created: {supervisor.agent_id}")
            return supervisor
        else:
            print("❌ Failed to create supervisor")
            return None
    
    async def create_research_agent(self, subtopic: str, agent_id: str = None):
        """Create and initialize research agent."""
        print(f"🔬 Creating research agent for: {subtopic}")
        
        research_agent = ResearchSubAgent(subtopic, agent_id)
        success = await research_agent.initialize()
        
        if success:
            self.agents[research_agent.agent_id] = research_agent
            await self.comm_hub.register_agent(research_agent.agent_id, {"role": "researcher"})
            print(f"✅ Research agent created: {research_agent.agent_id}")
            return research_agent
        else:
            print("❌ Failed to create research agent")
            return None
    
    async def create_scoping_agent(self):
        """Create and initialize scoping agent."""
        print("🎯 Creating scoping agent...")
        
        scoping_agent = ScopingAgent()
        success = await scoping_agent.initialize()
        
        if success:
            self.agents[scoping_agent.agent_id] = scoping_agent
            await self.comm_hub.register_agent(scoping_agent.agent_id, {"role": "scoping"})
            print(f"✅ Scoping agent created: {scoping_agent.agent_id}")
            return scoping_agent
        else:
            print("❌ Failed to create scoping agent")
            return None
    
    async def test_mock_tools(self):
        """Test mock tools functionality."""
        print("\n🛠️ Testing mock tools...")
        
        # Test web search
        web_search = MockWebSearchTool()
        search_results = await web_search.search("artificial intelligence", max_results=3)
        
        print(f"📊 Web search results:")
        print(f"   - Query: {search_results['query']}")
        print(f"   - Results count: {len(search_results['results'])}")
        print(f"   - Search time: {search_results['search_time']:.2f}s")
        
        # Test MCP server
        mcp_server = MockMCPServer()
        tools = await mcp_server.list_tools()
        
        print(f"🔧 MCP server tools: {tools}")
        
        # Test document analysis
        analysis_result = await mcp_server.call_tool(
            "document_analyzer",
            content="Artificial intelligence is transforming various industries.",
            analysis_type="summary"
        )
        
        print(f"📄 Document analysis:")
        print(f"   - Summary: {analysis_result['summary'][:100]}...")
        print(f"   - Word count: {analysis_result['word_count']}")
    
    async def test_memory_operations(self):
        """Test memory system operations."""
        print("\n🧠 Testing memory operations...")
        
        memory_system = self.sdk_manager.get_memory_system()
        
        # Create namespace
        namespace = await memory_system.create_namespace("debug_test")
        print(f"📂 Created namespace: {namespace}")
        
        # Store test data
        test_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "test_type": "debug_session",
            "data": {"key1": "value1", "key2": "value2"}
        }
        
        entry_id = await memory_system.store(namespace, "debug_entry", test_data)
        print(f"💾 Stored data with entry ID: {entry_id}")
        
        # Retrieve data
        retrieved = await memory_system.retrieve(namespace, "debug_entry")
        print(f"📥 Retrieved data: {retrieved['test_type']}")
        
        # Search data
        search_results = await memory_system.search(namespace, "debug")
        print(f"🔍 Search results: {len(search_results)} matches")
        
        # Get statistics
        stats = await memory_system.get_namespace_stats(namespace)
        print(f"📈 Namespace stats: {stats['total_entries']} entries")
    
    async def test_a2a_communication(self):
        """Test agent-to-agent communication."""
        print("\n📡 Testing A2A communication...")
        
        if len(self.agents) < 2:
            print("⚠️ Need at least 2 agents for communication test")
            return
        
        agent_ids = list(self.agents.keys())
        sender_id = agent_ids[0]
        receiver_id = agent_ids[1]
        
        print(f"📨 Sending message from {sender_id} to {receiver_id}")
        
        # Send task assignment
        success = await self.comm_hub.send_task_assignment(
            sender_id,
            receiver_id,
            {
                "task": "test_communication",
                "priority": "normal",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        if success:
            print("✅ Message sent successfully")
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Check statistics
            stats = self.comm_hub.get_stats()
            print(f"📊 Communication stats:")
            print(f"   - Messages sent: {stats['hub']['messages_sent']}")
            print(f"   - Messages delivered: {stats['hub']['messages_delivered']}")
        else:
            print("❌ Failed to send message")
    
    async def test_supervisor_workflow(self):
        """Test supervisor workflow execution."""
        print("\n👑 Testing supervisor workflow...")
        
        if "supervisor" not in self.agents:
            print("⚠️ No supervisor agent available")
            return
        
        supervisor = self.agents["supervisor"]
        test_query = "What are the current trends in machine learning?"
        
        print(f"🔍 Executing research query: {test_query}")
        
        try:
            result = await supervisor.execute_control_loop(test_query)
            
            print("✅ Workflow completed successfully!")
            print(f"📊 Results summary:")
            print(f"   - Session ID: {result['session_id']}")
            print(f"   - Phases completed: {result['phases_completed']}")
            print(f"   - Execution time: {result['total_execution_time']:.2f}s")
            
            # Show research brief
            brief = result['research_brief']
            print(f"   - Research objective: {brief['research_objective'][:100]}...")
            print(f"   - Subtopics identified: {len(brief['required_topics'])}")
            
            # Show research results
            research_results = result['research_results']
            print(f"   - Subtopics researched: {len(research_results['subtopic_results'])}")
            
            # Show final report
            final_report = result['final_report']
            print(f"   - Key findings: {len(final_report['key_findings'])}")
            print(f"   - Total sources: {final_report['total_sources']}")
            
        except Exception as e:
            print(f"❌ Workflow failed: {str(e)}")
    
    def print_system_status(self):
        """Print current system status."""
        print(f"\n📊 System Status:")
        print(f"   - SDK initialized: {self.sdk_manager.is_initialized() if self.sdk_manager else False}")
        print(f"   - Communication running: {self.comm_hub.is_running if self.comm_hub else False}")
        print(f"   - Active agents: {len(self.agents)}")
        
        if self.agents:
            print(f"   - Agent details:")
            for agent_id, agent in self.agents.items():
                print(f"     • {agent_id}: {agent.role} ({'active' if agent.is_active else 'inactive'})")
        
        if self.comm_hub:
            stats = self.comm_hub.get_stats()
            print(f"   - Registered agents: {stats['registered_agents']}")
            print(f"   - Messages sent: {stats['hub']['messages_sent']}")


async def run_debug_session():
    """Run interactive debug session."""
    print("🚀 Starting Open Deep Research Strands Debug Session")
    print("=" * 60)
    
    session = DebugSession()
    
    try:
        await session.initialize()
        
        # Create agents
        supervisor = await session.create_supervisor()
        research_agent = await session.create_research_agent("AI applications", "ai_app_001")
        scoping_agent = await session.create_scoping_agent()
        
        session.print_system_status()
        
        # Run tests
        await session.test_mock_tools()
        await session.test_memory_operations()
        await session.test_a2a_communication()
        await session.test_supervisor_workflow()
        
        print("\n🎉 Debug session completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Debug session failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await session.cleanup()


async def run_quick_test():
    """Run quick system validation test."""
    print("⚡ Running Quick System Test")
    print("=" * 30)
    
    session = DebugSession()
    
    try:
        await session.initialize()
        
        # Quick agent creation test
        supervisor = await session.create_supervisor()
        if supervisor:
            print("✅ Supervisor creation: PASS")
        else:
            print("❌ Supervisor creation: FAIL")
            return
        
        # Quick workflow test
        test_query = "Brief test of AI research"
        result = await supervisor.execute_control_loop(test_query)
        
        if result and result.get("status") == "completed":
            print("✅ Workflow execution: PASS")
            print(f"   - Execution time: {result['total_execution_time']:.2f}s")
        else:
            print("❌ Workflow execution: FAIL")
        
        print("\n🎉 Quick test completed!")
        
    except Exception as e:
        print(f"\n❌ Quick test failed: {str(e)}")
        
    finally:
        await session.cleanup()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(run_quick_test())
    else:
        asyncio.run(run_debug_session())
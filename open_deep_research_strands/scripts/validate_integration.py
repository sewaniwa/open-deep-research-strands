#!/usr/bin/env python3
"""
Integration validation script for Phase 1 local development environment.
"""
import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# Project root for relative operations
project_root = Path(__file__).parent.parent


def check_imports():
    """Check that all required modules can be imported."""
    print("📦 Checking imports...")
    
    try:
        # Core configuration
        print("  🔍 Testing configuration modules...")
        from src.config.strands_config import initialize_strands_sdk, get_sdk_manager
        from configs.local_config import get_config
        print("✅ Configuration modules imported")
        
        # Agent classes
        print("  🔍 Testing agent modules...")
        from src.agents.supervisor_agent import SupervisorAgent
        from src.agents.research_sub_agent import ResearchSubAgent
        from src.agents.scoping_agent import ScopingAgent
        from src.agents.base_agent import create_task_data
        print("✅ Agent modules imported")
        
        # Communication system
        print("  🔍 Testing communication modules...")
        from src.communication.agent_communication import AgentCommunicationHub
        from src.communication.messages import A2AMessage, MessageType
        from src.communication.message_router import MessageRouter
        from src.communication.local_queue import LocalMessageQueue
        print("✅ Communication modules imported")
        
        # Tools and utilities
        print("  🔍 Testing tool modules...")
        from src.tools.mock_tools import MockWebSearchTool, MockMCPServer
        from src.tools.llm_interface import LLMManager
        from src.tools.local_memory import LocalMemorySystem
        print("✅ Tool modules imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sdk_initialization():
    """Test SDK initialization."""
    print("\n🚀 Testing SDK initialization...")
    
    try:
        from src.config.strands_config import initialize_strands_sdk, get_sdk_manager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_override = {
                "storage_path": Path(temp_dir),
                "debug_mode": True
            }
            
            # Initialize SDK
            success = await initialize_strands_sdk(config_override)
            if not success:
                print("❌ SDK initialization failed")
                return False
            
            # Get SDK manager
            sdk_manager = get_sdk_manager()
            if not sdk_manager.is_initialized():
                print("❌ SDK manager not properly initialized")
                return False
            
            # Test components
            runtime = sdk_manager.get_runtime()
            memory_system = sdk_manager.get_memory_system()
            
            if runtime is None or memory_system is None:
                print("❌ SDK components not available")
                return False
            
            print("✅ SDK initialization successful")
            return True
            
    except Exception as e:
        print(f"❌ SDK initialization error: {e}")
        return False


async def test_agent_creation():
    """Test agent creation and initialization."""
    print("\n🤖 Testing agent creation...")
    
    try:
        from src.config.strands_config import initialize_strands_sdk, get_sdk_manager
        from src.agents.supervisor_agent import SupervisorAgent
        from src.agents.research_sub_agent import ResearchSubAgent
        from src.agents.scoping_agent import ScopingAgent
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize SDK first
            config_override = {"storage_path": Path(temp_dir), "debug_mode": True}
            await initialize_strands_sdk(config_override)
            
            # Test SupervisorAgent
            supervisor = SupervisorAgent()
            success = await supervisor.initialize()
            if not success:
                print("❌ Supervisor agent initialization failed")
                return False
            
            assert supervisor.is_active
            assert supervisor.session_id is not None
            await supervisor.shutdown()
            print("✅ SupervisorAgent creation successful")
            
            # Test ResearchSubAgent  
            research_agent = ResearchSubAgent("test topic", "test_001")
            success = await research_agent.initialize()
            if not success:
                print("❌ Research agent initialization failed")
                return False
            
            assert research_agent.is_active
            await research_agent.shutdown()
            print("✅ ResearchSubAgent creation successful")
            
            # Test ScopingAgent
            scoping_agent = ScopingAgent()
            success = await scoping_agent.initialize()
            if not success:
                print("❌ Scoping agent initialization failed")
                return False
            
            assert scoping_agent.is_active
            await scoping_agent.shutdown()
            print("✅ ScopingAgent creation successful")
            
            return True
            
    except Exception as e:
        print(f"❌ Agent creation error: {e}")
        return False


async def test_communication_system():
    """Test A2A communication system."""
    print("\n📡 Testing communication system...")
    
    try:
        from src.communication.agent_communication import initialize_global_communication
        
        # Initialize communication hub
        comm_hub = await initialize_global_communication()
        
        # Register test agents
        await comm_hub.register_agent("test_agent_1", {"role": "test"})
        await comm_hub.register_agent("test_agent_2", {"role": "test"})
        
        # Test message sending
        success = await comm_hub.send_task_assignment(
            "test_agent_1", 
            "test_agent_2",
            {"task": "test_task", "data": "test_data"}
        )
        
        if not success:
            print("❌ Message sending failed")
            await comm_hub.stop()
            return False
        
        # Test statistics
        stats = comm_hub.get_stats()
        if stats["hub"]["messages_sent"] < 1:
            print("❌ Message statistics not updated")
            await comm_hub.stop()
            return False
        
        # Cleanup
        await comm_hub.stop()
        print("✅ Communication system test successful")
        return True
        
    except Exception as e:
        print(f"❌ Communication system error: {e}")
        return False


async def test_mock_tools():
    """Test mock tools functionality."""
    print("\n🛠️ Testing mock tools...")
    
    try:
        from src.tools.mock_tools import MockWebSearchTool, MockMCPServer
        
        # Test web search
        web_search = MockWebSearchTool()
        results = await web_search.search("test query", max_results=5)
        
        if not results or "results" not in results:
            print("❌ Web search failed")
            return False
        
        if len(results["results"]) == 0:
            print("❌ Web search returned no results")
            return False
        
        print("✅ MockWebSearchTool test successful")
        
        # Test MCP server
        mcp_server = MockMCPServer()
        tools = await mcp_server.list_tools()
        
        if not tools or len(tools) == 0:
            print("❌ MCP server has no tools")
            return False
        
        # Test tool execution
        result = await mcp_server.call_tool(
            "web_search", 
            query="test", 
            max_results=3
        )
        
        if not result or "results" not in result:
            print("❌ MCP tool execution failed")
            return False
        
        print("✅ MockMCPServer test successful")
        return True
        
    except Exception as e:
        print(f"❌ Mock tools error: {e}")
        return False


async def test_memory_system():
    """Test memory system functionality."""
    print("\n🧠 Testing memory system...")
    
    try:
        from src.config.strands_config import initialize_strands_sdk, get_sdk_manager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize SDK
            config_override = {"storage_path": Path(temp_dir), "debug_mode": True}
            await initialize_strands_sdk(config_override)
            sdk_manager = get_sdk_manager()
            memory_system = sdk_manager.get_memory_system()
            
            # Test namespace creation
            namespace = await memory_system.create_namespace("test_namespace")
            if namespace != "test_namespace":
                print("❌ Namespace creation failed")
                return False
            
            # Test data storage
            test_data = {"key": "value", "timestamp": datetime.utcnow().isoformat()}
            entry_id = await memory_system.store(namespace, "test_key", test_data)
            
            if not entry_id:
                print("❌ Data storage failed")
                return False
            
            # Test data retrieval
            retrieved = await memory_system.retrieve(namespace, "test_key")
            if retrieved != test_data:
                print("❌ Data retrieval failed")
                return False
            
            # Test search
            search_results = await memory_system.search(namespace, "value")
            if len(search_results) == 0:
                print("❌ Memory search failed")
                return False
            
            print("✅ Memory system test successful")
            return True
            
    except Exception as e:
        print(f"❌ Memory system error: {e}")
        return False


async def test_end_to_end_workflow():
    """Test end-to-end workflow execution."""
    print("\n🔄 Testing end-to-end workflow...")
    
    try:
        from src.config.strands_config import initialize_strands_sdk, get_sdk_manager
        from src.agents.supervisor_agent import SupervisorAgent
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize complete system
            config_override = {"storage_path": Path(temp_dir), "debug_mode": True}
            await initialize_strands_sdk(config_override)
            supervisor = SupervisorAgent()
            success = await supervisor.initialize()
            
            if not success:
                print("❌ Supervisor initialization failed")
                return False
            
            # Execute research workflow
            test_query = "What is machine learning?"
            
            try:
                result = await supervisor.execute_control_loop(test_query)
                
                # Verify result structure
                required_keys = ["session_id", "user_query", "research_brief", 
                               "research_results", "final_report", "status"]
                
                for key in required_keys:
                    if key not in result:
                        print(f"❌ Missing key in result: {key}")
                        await supervisor.shutdown()
                        return False
                
                if result["status"] != "completed":
                    print(f"❌ Workflow not completed: {result['status']}")
                    await supervisor.shutdown()
                    return False
                
                # Verify phases completed
                if result["phases_completed"] != ["scoping", "research", "report"]:
                    print("❌ Not all phases completed")
                    await supervisor.shutdown()
                    return False
                
                # Verify content quality
                brief = result["research_brief"]
                if len(brief["required_topics"]) < 3:
                    print("❌ Insufficient subtopics generated")
                    await supervisor.shutdown()
                    return False
                
                research_results = result["research_results"]
                if len(research_results["subtopic_results"]) < 3:
                    print("❌ Insufficient research results")
                    await supervisor.shutdown()
                    return False
                
                final_report = result["final_report"]
                if len(final_report["key_findings"]) == 0:
                    print("❌ No key findings in final report")
                    await supervisor.shutdown()
                    return False
                
                await supervisor.shutdown()
                print("✅ End-to-end workflow test successful")
                print(f"   - Query: {test_query}")
                print(f"   - Execution time: {result['total_execution_time']:.2f}s")
                print(f"   - Subtopics: {len(brief['required_topics'])}")
                print(f"   - Key findings: {len(final_report['key_findings'])}")
                
                return True
                
            except Exception as e:
                await supervisor.shutdown()
                print(f"❌ Workflow execution error: {e}")
                return False
            
    except Exception as e:
        print(f"❌ End-to-end test error: {e}")
        return False


async def main():
    """Run all integration validation tests."""
    print("🚀 Open Deep Research Strands - Phase 1 Integration Validation")
    print("=" * 70)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    tests = [
        ("Import Validation", check_imports),
        ("SDK Initialization", test_sdk_initialization),
        ("Agent Creation", test_agent_creation), 
        ("Communication System", test_communication_system),
        ("Mock Tools", test_mock_tools),
        ("Memory System", test_memory_system),
        ("End-to-End Workflow", test_end_to_end_workflow)
    ]
    
    results = []
    total_start_time = asyncio.get_event_loop().time()
    
    for test_name, test_func in tests:
        print(f"🧪 Running {test_name}...")
        start_time = asyncio.get_event_loop().time()
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            
            execution_time = asyncio.get_event_loop().time() - start_time
            results.append((test_name, success, execution_time))
            
            if success:
                print(f"✅ {test_name} PASSED ({execution_time:.2f}s)")
            else:
                print(f"❌ {test_name} FAILED ({execution_time:.2f}s)")
                
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            results.append((test_name, False, execution_time))
            print(f"💥 {test_name} ERROR ({execution_time:.2f}s): {e}")
        
        print()
    
    # Summary
    total_time = asyncio.get_event_loop().time() - total_start_time
    passed_tests = sum(1 for _, success, _ in results if success)
    total_tests = len(results)
    
    print("=" * 70)
    print("📊 PHASE 1 INTEGRATION VALIDATION SUMMARY")
    print("=" * 70)
    
    for test_name, success, exec_time in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {test_name:25} ({exec_time:.2f}s)")
    
    print(f"\nResults: {passed_tests}/{total_tests} tests passed")
    print(f"Total execution time: {total_time:.2f}s")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("\nPhase 1 Local Development Environment is fully functional:")
        print("✅ Project structure and configuration")
        print("✅ Strands Agents SDK integration") 
        print("✅ Basic agent classes (Supervisor, Research, Scoping)")
        print("✅ A2A communication system")
        print("✅ Mock tools and services")
        print("✅ Local memory system")
        print("✅ End-to-end research workflow")
        print("\nSystem is ready for Phase 2 development!")
        return True
    else:
        print(f"\n⚠️ {total_tests - passed_tests} INTEGRATION TESTS FAILED")
        print("Please resolve the failing tests before proceeding to Phase 2.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Integration validation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Integration validation crashed: {e}")
        sys.exit(1)
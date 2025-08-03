#!/usr/bin/env python3
"""
Simple test script for SupervisorAgent core functionality.
"""
import asyncio
import sys
import os
sys.path.insert(0, '/workspace/open_deep_research_strands')

async def test_supervisor_core():
    """Test SupervisorAgent core functionality."""
    print("🧪 Testing SupervisorAgent Core Implementation")
    print("=" * 60)
    
    try:
        # Test 1: Import check
        print("📦 Test 1: Import validation...")
        try:
            from src.agents.supervisor_agent import SupervisorAgent
            print("✅ SupervisorAgent imported successfully")
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            return False
        
        # Test 2: Basic instantiation
        print("\n🤖 Test 2: Agent instantiation...")
        try:
            supervisor = SupervisorAgent()
            print(f"✅ SupervisorAgent created: {supervisor.name}")
            print(f"   - Agent ID: {supervisor.agent_id}")
            print(f"   - Role: {supervisor.role}")
            print(f"   - Capabilities: {supervisor.capabilities}")
        except Exception as e:
            print(f"❌ Instantiation failed: {e}")
            return False
        
        # Test 3: Management systems check
        print("\n🔧 Test 3: Management systems validation...")
        try:
            # Check if management systems are initialized
            assert hasattr(supervisor, 'agent_manager'), "AgentManager not initialized"
            assert hasattr(supervisor, 'quality_controller'), "QualityController not initialized"
            assert hasattr(supervisor, 'swarm_controller'), "SwarmController not initialized"
            assert hasattr(supervisor, 'error_handler'), "ErrorHandler not initialized"
            
            print("✅ All management systems initialized:")
            print(f"   - AgentManager: {type(supervisor.agent_manager).__name__}")
            print(f"   - QualityController: {type(supervisor.quality_controller).__name__}")
            print(f"   - SwarmController: {type(supervisor.swarm_controller).__name__}")
            print(f"   - ErrorHandler: {type(supervisor.error_handler).__name__}")
        except Exception as e:
            print(f"❌ Management systems validation failed: {e}")
            return False
        
        # Test 4: Status reporting
        print("\n📊 Test 4: Status reporting...")
        try:
            status = supervisor.get_session_status()
            print("✅ Status reporting works:")
            print(f"   - Active sessions: {status['supervisor_status']['total_sessions']}")
            print(f"   - Current phase: {status['supervisor_status']['current_phase']}")
            print(f"   - Agent pool size: {status['agent_manager_status']['total_agents']}")
        except Exception as e:
            print(f"❌ Status reporting failed: {e}")
            return False
        
        # Test 5: Diagnostics
        print("\n🔍 Test 5: Management diagnostics...")
        try:
            diagnostics = await supervisor.get_management_diagnostics()
            print("✅ Diagnostics reporting works:")
            print(f"   - Supervisor class: {diagnostics['supervisor_agent']['class_name']}")
            print(f"   - Max concurrent agents: {diagnostics['agent_manager']['max_concurrent_agents']}")
            print(f"   - Quality thresholds: {list(diagnostics['quality_controller']['quality_thresholds'].keys())}")
            print(f"   - Swarm concurrent limit: {diagnostics['swarm_controller']['concurrent_limit']}")
            print(f"   - Error recovery strategies: {diagnostics['error_handler']['recovery_strategies']}")
        except Exception as e:
            print(f"❌ Diagnostics failed: {e}")
            return False
        
        print("\n" + "=" * 60)
        print("✅ ALL CORE TESTS PASSED!")
        print("SupervisorAgent core implementation is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_supervisor_core())
    if result:
        print("\n🎉 SupervisorAgent core implementation completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 SupervisorAgent core implementation has issues.")
        sys.exit(1)
"""
Phase 2 Integration Test Suite
Tests the complete multi-agent research system integration.
"""
import asyncio
import sys
import os
import time
from typing import Dict, Any
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'open_deep_research_strands'))

# Set environment variables for testing
os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'open_deep_research_strands')

class Phase2IntegrationTest:
    """Comprehensive integration test for Phase 2 implementation."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    async def run_all_tests(self):
        """Run all integration tests."""
        print("🧪 Starting Phase 2 Integration Test Suite")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Test 1: SupervisorAgent Initialization
        await self.test_supervisor_initialization()
        
        # Test 2: ScopingAgent Integration
        await self.test_scoping_agent_integration()
        
        # Test 3: ReportAgent Integration
        await self.test_report_agent_integration()
        
        # Test 4: End-to-End Research Workflow
        await self.test_end_to_end_workflow()
        
        # Test 5: Error Handling and Recovery
        await self.test_error_handling()
        
        # Test 6: Quality Control System
        await self.test_quality_control()
        
        # Test 7: Performance Benchmarks
        await self.test_performance()
        
        self.end_time = time.time()
        
        # Generate test report
        await self.generate_test_report()
    
    async def test_supervisor_initialization(self):
        """Test SupervisorAgent initialization and core systems."""
        print("\n📋 Test 1: SupervisorAgent Initialization")
        print("-" * 40)
        
        try:
            from src.agents.supervisor_agent import SupervisorAgent
            
            supervisor = SupervisorAgent()
            await supervisor.initialize()
            
            # Test management systems initialization
            assert supervisor.agent_manager is not None, "AgentManager not initialized"
            assert supervisor.quality_controller is not None, "QualityController not initialized"
            assert supervisor.swarm_controller is not None, "SwarmController not initialized"
            assert supervisor.error_handler is not None, "ErrorHandler not initialized"
            
            # Test session management
            session_state = await supervisor.start_research_session("test_query")
            assert "session_id" in session_state, "Session ID not generated"
            assert session_state["is_active"] == True, "Session not marked as active"
            
            self.test_results["supervisor_initialization"] = {
                "status": "PASSED",
                "details": "All management systems initialized successfully",
                "session_id": session_state.get("session_id")
            }
            print("✅ SupervisorAgent initialization: PASSED")
            
        except Exception as e:
            self.test_results["supervisor_initialization"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ SupervisorAgent initialization: FAILED - {e}")
    
    async def test_scoping_agent_integration(self):
        """Test ScopingAgent integration with SupervisorAgent."""
        print("\n🎯 Test 2: ScopingAgent Integration")
        print("-" * 40)
        
        try:
            from src.agents.supervisor_agent import SupervisorAgent
            
            supervisor = SupervisorAgent()
            await supervisor.initialize()
            
            session_state = await supervisor.start_research_session("artificial intelligence in healthcare")
            
            # Test scoping phase execution
            research_brief = await supervisor.execute_scoping_phase(
                "artificial intelligence in healthcare", 
                session_state
            )
            
            # Validate research brief structure
            required_fields = ["original_query", "research_objective", "required_topics", "scope_boundaries"]
            for field in required_fields:
                assert field in research_brief, f"Missing required field: {field}"
            
            assert len(research_brief["required_topics"]) >= 3, "Insufficient subtopics identified"
            
            self.test_results["scoping_integration"] = {
                "status": "PASSED",
                "details": "ScopingAgent integrated successfully",
                "subtopics_count": len(research_brief["required_topics"]),
                "scoping_method": research_brief.get("scoping_method", "unknown")
            }
            print("✅ ScopingAgent integration: PASSED")
            
        except Exception as e:
            self.test_results["scoping_integration"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ ScopingAgent integration: FAILED - {e}")
    
    async def test_report_agent_integration(self):
        """Test ReportAgent integration with SupervisorAgent."""
        print("\n📊 Test 3: ReportAgent Integration")
        print("-" * 40)
        
        try:
            from src.agents.report_agent import ReportAgent
            from src.agents.base_agent import TaskData
            
            # Create mock research results
            mock_research_results = {
                "subtopic_results": {
                    "subtopic_1": {
                        "title": "AI Fundamentals in Healthcare",
                        "analysis": "Artificial intelligence is transforming healthcare through advanced diagnostics and treatment optimization.",
                        "key_findings": [
                            "AI improves diagnostic accuracy by 15-20%",
                            "Machine learning reduces treatment planning time",
                            "Natural language processing enhances patient records analysis"
                        ],
                        "sources": [
                            {"title": "AI in Healthcare Review", "url": "https://example.com", "relevance": 0.9}
                        ],
                        "confidence_score": 0.85
                    }
                }
            }
            
            mock_research_brief = {
                "original_query": "artificial intelligence in healthcare",
                "research_objective": "Comprehensive analysis of AI applications in healthcare",
                "scope_boundaries": {"temporal": "2020-2024", "depth": "comprehensive"}
            }
            
            report_agent = ReportAgent()
            await report_agent.initialize()
            
            report_task = TaskData(
                task_id="test_report_001",
                task_type="report_generation",
                content={
                    "research_results": mock_research_results,
                    "research_brief": mock_research_brief,
                    "report_config": {"formats": ["markdown", "json"]}
                },
                priority="high"
            )
            
            report_result = await report_agent.execute_task(report_task)
            
            assert report_result.success, "Report generation failed"
            assert "report_content" in report_result.result, "Missing report content"
            assert "formatted_reports" in report_result.result, "Missing formatted reports"
            assert "quality_check" in report_result.result, "Missing quality check"
            
            self.test_results["report_integration"] = {
                "status": "PASSED",
                "details": "ReportAgent integrated successfully",
                "formats_generated": len(report_result.result["formatted_reports"]),
                "quality_score": report_result.result["quality_check"].get("quality_score", 0.0)
            }
            print("✅ ReportAgent integration: PASSED")
            
        except Exception as e:
            self.test_results["report_integration"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ ReportAgent integration: FAILED - {e}")
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end research workflow."""
        print("\n🔄 Test 4: End-to-End Research Workflow")
        print("-" * 40)
        
        try:
            from src.agents.supervisor_agent import SupervisorAgent
            
            supervisor = SupervisorAgent()
            await supervisor.initialize()
            
            # Start research session
            session_state = await supervisor.start_research_session("machine learning applications")
            
            # Execute complete research workflow
            final_report = await supervisor.conduct_research("machine learning applications")
            
            # Validate final report structure
            assert "title" in final_report, "Missing report title"
            assert "research_objective" in final_report, "Missing research objective"
            assert "key_findings" in final_report, "Missing key findings"
            assert len(final_report["key_findings"]) >= 3, "Insufficient key findings"
            
            # Check quality metrics
            quality_metrics = final_report.get("quality_metrics", {})
            overall_score = quality_metrics.get("overall_score", 0.0)
            assert overall_score >= 0.7, f"Quality score too low: {overall_score}"
            
            self.test_results["end_to_end_workflow"] = {
                "status": "PASSED",
                "details": "Complete workflow executed successfully",
                "quality_score": overall_score,
                "findings_count": len(final_report["key_findings"])
            }
            print("✅ End-to-End workflow: PASSED")
            
        except Exception as e:
            self.test_results["end_to_end_workflow"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ End-to-End workflow: FAILED - {e}")
    
    async def test_error_handling(self):
        """Test error handling and recovery mechanisms."""
        print("\n⚠️  Test 5: Error Handling and Recovery")
        print("-" * 40)
        
        try:
            from src.agents.error_handler import ResearchErrorHandler
            from src.agents.supervisor_agent import SupervisorAgent
            
            supervisor = SupervisorAgent()
            await supervisor.initialize()
            
            error_handler = supervisor.error_handler
            
            # Test error classification
            test_error = Exception("Test connection timeout")
            error_category = error_handler._classify_error(test_error, {})
            assert error_category is not None, "Error classification failed"
            
            # Test recovery strategy selection
            recovery_strategies = error_handler.recovery_strategies.get(error_category, [])
            assert len(recovery_strategies) > 0, "No recovery strategies found"
            
            # Test recovery execution
            recovery_result = await error_handler.execute_recovery(
                test_error, {}, "test_task_001"
            )
            assert "recovery_attempted" in recovery_result, "Recovery not attempted"
            
            self.test_results["error_handling"] = {
                "status": "PASSED",
                "details": "Error handling system working correctly",
                "error_category": str(error_category),
                "recovery_strategies": len(recovery_strategies)
            }
            print("✅ Error handling: PASSED")
            
        except Exception as e:
            self.test_results["error_handling"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ Error handling: FAILED - {e}")
    
    async def test_quality_control(self):
        """Test quality control system."""
        print("\n🎯 Test 6: Quality Control System")
        print("-" * 40)
        
        try:
            from src.agents.quality_controller import QualityController
            from src.agents.supervisor_agent import SupervisorAgent
            
            supervisor = SupervisorAgent()
            await supervisor.initialize()
            
            quality_controller = supervisor.quality_controller
            
            # Create mock research results for quality assessment
            mock_results = {
                "subtopic_results": {
                    "test_subtopic": {
                        "confidence_score": 0.85,
                        "source_count": 5,
                        "finding_count": 4
                    }
                }
            }
            
            mock_brief = {
                "research_objective": "Test quality assessment",
                "quality_requirements": {"minimum_sources": 3, "minimum_confidence": 0.8}
            }
            
            # Test quality assessment
            quality_assessment = await quality_controller.assess_research_quality(
                mock_results, mock_brief
            )
            
            # Quality assessment returns QualityAssessment object, convert to dict
            qa_dict = quality_assessment.to_dict()
            assert "overall_score" in qa_dict, "Missing overall quality score"
            assert "dimension_scores" in qa_dict, "Missing dimension scores"
            assert "recommendations" in qa_dict, "Missing recommendations"
            
            self.test_results["quality_control"] = {
                "status": "PASSED",
                "details": "Quality control system working correctly",
                "overall_score": qa_dict["overall_score"],
                "dimensions_assessed": len(qa_dict["dimension_scores"])
            }
            print("✅ Quality control: PASSED")
            
        except Exception as e:
            self.test_results["quality_control"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ Quality control: FAILED - {e}")
    
    async def test_performance(self):
        """Test system performance benchmarks."""
        print("\n⚡ Test 7: Performance Benchmarks")
        print("-" * 40)
        
        try:
            from src.agents.supervisor_agent import SupervisorAgent
            
            # Performance test: Session initialization
            start_time = time.time()
            supervisor = SupervisorAgent()
            await supervisor.initialize()
            init_time = time.time() - start_time
            
            # Performance test: Scoping phase
            start_time = time.time()
            session_state = await supervisor.start_research_session("performance test query")
            brief = await supervisor.execute_scoping_phase("performance test query", session_state)
            scoping_time = time.time() - start_time
            
            # Performance benchmarks
            assert init_time < 5.0, f"Initialization too slow: {init_time}s"
            assert scoping_time < 10.0, f"Scoping phase too slow: {scoping_time}s"
            
            self.test_results["performance"] = {
                "status": "PASSED",
                "details": "Performance benchmarks met",
                "initialization_time": round(init_time, 2),
                "scoping_time": round(scoping_time, 2)
            }
            print("✅ Performance benchmarks: PASSED")
            
        except Exception as e:
            self.test_results["performance"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ Performance benchmarks: FAILED - {e}")
    
    async def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("📋 PHASE 2 INTEGRATION TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASSED")
        failed_tests = total_tests - passed_tests
        
        execution_time = self.end_time - self.start_time
        
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"   Execution Time: {execution_time:.2f}s")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result["status"] == "PASSED" else "❌"
            print(f"   {status_icon} {test_name.replace('_', ' ').title()}: {result['status']}")
            if result["status"] == "FAILED":
                print(f"      Error: {result.get('error', 'Unknown error')}")
            else:
                print(f"      Details: {result.get('details', 'No details')}")
        
        print(f"\n🎯 SYSTEM STATUS:")
        if failed_tests == 0:
            print("   🟢 ALL SYSTEMS OPERATIONAL")
            print("   Phase 2 implementation is complete and fully functional!")
        elif failed_tests <= 2:
            print("   🟡 MOSTLY OPERATIONAL")
            print("   Minor issues detected, but core functionality is working.")
        else:
            print("   🔴 ISSUES DETECTED")
            print("   Multiple system failures require attention.")
        
        # Write detailed report to file
        report_content = {
            "test_execution": {
                "timestamp": datetime.utcnow().isoformat(),
                "execution_time": execution_time,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests/total_tests)*100
            },
            "test_results": self.test_results
        }
        
        try:
            import json
            with open("/workspace/phase2_test_report.json", "w") as f:
                json.dump(report_content, f, indent=2)
            print(f"\n📄 Detailed report saved to: /workspace/phase2_test_report.json")
        except Exception as e:
            print(f"\n⚠️  Could not save detailed report: {e}")
        
        print("=" * 60)


async def main():
    """Main test execution function."""
    test_suite = Phase2IntegrationTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
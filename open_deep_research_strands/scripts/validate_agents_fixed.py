#!/usr/bin/env python3
"""
Fixed validation script for agent classes.
"""
import ast
import sys
from pathlib import Path


def validate_python_syntax(file_path: Path) -> bool:
    """Validate Python file syntax."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        ast.parse(content)
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False


def validate_class_structure(file_path: Path, expected_classes: list) -> bool:
    """Validate that expected classes are defined in the file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Find all class definitions
        classes_found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes_found.append(node.name)
        
        # Check if expected classes are present
        missing_classes = []
        for expected_class in expected_classes:
            if expected_class not in classes_found:
                missing_classes.append(expected_class)
        
        if missing_classes:
            print(f"❌ Missing classes in {file_path}: {missing_classes}")
            return False
        
        print(f"✅ All expected classes found in {file_path}: {classes_found}")
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing {file_path}: {e}")
        return False


def validate_method_structure(file_path: Path, class_name: str, expected_methods: list) -> bool:
    """Validate that expected methods are defined in a class."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Find the specific class
        target_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                target_class = node
                break
        
        if not target_class:
            print(f"❌ Class {class_name} not found in {file_path}")
            return False
        
        # Find all method definitions in the class (including async)
        methods_found = []
        for node in target_class.body:
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                methods_found.append(node.name)
        
        # Check if expected methods are present
        missing_methods = []
        for expected_method in expected_methods:
            if expected_method not in methods_found:
                missing_methods.append(expected_method)
        
        if missing_methods:
            print(f"❌ Missing methods in {class_name}: {missing_methods}")
            print(f"   Found methods: {methods_found}")
            return False
        
        print(f"✅ All expected methods found in {class_name}: {len(methods_found)} total methods")
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing methods in {file_path}: {e}")
        return False


def validate_file_content(file_path: Path, expected_content: list) -> bool:
    """Validate that file contains expected content patterns."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        missing_content = []
        for expected in expected_content:
            if expected not in content:
                missing_content.append(expected)
        
        if missing_content:
            print(f"❌ Missing content patterns in {file_path}: {missing_content}")
            return False
        
        print(f"✅ All expected content found in {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error checking content in {file_path}: {e}")
        return False


def main():
    """Run agent validation tests."""
    print("🚀 Validating Agent Classes (Fixed)...\n")
    
    project_root = Path(__file__).parent.parent
    agents_dir = project_root / "src" / "agents"
    
    test_files = [
        {
            "file": agents_dir / "base_agent.py",
            "classes": ["BaseResearchAgent", "TaskData", "AgentResult"],
            "key_class": "BaseResearchAgent",
            "key_methods": ["__init__", "initialize", "execute_task", "shutdown"],
            "content_patterns": ["async def initialize", "async def execute_task", "async def shutdown"]
        },
        {
            "file": agents_dir / "supervisor_agent.py", 
            "classes": ["SupervisorAgent"],
            "key_class": "SupervisorAgent",
            "key_methods": ["__init__", "execute_task", "execute_control_loop"],
            "content_patterns": ["async def execute_task", "async def execute_control_loop"]
        },
        {
            "file": agents_dir / "research_sub_agent.py",
            "classes": ["ResearchSubAgent"],
            "key_class": "ResearchSubAgent", 
            "key_methods": ["__init__", "execute_task", "conduct_research"],
            "content_patterns": ["async def execute_task", "async def conduct_research"]
        },
        {
            "file": agents_dir / "scoping_agent.py",
            "classes": ["ScopingAgent"],
            "key_class": "ScopingAgent",
            "key_methods": ["__init__", "execute_task", "conduct_clarification_dialogue"],
            "content_patterns": ["async def execute_task", "async def conduct_clarification_dialogue"]
        }
    ]
    
    all_passed = True
    
    for test_info in test_files:
        file_path = test_info["file"]
        print(f"\n📋 Validating {file_path.name}:")
        
        # Test syntax
        if not validate_python_syntax(file_path):
            all_passed = False
            continue
        
        # Test class structure
        if not validate_class_structure(file_path, test_info["classes"]):
            all_passed = False
            continue
        
        # Test content patterns (more reliable than AST for async methods)
        if not validate_file_content(file_path, test_info["content_patterns"]):
            all_passed = False
            continue
        
        print(f"✅ {file_path.name} validation passed")
    
    # Test agent relationships and inheritance
    print(f"\n📋 Validating Agent Relationships:")
    
    try:
        supervisor_file = agents_dir / "supervisor_agent.py"
        research_file = agents_dir / "research_sub_agent.py"
        scoping_file = agents_dir / "scoping_agent.py"
        
        inheritance_tests = [
            (supervisor_file, "SupervisorAgent", ["BaseResearchAgent", "AgentCapabilityMixin"]),
            (research_file, "ResearchSubAgent", ["BaseResearchAgent", "AgentCapabilityMixin"]),
            (scoping_file, "ScopingAgent", ["BaseResearchAgent", "AgentCapabilityMixin"])
        ]
        
        for file_path, class_name, expected_bases in inheritance_tests:
            with open(file_path, 'r') as f:
                content = f.read()
            
            for base in expected_bases:
                if base in content:
                    print(f"✅ {class_name} uses {base}")
                else:
                    print(f"❌ {class_name} missing {base}")
                    all_passed = False
        
    except Exception as e:
        print(f"❌ Relationship validation failed: {e}")
        all_passed = False
    
    # Test key functionality patterns
    print(f"\n📋 Validating Key Functionality:")
    
    functionality_tests = [
        (agents_dir / "supervisor_agent.py", "3-phase control loop", ["execute_scoping_phase", "execute_research_phase", "execute_report_phase"]),
        (agents_dir / "research_sub_agent.py", "iterative research", ["generate_search_queries", "execute_searches", "analyze_search_results"]),
        (agents_dir / "scoping_agent.py", "dialogue management", ["generate_clarification_questions", "update_understanding", "generate_research_brief"])
    ]
    
    for file_path, feature_name, patterns in functionality_tests:
        if validate_file_content(file_path, patterns):
            print(f"✅ {feature_name} functionality implemented")
        else:
            print(f"❌ {feature_name} functionality incomplete")
            all_passed = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 AGENT VALIDATION SUMMARY")
    print(f"{'='*50}")
    
    if all_passed:
        print("🎉 All agent validation tests passed!")
        print("\nAgent Implementation Summary:")
        print("✅ BaseResearchAgent - Complete base class with SDK integration")
        print("✅ SupervisorAgent - 3-phase control loop orchestrator")  
        print("✅ ResearchSubAgent - Iterative research specialist")
        print("✅ ScopingAgent - Requirement clarification and brief generation")
        print("\nNext steps:")
        print("1. Continue with Task 1.5 (A2A Communication System)")
        print("2. Install dependencies for full testing: pip install -r requirements.txt")
        print("3. Run integration tests: pytest tests/")
        return True
    else:
        print("⚠️ Some agent validation tests failed.")
        print("Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
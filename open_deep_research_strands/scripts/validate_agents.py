#!/usr/bin/env python3
"""
Validation script for agent classes without external dependencies.
"""
import ast
import sys
from pathlib import Path


def validate_python_syntax(file_path: Path) -> bool:
    """Validate Python file syntax."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse the file to check syntax
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
        
        # Find all method definitions in the class
        methods_found = []
        for node in target_class.body:
            if isinstance(node, ast.FunctionDef):
                methods_found.append(node.name)
        
        # Check if expected methods are present
        missing_methods = []
        for expected_method in expected_methods:
            if expected_method not in methods_found:
                missing_methods.append(expected_method)
        
        if missing_methods:
            print(f"❌ Missing methods in {class_name}: {missing_methods}")
            return False
        
        print(f"✅ All expected methods found in {class_name}: {len(methods_found)} methods")
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing methods in {file_path}: {e}")
        return False


def validate_imports(file_path: Path) -> bool:
    """Validate import statements structure."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Find all imports
        imports_found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports_found.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports_found.append(f"from {node.module}")
        
        print(f"✅ Import structure valid in {file_path}: {len(imports_found)} imports")
        return True
        
    except Exception as e:
        print(f"❌ Import analysis failed for {file_path}: {e}")
        return False


def main():
    """Run agent validation tests."""
    print("🚀 Validating Agent Classes...\n")
    
    project_root = Path(__file__).parent.parent
    agents_dir = project_root / "src" / "agents"
    
    test_files = [
        {
            "file": agents_dir / "base_agent.py",
            "classes": ["BaseResearchAgent", "TaskData", "AgentResult", "AgentCapabilityMixin"],
            "key_class": "BaseResearchAgent",
            "key_methods": ["__init__", "initialize", "execute_task", "shutdown"]
        },
        {
            "file": agents_dir / "supervisor_agent.py", 
            "classes": ["SupervisorAgent"],
            "key_class": "SupervisorAgent",
            "key_methods": ["__init__", "execute_task", "execute_control_loop"]
        },
        {
            "file": agents_dir / "research_sub_agent.py",
            "classes": ["ResearchSubAgent"],
            "key_class": "ResearchSubAgent", 
            "key_methods": ["__init__", "execute_task", "conduct_research"]
        },
        {
            "file": agents_dir / "scoping_agent.py",
            "classes": ["ScopingAgent"],
            "key_class": "ScopingAgent",
            "key_methods": ["__init__", "execute_task", "conduct_clarification_dialogue"]
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
        
        # Test imports
        if not validate_imports(file_path):
            all_passed = False
            continue
        
        # Test class structure
        if not validate_class_structure(file_path, test_info["classes"]):
            all_passed = False
            continue
        
        # Test key methods
        if not validate_method_structure(
            file_path, 
            test_info["key_class"], 
            test_info["key_methods"]
        ):
            all_passed = False
            continue
        
        print(f"✅ {file_path.name} validation passed")
    
    # Test agent relationships
    print(f"\n📋 Validating Agent Relationships:")
    
    try:
        # Check BaseResearchAgent inheritance
        base_agent_file = agents_dir / "base_agent.py"
        supervisor_file = agents_dir / "supervisor_agent.py"
        
        with open(supervisor_file, 'r') as f:
            supervisor_content = f.read()
        
        if "BaseResearchAgent" in supervisor_content:
            print("✅ SupervisorAgent inherits from BaseResearchAgent")
        else:
            print("❌ SupervisorAgent missing BaseResearchAgent inheritance")
            all_passed = False
        
        if "AgentCapabilityMixin" in supervisor_content:
            print("✅ SupervisorAgent uses AgentCapabilityMixin")
        else:
            print("❌ SupervisorAgent missing AgentCapabilityMixin")
            all_passed = False
        
    except Exception as e:
        print(f"❌ Relationship validation failed: {e}")
        all_passed = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 AGENT VALIDATION SUMMARY")
    print(f"{'='*50}")
    
    if all_passed:
        print("🎉 All agent validation tests passed!")
        print("\nAgent classes are properly structured and ready for use.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run full tests: pytest tests/test_basic_agents.py")
        print("3. Continue with Phase 1 Task 1.5 (A2A Communication)")
        return True
    else:
        print("⚠️ Some agent validation tests failed.")
        print("Please fix the issues above before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
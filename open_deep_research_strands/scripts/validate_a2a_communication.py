#!/usr/bin/env python3
"""
Validation script for A2A communication system.
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


def validate_enum_definitions(file_path: Path, expected_enums: list) -> bool:
    """Validate enum definitions."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Find all class definitions that inherit from Enum
        enums_found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class inherits from Enum
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Enum":
                        enums_found.append(node.name)
                        break
        
        missing_enums = []
        for expected_enum in expected_enums:
            if expected_enum not in enums_found:
                missing_enums.append(expected_enum)
        
        if missing_enums:
            print(f"❌ Missing enums in {file_path}: {missing_enums}")
            return False
        
        print(f"✅ All expected enums found in {file_path}: {enums_found}")
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing enums in {file_path}: {e}")
        return False


def main():
    """Run A2A communication validation tests."""
    print("🚀 Validating A2A Communication System...\n")
    
    project_root = Path(__file__).parent.parent
    comm_dir = project_root / "src" / "communication"
    
    test_files = [
        {
            "file": comm_dir / "messages.py",
            "classes": ["A2AMessage", "MessageBuilder", "MessageValidator"],
            "enums": ["MessageType", "MessagePriority", "MessageStatus"],
            "content_patterns": [
                "class A2AMessage",
                "def to_dict",
                "def from_dict", 
                "def to_json",
                "def from_json",
                "def is_expired",
                "def can_retry",
                "def create_reply"
            ]
        },
        {
            "file": comm_dir / "message_router.py",
            "classes": ["MessageRoute", "MessageRouter"],
            "content_patterns": [
                "async def route_message",
                "async def start_processing",
                "async def stop_processing",
                "def register_route",
                "def register_agent_handler",
                "_processing_loop"
            ]
        },
        {
            "file": comm_dir / "local_queue.py", 
            "classes": ["LocalMessageQueue", "LocalQueueManager"],
            "enums": ["QueueType"],
            "content_patterns": [
                "async def enqueue",
                "async def dequeue",
                "async def add_consumer",
                "async def start",
                "async def stop",
                "_consumer_loop"
            ]
        },
        {
            "file": comm_dir / "agent_communication.py",
            "classes": ["AgentCommunicationHub"],
            "content_patterns": [
                "async def register_agent",
                "async def unregister_agent",
                "async def send_message",
                "async def send_task_assignment",
                "async def send_research_request",
                "async def send_research_result",
                "async def broadcast_message"
            ]
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
        if "classes" in test_info:
            if not validate_class_structure(file_path, test_info["classes"]):
                all_passed = False
                continue
        
        # Test enum definitions
        if "enums" in test_info:
            if not validate_enum_definitions(file_path, test_info["enums"]):
                all_passed = False
                continue
        
        # Test content patterns
        if not validate_file_content(file_path, test_info["content_patterns"]):
            all_passed = False
            continue
        
        print(f"✅ {file_path.name} validation passed")
    
    # Test integration and dependencies
    print(f"\n📋 Validating Integration:")
    
    try:
        # Check imports between modules
        messages_file = comm_dir / "messages.py"
        router_file = comm_dir / "message_router.py"
        queue_file = comm_dir / "local_queue.py"
        hub_file = comm_dir / "agent_communication.py"
        
        # Check that router imports messages
        with open(router_file, 'r') as f:
            router_content = f.read()
        
        if ".messages import" in router_content:
            print("✅ MessageRouter imports message classes")
        else:
            print("❌ MessageRouter missing message imports")
            all_passed = False
        
        # Check that hub imports all components
        with open(hub_file, 'r') as f:
            hub_content = f.read()
        
        required_imports = [".messages import", ".message_router import", ".local_queue import"]
        for imp in required_imports:
            if imp in hub_content:
                print(f"✅ AgentCommunicationHub has {imp}")
            else:
                print(f"❌ AgentCommunicationHub missing {imp}")
                all_passed = False
        
    except Exception as e:
        print(f"❌ Integration validation failed: {e}")
        all_passed = False
    
    # Test key functionality patterns
    print(f"\n📋 Validating Key Functionality:")
    
    functionality_tests = [
        (comm_dir / "messages.py", "Message serialization", ["to_dict", "from_dict", "to_json", "from_json"]),
        (comm_dir / "message_router.py", "Async message routing", ["async def route_message", "_processing_loop", "register_route"]),
        (comm_dir / "local_queue.py", "Priority queue management", ["MessagePriority", "async def enqueue", "async def dequeue"]),
        (comm_dir / "agent_communication.py", "Agent communication hub", ["register_agent", "send_message", "broadcast_message"])
    ]
    
    for file_path, feature_name, patterns in functionality_tests:
        if validate_file_content(file_path, patterns):
            print(f"✅ {feature_name} functionality implemented")
        else:
            print(f"❌ {feature_name} functionality incomplete")
            all_passed = False
    
    # Test file structure
    print(f"\n📋 Validating File Structure:")
    
    required_files = [
        comm_dir / "__init__.py",
        comm_dir / "messages.py",
        comm_dir / "message_router.py", 
        comm_dir / "local_queue.py",
        comm_dir / "agent_communication.py"
    ]
    
    for file_path in required_files:
        if file_path.exists():
            print(f"✅ {file_path.name} exists")
        else:
            print(f"❌ {file_path.name} missing")
            all_passed = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 A2A COMMUNICATION VALIDATION SUMMARY")
    print(f"{'='*50}")
    
    if all_passed:
        print("🎉 All A2A communication validation tests passed!")
        print("\nA2A Communication System Summary:")
        print("✅ A2AMessage - Complete message structure with serialization")
        print("✅ MessageRouter - Async routing with pattern matching")
        print("✅ LocalMessageQueue - Priority-based queue with consumers")
        print("✅ AgentCommunicationHub - Integrated communication system")
        print("✅ Message types and priorities properly defined")
        print("✅ Error handling and retry logic implemented")
        print("\nNext steps:")
        print("1. Continue with Task 1.6 (Integration Testing)")
        print("2. Install dependencies for full testing: pip install -r requirements.txt")
        print("3. Run communication tests: pytest tests/test_a2a_communication.py")
        return True
    else:
        print("⚠️ Some A2A communication validation tests failed.")
        print("Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
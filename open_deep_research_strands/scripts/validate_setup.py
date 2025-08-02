#!/usr/bin/env python3
"""
Validation script for Open Deep Research Strands setup.
Tests the basic setup without external dependencies.
"""
import os
import sys
from pathlib import Path

def validate_project_structure():
    """Validate that all required directories and files exist."""
    project_root = Path(__file__).parent.parent
    
    required_paths = [
        # Core source directories
        "src",
        "src/agents",
        "src/workflows", 
        "src/communication",
        "src/tools",
        "src/evaluation",
        "src/config",
        
        # Configuration and setup
        "configs",
        "scripts",
        "tests",
        
        # Runtime directories
        "local_memory",
        "local_memory/sessions",
        "local_memory/cache",
        "local_memory/temp",
        "logs",
        
        # Configuration files
        "configs/local_config.py",
        "src/config/logging_config.py",
        "src/config/strands_config.py",
        "src/tools/local_memory.py",
        "src/tools/mock_tools.py",
        "src/tools/llm_interface.py",
        ".env.example",
        ".env",
        "pyproject.toml",
        "requirements.txt",
        "README.md"
    ]
    
    missing_paths = []
    
    for path_str in required_paths:
        path = project_root / path_str
        if not path.exists():
            missing_paths.append(path_str)
    
    if missing_paths:
        print("❌ Missing required paths:")
        for path in missing_paths:
            print(f"   - {path}")
        return False
    else:
        print("✅ All required paths exist")
        return True


def validate_python_files():
    """Validate that Python files have correct syntax."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    
    python_files = []
    for py_file in src_dir.rglob("*.py"):
        python_files.append(py_file)
    
    syntax_errors = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r') as f:
                code = f.read()
            
            # Basic syntax check without importing
            compile(code, str(py_file), 'exec')
            
        except SyntaxError as e:
            syntax_errors.append((py_file, str(e)))
        except Exception as e:
            # Skip import errors and other issues for now
            pass
    
    if syntax_errors:
        print("❌ Python syntax errors found:")
        for file_path, error in syntax_errors:
            print(f"   - {file_path}: {error}")
        return False
    else:
        print(f"✅ All {len(python_files)} Python files have valid syntax")
        return True


def validate_configuration():
    """Validate configuration files."""
    project_root = Path(__file__).parent.parent
    
    # Check .env file
    env_file = project_root / ".env"
    if env_file.exists():
        print("✅ .env file exists")
    else:
        print("❌ .env file missing")
        return False
    
    # Check pyproject.toml
    pyproject_file = project_root / "pyproject.toml"
    if pyproject_file.exists():
        try:
            content = pyproject_file.read_text()
            if "open-deep-research-strands" in content:
                print("✅ pyproject.toml is correctly configured")
            else:
                print("❌ pyproject.toml missing project name")
                return False
        except Exception as e:
            print(f"❌ Error reading pyproject.toml: {e}")
            return False
    else:
        print("❌ pyproject.toml missing")
        return False
    
    return True


def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    project_root = Path(__file__).parent.parent
    
    print("🔧 Testing basic configuration access...")
    
    try:
        # Add project to Python path
        sys.path.insert(0, str(project_root))
        
        # Test configuration constants (without importing the modules)
        config_file = project_root / "configs/local_config.py"
        if config_file.exists():
            with open(config_file, 'r') as f:
                content = f.read()
                if "LOCAL_CONFIG" in content:
                    print("✅ Local configuration structure looks correct")
                else:
                    print("❌ LOCAL_CONFIG not found in configuration")
                    return False
        
        # Test that critical files are not empty
        critical_files = [
            "src/config/strands_config.py",
            "src/tools/local_memory.py", 
            "src/tools/mock_tools.py",
            "src/tools/llm_interface.py"
        ]
        
        for file_path in critical_files:
            full_path = project_root / file_path
            if full_path.exists() and full_path.stat().st_size > 100:  # At least 100 bytes
                print(f"✅ {file_path} has content")
            else:
                print(f"❌ {file_path} is empty or missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing basic functionality: {e}")
        return False


def main():
    """Run all validation tests."""
    print("🚀 Validating Open Deep Research Strands setup...\n")
    
    tests = [
        ("Project Structure", validate_project_structure),
        ("Python Syntax", validate_python_files),
        ("Configuration Files", validate_configuration),
        ("Basic Functionality", test_basic_functionality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 VALIDATION SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All validation tests passed! Setup is complete.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Edit .env file to add your API keys")
        print("3. Run full tests: pytest tests/")
        return True
    else:
        print(f"\n⚠️  {total - passed} validation tests failed. Please fix the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
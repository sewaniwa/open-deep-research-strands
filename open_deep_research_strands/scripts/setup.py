#!/usr/bin/env python3
"""
Setup script for Open Deep Research Strands project.
"""
import os
import sys
from pathlib import Path

def create_directories():
    """Create necessary directories for the project."""
    directories = [
        "logs",
        "local_memory/sessions",
        "local_memory/cache", 
        "local_memory/temp",
    ]
    
    project_root = Path(__file__).parent.parent
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")


def setup_environment():
    """Set up the development environment."""
    project_root = Path(__file__).parent.parent
    
    # Create .env file if it doesn't exist
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        env_file.write_text(env_example.read_text())
        print(f"Created .env file from template: {env_file}")
        print("Please edit .env file to add your API keys")
    
    # Create necessary directories
    create_directories()
    
    print("\nSetup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file to add your API keys")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run tests: pytest tests/")


if __name__ == "__main__":
    setup_environment()